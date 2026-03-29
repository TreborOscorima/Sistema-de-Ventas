"""Estado de configuración de Facturación Electrónica.

Gestiona la configuración de billing (CompanyBillingConfig) desde
el panel de administración en Configuración > Facturación.
Incluye listado y reintento de documentos fiscales fallidos,
y el dashboard completo de documentos fiscales con filtros/paginación.
"""
import reflex as rx
from datetime import datetime
from sqlalchemy import func, or_
from sqlmodel import select

from app.enums import FiscalStatus, ReceiptType
from app.models.billing import CompanyBillingConfig, FiscalDocument
from app.services.billing_service import retry_fiscal_document, emit_fiscal_document
from app.utils.crypto import encrypt_text
from app.utils.fiscal_validators import validate_tax_id, validate_business_name
from app.i18n import MSG
from app.utils.logger import get_logger
from app.utils.timezone import utc_now_naive
from .mixin_state import MixinState

logger = get_logger("BillingState")


class BillingState(MixinState):
    """Estado para la configuración de facturación electrónica."""

    # ── Form fields ───────────────────────────────────────────
    billing_form_key: int = 0
    billing_is_active: bool = False
    billing_country: str = "PE"
    billing_environment: str = "sandbox"
    billing_tax_id: str = ""
    billing_tax_id_type: str = "RUC"
    billing_business_name: str = ""
    billing_business_address: str = ""
    billing_nubefact_url: str = ""
    billing_nubefact_token_display: str = ""
    billing_afip_punto_venta: int = 1
    billing_serie_factura: str = "F001"
    billing_serie_boleta: str = "B001"
    billing_max_limit: int = 500

    # ── Lookup API ─────────────────────────────────────────────
    billing_lookup_api_url: str = ""
    billing_lookup_api_token_display: str = ""
    # ── Argentina extras ───────────────────────────────────────
    billing_emisor_iva: str = "RI"
    billing_ar_threshold: str = "68782.00"
    billing_cert_status: str = ""  # "", "configurado", "no configurado"
    billing_key_status: str = ""

    # ── Read-only display ─────────────────────────────────────
    billing_current_count: int = 0
    billing_seq_factura: int = 0
    billing_seq_boleta: int = 0
    billing_config_exists: bool = False

    # ── Helpers ─────────────────────────────────────────────────

    def _refresh_billing_active_flag(self):
        """Carga solo billing_is_active desde DB (ligero, para sidebar).

        Se llama desde _do_runtime_refresh() para que el sidebar sepa
        si mostrar el item de Facturación Electrónica sin cargar toda
        la configuración completa.
        """
        company_id = self._company_id()
        if not company_id:
            self.billing_is_active = False
            return
        with rx.session() as session:
            config = session.exec(
                select(CompanyBillingConfig.is_active)
                .where(CompanyBillingConfig.company_id == company_id)
            ).first()
            self.billing_is_active = bool(config) if config is not None else False

    # ── Events ────────────────────────────────────────────────

    @rx.event
    def load_billing_config(self):
        """Carga la configuración de billing desde DB."""
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            config = session.exec(
                select(CompanyBillingConfig)
                .where(CompanyBillingConfig.company_id == company_id)
            ).first()
            if config is None:
                self.billing_config_exists = False
                self.billing_is_active = False
                # Pre-fill from company settings
                self.billing_country = getattr(self, "selected_country_code", "PE") or "PE"
                self.billing_tax_id = getattr(self, "ruc", "") or ""
                self.billing_business_name = getattr(self, "company_name", "") or ""
                self.billing_business_address = getattr(self, "address", "") or ""
                self.billing_form_key += 1
                return
            self.billing_config_exists = True
            self.billing_is_active = config.is_active
            self.billing_country = config.country or "PE"
            self.billing_environment = config.environment or "sandbox"
            self.billing_tax_id = config.tax_id or ""
            self.billing_tax_id_type = config.tax_id_type or "RUC"
            self.billing_business_name = config.business_name or ""
            self.billing_business_address = config.business_address or ""
            self.billing_nubefact_url = config.nubefact_url or ""
            self.billing_nubefact_token_display = (
                "****configurado****" if config.nubefact_token else ""
            )
            self.billing_afip_punto_venta = config.afip_punto_venta or 1
            self.billing_emisor_iva = config.emisor_iva_condition or "RI"
            self.billing_ar_threshold = str(config.ar_identification_threshold or "68782")
            self.billing_lookup_api_url = config.lookup_api_url or ""
            self.billing_lookup_api_token_display = (
                "****configurado****" if config.lookup_api_token else ""
            )
            self.billing_serie_factura = config.serie_factura or "F001"
            self.billing_serie_boleta = config.serie_boleta or "B001"
            self.billing_max_limit = config.max_billing_limit or 500
            self.billing_current_count = config.current_billing_count or 0
            self.billing_seq_factura = config.current_sequence_factura or 0
            self.billing_seq_boleta = config.current_sequence_boleta or 0
            # ── Estado de certificados AFIP ──
            self.billing_cert_status = (
                "configurado" if config.encrypted_certificate else "no configurado"
            )
            self.billing_key_status = (
                "configurado" if config.encrypted_private_key else "no configurado"
            )
            self.billing_form_key += 1

    @rx.event
    def save_billing_config(self):
        """Valida y persiste la configuración de billing."""
        block = self._require_manage_config()
        if block:
            return block

        company_id = self._company_id()
        if not company_id:
            self.add_notification(MSG.FISCAL_COMPANY_UNDEFINED, "error")
            return

        # Validaciones — el usuario final solo gestiona datos fiscales básicos.
        # Los campos técnicos (Nubefact URL/Token, ambiente, series) los
        # configura el Owner desde el backoffice de plataforma.

        # Validar RUC/CUIT con checksum según país
        tid_ok, tid_err = validate_tax_id(
            self.billing_tax_id, self.billing_country
        )
        if not tid_ok:
            self.add_notification(tid_err, "warning")
            return

        # Validar razón social
        bname_ok, bname_err = validate_business_name(
            self.billing_business_name
        )
        if not bname_ok:
            self.add_notification(bname_err, "warning")
            return

        with rx.session() as session:
            config = session.exec(
                select(CompanyBillingConfig)
                .where(CompanyBillingConfig.company_id == company_id)
            ).first()

            if config is None:
                config = CompanyBillingConfig(company_id=company_id)

            # Solo actualizar campos que el usuario final gestiona.
            # Campos técnicos (nubefact_url, nubefact_token, environment,
            # series, is_active, etc.) los gestiona el Owner.
            config.country = self.billing_country.strip()
            config.tax_id = self.billing_tax_id.strip()
            config.tax_id_type = self.billing_tax_id_type.strip()
            config.business_name = self.billing_business_name.strip()
            config.business_address = self.billing_business_address.strip()
            config.lookup_api_url = self.billing_lookup_api_url.strip()
            config.emisor_iva_condition = self.billing_emisor_iva.strip() or "RI"
            config.ar_identification_threshold = (
                self.billing_ar_threshold.strip() or "68782.00"
            )
            config.updated_at = utc_now_naive()

            session.add(config)
            session.commit()

        self.billing_config_exists = True
        self.add_notification(MSG.FISCAL_CONFIG_SAVED, "success")
        return rx.toast(MSG.FISCAL_CONFIG_SAVED_SHORT, duration=3000)

    @rx.event
    def save_billing_token(self, token: str):
        """Guarda el token de Nubefact encriptado."""
        block = self._require_manage_config()
        if block:
            return block
        token = (token or "").strip()
        if not token:
            self.add_notification(MSG.FISCAL_TOKEN_EMPTY, "warning")
            return
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            config = session.exec(
                select(CompanyBillingConfig)
                .where(CompanyBillingConfig.company_id == company_id)
            ).first()
            if config is None:
                self.add_notification(
                    MSG.FISCAL_SAVE_FIRST, "warning"
                )
                return
            config.nubefact_token = encrypt_text(token)
            config.updated_at = utc_now_naive()
            session.add(config)
            session.commit()
        self.billing_nubefact_token_display = "****configurado****"
        self.add_notification(MSG.FISCAL_TOKEN_SAVED, "success")

    # ── Setters usados por la UI del usuario final ──────────

    @rx.event
    def set_billing_country(self, value: str):
        self.billing_country = value or "PE"
        if value == "PE":
            self.billing_tax_id_type = "RUC"
        elif value == "AR":
            self.billing_tax_id_type = "CUIT"

    @rx.event
    def set_billing_tax_id(self, value: str):
        self.billing_tax_id = value or ""

    @rx.event
    def set_billing_business_name(self, value: str):
        self.billing_business_name = value or ""

    @rx.event
    def set_billing_business_address(self, value: str):
        self.billing_business_address = value or ""

    @rx.event
    def set_lookup_api_url(self, value: str):
        self.billing_lookup_api_url = value or ""

    @rx.event
    def set_lookup_api_token(self, value: str):
        """Almacena el token crudo y muestra versión enmascarada."""
        raw = (value or "").strip()
        self._lookup_api_token_raw = raw
        if raw:
            self.billing_lookup_api_token_display = raw[:4] + "****" + raw[-4:] if len(raw) > 8 else "****"
        else:
            self.billing_lookup_api_token_display = ""

    @rx.event
    def save_afip_certificate(self, cert_pem: str):
        """Guarda el certificado X.509 PEM de AFIP encriptado."""
        block = self._require_manage_config()
        if block:
            return block
        cert_pem = (cert_pem or "").strip()
        if not cert_pem:
            self.add_notification(MSG.FISCAL_CERT_EMPTY, "warning")
            return
        if "-----BEGIN CERTIFICATE-----" not in cert_pem:
            self.add_notification(MSG.FISCAL_CERT_INVALID_PEM, "warning")
            return
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            config = session.exec(
                select(CompanyBillingConfig)
                .where(CompanyBillingConfig.company_id == company_id)
            ).first()
            if config is None:
                self.add_notification(
                    MSG.FISCAL_SAVE_FIRST_FISCAL, "warning"
                )
                return
            config.encrypted_certificate = encrypt_text(cert_pem)
            config.updated_at = utc_now_naive()
            session.add(config)
            session.commit()
        self.billing_cert_status = "configurado"
        self.add_notification(MSG.FISCAL_CERT_SAVED, "success")

    @rx.event
    def save_afip_private_key(self, key_pem: str):
        """Guarda la clave privada RSA PEM de AFIP encriptada."""
        block = self._require_manage_config()
        if block:
            return block
        key_pem = (key_pem or "").strip()
        if not key_pem:
            self.add_notification(MSG.FISCAL_KEY_EMPTY, "warning")
            return
        if "-----BEGIN" not in key_pem or "PRIVATE KEY" not in key_pem:
            self.add_notification(MSG.FISCAL_KEY_INVALID_PEM, "warning")
            return
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            config = session.exec(
                select(CompanyBillingConfig)
                .where(CompanyBillingConfig.company_id == company_id)
            ).first()
            if config is None:
                self.add_notification(
                    MSG.FISCAL_SAVE_FIRST_FISCAL, "warning"
                )
                return
            config.encrypted_private_key = encrypt_text(key_pem)
            config.updated_at = utc_now_naive()
            session.add(config)
            session.commit()
        self.billing_key_status = "configurado"
        self.add_notification(MSG.FISCAL_KEY_SAVED, "success")

    @rx.event
    def set_emisor_iva(self, value: str):
        self.billing_emisor_iva = value or "RI"

    @rx.event
    def set_ar_threshold(self, value: float | str):
        self.billing_ar_threshold = str(value) if value else "68782.00"

    @rx.event
    def save_lookup_api_token(self, token: str):
        """Guarda el token de API de consulta RUC/DNI encriptado."""
        block = self._require_manage_config()
        if block:
            return block
        token = (token or "").strip()
        if not token:
            self.add_notification(MSG.FISCAL_TOKEN_EMPTY, "warning")
            return
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            config = session.exec(
                select(CompanyBillingConfig)
                .where(CompanyBillingConfig.company_id == company_id)
            ).first()
            if config is None:
                self.add_notification(
                    MSG.FISCAL_SAVE_FIRST, "warning"
                )
                return
            config.lookup_api_token = encrypt_text(token)
            config.updated_at = utc_now_naive()
            session.add(config)
            session.commit()
        self.billing_lookup_api_token_display = "****configurado****"
        self.add_notification(MSG.FISCAL_LOOKUP_TOKEN_SAVED, "success")

    # ── Failed fiscal documents (panel en Configuración) ───────
    failed_fiscal_docs: list[dict[str, str]] = []
    retry_loading: bool = False

    # ── Fiscal Documents Dashboard (página /documentos-fiscales) ─
    fiscal_docs_list: list[dict] = []
    fiscal_docs_loading: bool = False
    fiscal_docs_page: int = 0
    fiscal_docs_per_page: int = 20
    fiscal_docs_total: int = 0
    fiscal_docs_status_filter: str = "todos"
    fiscal_docs_receipt_filter: str = "todos"
    fiscal_docs_search: str = ""
    fiscal_docs_date_from: str = ""
    fiscal_docs_date_to: str = ""
    # ── Detail modal ──────────────────────────────────────────
    fiscal_doc_selected: dict = {}
    fiscal_doc_detail_open: bool = False

    @rx.event
    def load_failed_fiscal_docs(self):
        """Carga documentos fiscales en estado error/pending para la empresa."""
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            docs = session.exec(
                select(FiscalDocument)
                .where(FiscalDocument.company_id == company_id)
                .where(
                    FiscalDocument.fiscal_status.in_([
                        FiscalStatus.error,
                        FiscalStatus.pending,
                    ])
                )
                .order_by(FiscalDocument.created_at.desc())  # type: ignore[union-attr]
                .limit(50)
            ).all()
            self.failed_fiscal_docs = [
                {
                    "id": str(doc.id),
                    "sale_id": str(doc.sale_id),
                    "receipt_type": doc.receipt_type or "",
                    "full_number": doc.full_number or "Sin número",
                    "status": doc.fiscal_status or "",
                    "retry_count": str(doc.retry_count or 0),
                    "errors": (doc.fiscal_errors or "")[:200],
                    "created_at": (
                        doc.created_at.strftime("%Y-%m-%d %H:%M")
                        if doc.created_at
                        else ""
                    ),
                }
                for doc in docs
            ]

    @rx.event
    async def retry_fiscal_doc(self, doc_id: str):
        """Reintenta la emisión de un documento fiscal fallido."""
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.add_notification(MSG.FISCAL_BRANCH_UNDEFINED, "error")
            return

        self.retry_loading = True
        yield

        try:
            result = await retry_fiscal_document(
                fiscal_doc_id=int(doc_id),
                company_id=company_id,
                branch_id=branch_id,
            )
            if result is None:
                self.add_notification(
                    MSG.FISCAL_RETRY_FAILED, "error"
                )
            elif result.fiscal_status == FiscalStatus.authorized:
                self.add_notification(
                    MSG.FISCAL_DOC_AUTHORIZED.format(full_number=result.full_number),
                    "success",
                )
            elif result.fiscal_status in (FiscalStatus.error, FiscalStatus.rejected):
                self.add_notification(
                    MSG.FISCAL_DOC_ERRORS.format(full_number=result.full_number),
                    "warning",
                )
            else:
                self.add_notification(
                    MSG.FISCAL_DOC_STATUS.format(
                        full_number=result.full_number, status=result.fiscal_status,
                    ),
                    "info",
                )
        except Exception as exc:
            logger.exception("Error en retry_fiscal_doc: %s", exc)
            self.add_notification(MSG.FISCAL_RETRY_ERROR, "error")
        finally:
            self.retry_loading = False

        # Refrescar la lista
        self.load_failed_fiscal_docs()

    # ══════════════════════════════════════════════════════════
    # DASHBOARD DE DOCUMENTOS FISCALES — /documentos-fiscales
    # ══════════════════════════════════════════════════════════

    @rx.event
    def page_init_documentos_fiscales(self):
        """on_load para la página /documentos-fiscales."""
        self.fiscal_docs_page = 0
        self.fiscal_docs_status_filter = "todos"
        self.fiscal_docs_receipt_filter = "todos"
        self.fiscal_docs_search = ""
        self.fiscal_docs_date_from = ""
        self.fiscal_docs_date_to = ""
        self.fiscal_doc_selected = {}
        self.fiscal_doc_detail_open = False
        self.load_fiscal_docs()

    @rx.event
    def load_fiscal_docs(self):
        """Carga documentos fiscales con filtros y paginación."""
        company_id = self._company_id()
        if not company_id:
            return

        self.fiscal_docs_loading = True
        try:
            with rx.session() as session:
                # ── Base query ────────────────────────────────────────
                conditions = [FiscalDocument.company_id == company_id]

                if self.fiscal_docs_status_filter != "todos":
                    conditions.append(
                        FiscalDocument.fiscal_status == self.fiscal_docs_status_filter
                    )

                if self.fiscal_docs_receipt_filter != "todos":
                    conditions.append(
                        FiscalDocument.receipt_type == self.fiscal_docs_receipt_filter
                    )

                # Búsqueda por número, receptor o doc
                search = (self.fiscal_docs_search or "").strip()
                if search:
                    like_term = f"%{search}%"
                    conditions.append(
                        or_(
                            FiscalDocument.full_number.like(like_term),  # type: ignore
                            FiscalDocument.buyer_name.like(like_term),  # type: ignore
                            FiscalDocument.buyer_doc_number.like(like_term),  # type: ignore
                        )
                    )

                # Filtro por fecha desde
                date_from_str = (self.fiscal_docs_date_from or "").strip()
                if date_from_str:
                    try:
                        df = datetime.strptime(date_from_str, "%Y-%m-%d")
                        conditions.append(FiscalDocument.created_at >= df)
                    except ValueError:
                        pass

                # Filtro por fecha hasta
                date_to_str = (self.fiscal_docs_date_to or "").strip()
                if date_to_str:
                    try:
                        dt = datetime.strptime(date_to_str, "%Y-%m-%d")
                        # Incluir todo el día
                        dt = dt.replace(hour=23, minute=59, second=59)
                        conditions.append(FiscalDocument.created_at <= dt)
                    except ValueError:
                        pass

                # ── Contar total ──────────────────────────────────────
                count_stmt = select(func.count(FiscalDocument.id)).where(*conditions)
                self.fiscal_docs_total = session.exec(count_stmt).one() or 0

                # ── Paginación ────────────────────────────────────────
                offset = self.fiscal_docs_page * self.fiscal_docs_per_page
                docs_stmt = (
                    select(FiscalDocument)
                    .where(*conditions)
                    .order_by(FiscalDocument.created_at.desc())  # type: ignore[union-attr]
                    .offset(offset)
                    .limit(self.fiscal_docs_per_page)
                )
                docs = session.exec(docs_stmt).all()

                self.fiscal_docs_list = [
                    {
                        "id": str(doc.id),
                        "sale_id": str(doc.sale_id),
                        "receipt_type": doc.receipt_type or "",
                        "full_number": doc.full_number or "Sin número",
                        "status": doc.fiscal_status or "",
                        "retry_count": str(doc.retry_count or 0),
                        "errors": (doc.fiscal_errors or "")[:500],
                        "buyer_doc_type": doc.buyer_doc_type or "",
                        "buyer_doc_number": doc.buyer_doc_number or "",
                        "buyer_name": doc.buyer_name or "",
                        "total_amount": str(doc.total_amount or "0.00"),
                        "taxable_amount": str(doc.taxable_amount or "0.00"),
                        "tax_amount": str(doc.tax_amount or "0.00"),
                        "hash_code": doc.hash_code or "",
                        "qr_data": (doc.qr_data or "")[:200],
                        "created_at": (
                            doc.created_at.strftime("%d/%m/%Y %H:%M")
                            if doc.created_at else ""
                        ),
                        "sent_at": (
                            doc.sent_at.strftime("%d/%m/%Y %H:%M")
                            if doc.sent_at else ""
                        ),
                        "authorized_at": (
                            doc.authorized_at.strftime("%d/%m/%Y %H:%M")
                            if doc.authorized_at else ""
                        ),
                    }
                    for doc in docs
                ]
        except Exception as exc:
            logger.exception("Error en load_fiscal_docs: %s", exc)
            self.fiscal_docs_list = []
            self.fiscal_docs_total = 0
        finally:
            self.fiscal_docs_loading = False

    @rx.var(cache=False)
    def fiscal_docs_total_pages(self) -> int:
        """Número total de páginas."""
        if self.fiscal_docs_per_page <= 0:
            return 1
        total = max(0, self.fiscal_docs_total)
        return max(1, (total + self.fiscal_docs_per_page - 1) // self.fiscal_docs_per_page)

    @rx.var(cache=False)
    def fiscal_docs_has_prev(self) -> bool:
        return self.fiscal_docs_page > 0

    @rx.var(cache=False)
    def fiscal_docs_has_next(self) -> bool:
        return self.fiscal_docs_page < self.fiscal_docs_total_pages - 1

    @rx.var(cache=False)
    def fiscal_docs_page_display(self) -> str:
        return f"Pág. {self.fiscal_docs_page + 1} de {self.fiscal_docs_total_pages}"

    @rx.event
    def fiscal_docs_next_page(self):
        if self.fiscal_docs_has_next:
            self.fiscal_docs_page += 1
            self.load_fiscal_docs()

    @rx.event
    def fiscal_docs_prev_page(self):
        if self.fiscal_docs_has_prev:
            self.fiscal_docs_page -= 1
            self.load_fiscal_docs()

    @rx.event
    def set_fiscal_docs_status_filter(self, value: str):
        self.fiscal_docs_status_filter = value or "todos"

    @rx.event
    def set_fiscal_docs_receipt_filter(self, value: str):
        self.fiscal_docs_receipt_filter = value or "todos"

    @rx.event
    def set_fiscal_docs_search(self, value: str):
        self.fiscal_docs_search = value or ""

    @rx.event
    def set_fiscal_docs_date_from(self, value: str):
        self.fiscal_docs_date_from = value or ""

    @rx.event
    def set_fiscal_docs_date_to(self, value: str):
        self.fiscal_docs_date_to = value or ""

    @rx.event
    def apply_fiscal_docs_filters(self):
        """Aplica filtros y vuelve a la primera página."""
        self.fiscal_docs_page = 0
        self.load_fiscal_docs()

    @rx.event
    def reset_fiscal_docs_filters(self):
        """Limpia todos los filtros y recarga."""
        self.fiscal_docs_page = 0
        self.fiscal_docs_status_filter = "todos"
        self.fiscal_docs_receipt_filter = "todos"
        self.fiscal_docs_search = ""
        self.fiscal_docs_date_from = ""
        self.fiscal_docs_date_to = ""
        self.load_fiscal_docs()

    @rx.event
    def open_fiscal_doc_detail(self, doc_id: str):
        """Abre el modal de detalle de un documento fiscal."""
        for doc in self.fiscal_docs_list:
            if doc.get("id") == doc_id:
                self.fiscal_doc_selected = doc
                break
        self.fiscal_doc_detail_open = True

    @rx.event
    def close_fiscal_doc_detail(self):
        """Cierra el modal de detalle."""
        self.fiscal_doc_detail_open = False
        self.fiscal_doc_selected = {}

    @rx.event
    async def retry_fiscal_doc_from_dashboard(self, doc_id: str):
        """Reintenta un documento fiscal desde el dashboard."""
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.add_notification(MSG.FISCAL_BRANCH_UNDEFINED, "error")
            return

        self.fiscal_docs_loading = True
        yield

        try:
            result = await retry_fiscal_document(
                fiscal_doc_id=int(doc_id),
                company_id=company_id,
                branch_id=branch_id,
            )
            if result is None:
                self.add_notification(MSG.FISCAL_RETRY_FAILED, "error")
            elif result.fiscal_status == FiscalStatus.authorized:
                self.add_notification(
                    MSG.FISCAL_DOC_AUTHORIZED.format(full_number=result.full_number),
                    "success",
                )
                self.fiscal_doc_detail_open = False
            elif result.fiscal_status in (FiscalStatus.error, FiscalStatus.rejected):
                self.add_notification(
                    MSG.FISCAL_DOC_ERRORS_SHORT.format(full_number=result.full_number),
                    "warning",
                )
            else:
                self.add_notification(
                    MSG.FISCAL_DOC_STATUS.format(
                        full_number=result.full_number, status=result.fiscal_status,
                    ),
                    "info",
                )
        except Exception as exc:
            logger.exception("Error en retry_fiscal_doc_from_dashboard: %s", exc)
            self.add_notification(MSG.FISCAL_RETRY_ERROR, "error")
        finally:
            self.fiscal_docs_loading = False

        self.load_fiscal_docs()

    # ══════════════════════════════════════════════════════════
    # NOTA DE CRÉDITO — anulación de ventas facturadas
    # ══════════════════════════════════════════════════════════

    nota_credito_loading: bool = False

    @rx.event
    async def emit_credit_note(self, fiscal_doc_id: str, reason: str = ""):
        """Emite una nota de crédito para anular un documento fiscal autorizado.

        Se llama cuando una venta previamente facturada (boleta/factura con
        estado 'authorized') necesita ser anulada.  Crea un nuevo FiscalDocument
        del tipo nota_credito referenciando la venta original.
        """
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.add_notification(MSG.FISCAL_BRANCH_UNDEFINED, "error")
            return

        self.nota_credito_loading = True
        yield

        try:
            # ── Validar y capturar datos dentro de la sesión ──────
            orig_sale_id: int | None = None
            orig_buyer_doc_type: str | None = None
            orig_buyer_doc_number: str | None = None
            orig_buyer_name: str | None = None
            orig_id: int | None = None

            with rx.session() as session:
                original = session.exec(
                    select(FiscalDocument).where(
                        FiscalDocument.id == int(fiscal_doc_id),
                        FiscalDocument.company_id == company_id,
                    )
                ).first()

                if not original:
                    self.add_notification(MSG.FISCAL_DOC_NOT_FOUND, "error")
                    return

                if original.fiscal_status != FiscalStatus.authorized:
                    self.add_notification(
                        MSG.FISCAL_ANNUL_AUTHORIZED_ONLY,
                        "warning",
                    )
                    return

                # Verificar que no exista ya una NC para esta venta
                nc_exists = session.exec(
                    select(FiscalDocument).where(
                        FiscalDocument.sale_id == original.sale_id,
                        FiscalDocument.receipt_type == ReceiptType.nota_credito,
                        FiscalDocument.company_id == company_id,
                    )
                ).first()
                if nc_exists:
                    self.add_notification(
                        MSG.FISCAL_NC_EXISTS.format(full_number=nc_exists.full_number),
                        "warning",
                    )
                    return

                # Capturar todos los valores ANTES de cerrar la sesión
                orig_sale_id = original.sale_id
                orig_buyer_doc_type = original.buyer_doc_type
                orig_buyer_doc_number = original.buyer_doc_number
                orig_buyer_name = original.buyer_name
                orig_id = original.id

            if orig_sale_id is None:
                self.add_notification(MSG.FISCAL_READ_ERROR, "error")
                return

            # Emitir la nota de crédito vía billing_service
            result = await emit_fiscal_document(
                sale_id=orig_sale_id,
                company_id=company_id,
                branch_id=branch_id,
                receipt_type_override=ReceiptType.nota_credito,
                buyer_doc_type=orig_buyer_doc_type,
                buyer_doc_number=orig_buyer_doc_number,
                buyer_name=orig_buyer_name,
                credit_note_reason=reason or "ANULACIÓN",
                original_fiscal_doc_id=orig_id,
            )

            if result and result.fiscal_status == FiscalStatus.authorized:
                self.add_notification(
                    MSG.FISCAL_NC_AUTHORIZED.format(full_number=result.full_number),
                    "success",
                )
            elif result:
                self.add_notification(
                    MSG.FISCAL_NC_STATUS.format(
                        full_number=result.full_number, status=result.fiscal_status,
                    ),
                    "warning",
                )
            else:
                self.add_notification(
                    MSG.FISCAL_NC_FAILED, "error"
                )
        except Exception as exc:
            logger.exception("Error en emit_credit_note: %s", exc)
            self.add_notification(MSG.FISCAL_NC_ERROR, "error")
        finally:
            self.nota_credito_loading = False

        self.load_fiscal_docs()
        self.fiscal_doc_detail_open = False
