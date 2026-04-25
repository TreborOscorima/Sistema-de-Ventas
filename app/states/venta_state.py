"""Estado de Ventas - Interfaz principal del punto de venta.

Este módulo maneja el estado de la pantalla de ventas, incluyendo:

- Carrito de compras (productos, cantidades, precios)
- Selección de método de pago
- Modo crédito con plan de cuotas
- Búsqueda y selección de clientes
- Procesamiento de la venta
- Generación de recibos

Clase principal:
    VentaState: Estado compuesto usando mixins para separar responsabilidades
        - CartMixin: Gestión del carrito
        - PaymentMixin: Métodos de pago
        - ReceiptMixin: Generación de recibos
        - RecentMovesMixin: Movimientos recientes en POS

Flujo típico:
    1. Usuario agrega productos al carrito (CartMixin)
    2. Selecciona método de pago (PaymentMixin)
    3. Opcionalmente selecciona cliente para crédito
    4. Confirma venta -> process_sale()
    5. Se genera recibo (ReceiptMixin)
"""
import json
import reflex as rx
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from sqlmodel import select
from sqlalchemy import or_

from app.constants import (
    CLIENT_SUGGESTIONS_LIMIT,
    DEFAULT_CREDIT_INTERVAL_DAYS,
    DEFAULT_INSTALLMENTS_COUNT,
)
from app.models import Client
from app.schemas.sale_schemas import PaymentInfoDTO, SaleItemDTO
from app.enums import ReceiptType
from app.models.billing import CompanyBillingConfig
from app.services.billing_service import emit_fiscal_document
from app.services.document_lookup_service import (
    determine_ar_cbte_tipo,
    get_cache_ttl,
    lookup_document,
)
from app.models.lookup_cache import DocumentLookupCache
from app.services.sale_service import SaleService, StockError
from app.i18n import MSG
from app.utils.db import get_async_session
from app.utils.logger import get_logger
from app.utils.sanitization import escape_like
from .mixin_state import MixinState
from .venta import CartMixin, PaymentMixin, ReceiptMixin, RecentMovesMixin


logger = get_logger("VentaState")


class VentaState(MixinState, CartMixin, PaymentMixin, ReceiptMixin, RecentMovesMixin):
    """Estado principal de la pantalla de ventas.
    
    Combina múltiples mixins para separar responsabilidades:
    - MixinState: Utilidades comunes (formateo, redondeo)
    - CartMixin: Productos en carrito, agregar/quitar items
    - PaymentMixin: Selección y validación de pagos
    - ReceiptMixin: Generación de recibos HTML
    
    Attributes:
        sale_form_key: Key para resetear formularios
        client_search_query: Término de búsqueda de cliente
        selected_client: Cliente seleccionado para crédito
        is_credit_mode: True si la venta es a crédito
        credit_installments: Número de cuotas
        credit_interval_days: Días entre cuotas
        credit_initial_payment: Pago inicial (adelanto)
        is_processing_sale: Flag para evitar doble-submit
        show_recent_modal: Estado del modal de movimientos recientes
    """
    sale_form_key: int = 0
    client_search_query: str = ""
    client_suggestions: list[dict] = []
    selected_client: dict | None = None
    _active_price_list_id: int = rx.field(default=0, is_var=False)
    is_credit_mode: bool = False
    credit_installments: int = DEFAULT_INSTALLMENTS_COUNT
    credit_interval_days: int = DEFAULT_CREDIT_INTERVAL_DAYS
    credit_initial_payment: str = "0"
    is_processing_sale: bool = False
    sale_receipt_type_selection: str = "nota_venta"

    # ── Fiscal document lookup ─────────────────────────────────
    fiscal_doc_number: str = ""
    fiscal_lookup_result: dict = {}
    fiscal_lookup_loading: bool = False
    fiscal_lookup_error: str = ""
    fiscal_ar_cbte_letra: str = ""  # "A", "B", "C" — auto-determinado

    @rx.var(cache=True)
    def selected_client_credit_available(self) -> float:
        if not self.selected_client:
            return 0.0
        balance = None
        if isinstance(self.selected_client, dict):
            balance = self.selected_client.get("balance")
            if balance is None:
                balance = self.selected_client.get("credit_available")
        if balance is None:
            return 0.0
        available = float(balance)
        if available < 0:
            available = 0
        return self._round_currency(available)

    @rx.var(cache=True)
    def credit_financed_amount(self) -> float:
        if not self.is_credit_mode:
            return 0.0
        try:
            initial_payment = Decimal(str(self.credit_initial_payment or "0"))
        except Exception:
            initial_payment = Decimal("0")
        total = Decimal(str(self.sale_total or 0))
        financed = total - initial_payment
        if financed < 0:
            financed = Decimal("0")
        return self._round_currency(financed)

    @rx.var(cache=True)
    def credit_installment_amount(self) -> float:
        if not self.is_credit_mode:
            return 0.0
        count = self.credit_installments if self.credit_installments > 0 else 1
        return self._round_currency(self.credit_financed_amount / count)

    @rx.event
    def search_client_change(self, query: str):
        self.client_search_query = query or ""
        term = (query or "").strip()
        if len(term) <= 2:
            self.client_suggestions = []
            return
        like_search = f"%{escape_like(term)}%"
        company_id = self.current_user.get("company_id")
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.client_suggestions = []
            return
        with rx.session() as session:
            clients = session.exec(
                select(Client)
                .where(
                    or_(
                        Client.name.ilike(like_search),
                        Client.dni.ilike(like_search),
                    )
                )
                .where(Client.company_id == company_id)
                .where(Client.branch_id == branch_id)
                .limit(CLIENT_SUGGESTIONS_LIMIT)
            ).all()
        self.client_suggestions = [
            {
                "id": client.id,
                "name": client.name,
                "dni": client.dni,
                "price_list_id": client.price_list_id or 0,
                "balance": self._round_currency(
                    float(max(client.credit_limit - client.current_debt, 0))
                ),
            }
            for client in clients
        ]

    @rx.event
    def select_client(self, client_data: dict | Client):
        selected = None
        if isinstance(client_data, Client):
            if hasattr(client_data, "model_dump"):
                selected = client_data.model_dump()
            else:
                selected = client_data.dict()
            balance = client_data.credit_limit - client_data.current_debt
            if balance is None:
                balance = 0
            selected["balance"] = self._round_currency(max(balance, 0))
            selected["price_list_id"] = getattr(client_data, "price_list_id", None) or 0
        elif isinstance(client_data, dict) and client_data:
            selected = dict(client_data)
        self.selected_client = dict(selected) if isinstance(selected, dict) else None
        self._active_price_list_id = int(
            (selected or {}).get("price_list_id") or 0
        )
        self.client_search_query = ""
        self.client_suggestions = []

    @rx.event
    def clear_selected_client(self):
        self.selected_client = None
        self._active_price_list_id = 0

    @rx.event
    def set_sale_receipt_type(self, value: str):
        """Setter para selección manual de tipo de comprobante."""
        self.sale_receipt_type_selection = value or "nota_venta"
        # Limpiar lookup si vuelve a nota_venta
        if value == "nota_venta":
            self._clear_fiscal_lookup()

    @rx.event
    async def lookup_fiscal_document(self, doc_number: str):
        """Consulta RUC/CUIT/DNI en la API fiscal correspondiente.

        Flujo:
        1. Validar input (solo dígitos, mínimo 8 caracteres).
        2. Consultar caché local (DocumentLookupCache) — si TTL vigente, usar.
        3. Llamar API externa vía lookup_document().
        4. Guardar resultado en caché para futuras consultas.
        5. Auto-determinar tipo comprobante AR si aplica.
        """
        doc_number = (doc_number or "").strip().replace("-", "")
        self.fiscal_doc_number = doc_number

        if not doc_number.isdigit() or len(doc_number) < 8:
            self.fiscal_lookup_result = {}
            self.fiscal_lookup_error = ""
            self.fiscal_ar_cbte_letra = ""
            return

        self.fiscal_lookup_loading = True
        self.fiscal_lookup_error = ""
        yield

        try:
            # Obtener config de billing para saber el país y token
            company_id = self._company_id()
            config = None
            if company_id:
                with rx.session() as session:
                    config = session.exec(
                        select(CompanyBillingConfig)
                        .where(CompanyBillingConfig.company_id == company_id)
                    ).first()

            country = (config.country if config else "PE") or "PE"
            country_code = country[:2].upper() if country else "PE"

            # ── Consultar caché local ────────────────────────────
            with rx.session() as session:
                cache_stmt = select(DocumentLookupCache).where(
                    DocumentLookupCache.doc_number == doc_number,
                    DocumentLookupCache.country == country_code,
                )
                cached = session.exec(cache_stmt).first()

                if cached:
                    ttl = get_cache_ttl(cached.doc_type, not cached.not_found)
                    age = (
                        datetime.now(timezone.utc)
                        - cached.fetched_at.replace(tzinfo=timezone.utc)
                    )
                    if age < ttl and not cached.not_found:
                        self.fiscal_lookup_result = {
                            "doc_number": cached.doc_number,
                            "doc_type": cached.doc_type,
                            "legal_name": cached.legal_name,
                            "fiscal_address": cached.fiscal_address,
                            "status": cached.status,
                            "condition": cached.condition,
                            "iva_condition": cached.iva_condition,
                            "iva_condition_code": str(cached.iva_condition_code),
                        }
                        self.fiscal_lookup_error = ""
                        # Auto-determinar tipo comprobante AR desde caché
                        if country_code == "AR" and cached.iva_condition:
                            emisor_iva = (
                                (config.emisor_iva_condition if config else "RI") or "RI"
                            )
                            letra, _ = determine_ar_cbte_tipo(
                                emisor_iva, cached.iva_condition
                            )
                            self.fiscal_ar_cbte_letra = letra
                        else:
                            self.fiscal_ar_cbte_letra = ""
                        self.fiscal_lookup_loading = False
                        return

            # ── Llamar API externa ───────────────────────────────
            result = await lookup_document(
                doc_number=doc_number,
                country=country,
                config=config,
            )

            if result.error and not result.found:
                self.fiscal_lookup_error = result.error
                self.fiscal_lookup_result = {}
                self.fiscal_ar_cbte_letra = ""
            elif result.found:
                self.fiscal_lookup_result = {
                    "doc_number": result.doc_number,
                    "doc_type": result.doc_type,
                    "legal_name": result.legal_name,
                    "fiscal_address": result.fiscal_address,
                    "status": result.status,
                    "condition": result.condition,
                    "iva_condition": result.iva_condition,
                    "iva_condition_code": str(result.iva_condition_code),
                }
                self.fiscal_lookup_error = ""

                # Validar estado para Perú
                if country_code == "PE" and result.doc_type == "RUC":
                    if result.status and result.status != "ACTIVO":
                        self.fiscal_lookup_error = (
                            MSG.LOOKUP_RUC_BAD_STATUS.format(status=result.status)
                        )
                    elif result.condition and result.condition not in ("HABIDO", ""):
                        self.fiscal_lookup_error = (
                            MSG.LOOKUP_RUC_BAD_CONDITION.format(condition=result.condition)
                        )

                # Auto-determinar tipo comprobante AR
                if country_code == "AR" and result.iva_condition:
                    emisor_iva = (config.emisor_iva_condition if config else "RI") or "RI"
                    letra, _ = determine_ar_cbte_tipo(emisor_iva, result.iva_condition)
                    self.fiscal_ar_cbte_letra = letra
                else:
                    self.fiscal_ar_cbte_letra = ""

                # ── Guardar en caché ─────────────────────────────
                try:
                    with rx.session() as session:
                        existing = session.exec(
                            select(DocumentLookupCache).where(
                                DocumentLookupCache.doc_number == doc_number,
                                DocumentLookupCache.country == country_code,
                            )
                        ).first()
                        if existing:
                            existing.legal_name = result.legal_name
                            existing.fiscal_address = result.fiscal_address
                            existing.status = result.status
                            existing.condition = result.condition
                            existing.iva_condition = result.iva_condition
                            existing.iva_condition_code = result.iva_condition_code
                            existing.doc_type = result.doc_type
                            existing.raw_json = json.dumps(
                                result.raw_data, default=str
                            )
                            existing.fetched_at = datetime.now(timezone.utc)
                            existing.not_found = False
                        else:
                            cache_entry = DocumentLookupCache(
                                country=country_code,
                                doc_type=result.doc_type,
                                doc_number=doc_number,
                                legal_name=result.legal_name,
                                fiscal_address=result.fiscal_address,
                                status=result.status,
                                condition=result.condition,
                                iva_condition=result.iva_condition,
                                iva_condition_code=result.iva_condition_code,
                                raw_json=json.dumps(
                                    result.raw_data, default=str
                                ),
                                not_found=False,
                            )
                            session.add(cache_entry)
                        session.commit()
                except Exception:
                    logger.debug("Cache save failed for fiscal lookup %s", doc_number, exc_info=True)
            else:
                self.fiscal_lookup_result = {}
                self.fiscal_lookup_error = MSG.LOOKUP_NOT_FOUND.format(doc_number=doc_number)
                self.fiscal_ar_cbte_letra = ""

                # Cache negativo (not_found)
                try:
                    with rx.session() as session:
                        existing = session.exec(
                            select(DocumentLookupCache).where(
                                DocumentLookupCache.doc_number == doc_number,
                                DocumentLookupCache.country == country_code,
                            )
                        ).first()
                        if existing:
                            existing.not_found = True
                            existing.fetched_at = datetime.now(timezone.utc)
                        else:
                            cache_entry = DocumentLookupCache(
                                country=country_code,
                                doc_type=result.doc_type or "",
                                doc_number=doc_number,
                                not_found=True,
                            )
                            session.add(cache_entry)
                        session.commit()
                except Exception:
                    logger.debug("Negative cache save failed for fiscal lookup %s", doc_number, exc_info=True)
        except Exception as exc:
            logger.exception("lookup_fiscal_document error: %s", exc)
            self.fiscal_lookup_error = MSG.LOOKUP_ERROR
            self.fiscal_lookup_result = {}
        finally:
            self.fiscal_lookup_loading = False

    @rx.event
    def clear_fiscal_lookup(self):
        """Limpia el resultado del lookup fiscal."""
        self._clear_fiscal_lookup()

    def _clear_fiscal_lookup(self):
        """Helper interno para limpiar lookup."""
        self.fiscal_doc_number = ""
        self.fiscal_lookup_result = {}
        self.fiscal_lookup_error = ""
        self.fiscal_lookup_loading = False
        self.fiscal_ar_cbte_letra = ""

    @rx.event
    def toggle_credit_mode(self, value: bool | str):
        if isinstance(value, str):
            value = value.lower() in ["true", "1", "on", "yes"]
        self.is_credit_mode = bool(value)
        if self.is_credit_mode and self.payment_method_kind == "mixed":
            self.payment_mixed_card = 0
            self.payment_mixed_wallet = 0
            self._update_mixed_message()

    @rx.event
    def set_installments_count(self, value: str):
        try:
            count = int(value)
        except (TypeError, ValueError):
            count = 1
        if count < 1:
            count = 1
        self.credit_installments = count

    @rx.event
    def set_payment_interval_days(self, value: str):
        try:
            days = int(value)
        except (TypeError, ValueError):
            days = 30
        if days < 1:
            days = 1
        self.credit_interval_days = days

    @rx.event
    def set_credit_initial_payment(self, value: Any):
        self.credit_initial_payment = str(value or "")
        self.payment_cash_amount = self._safe_amount(self.credit_initial_payment)
        if self.payment_method_kind == "cash":
            self._update_cash_feedback()

    def _reset_credit_context(self):
        self.selected_client = None
        self._active_price_list_id = 0
        self.client_search_query = ""
        self.client_suggestions = []
        self.is_credit_mode = False
        self.credit_initial_payment = ""
        self.credit_installments = DEFAULT_INSTALLMENTS_COUNT
        self.credit_interval_days = DEFAULT_CREDIT_INTERVAL_DAYS
        self.payment_cash_amount = 0
        self.sale_receipt_type_selection = "nota_venta"
        if hasattr(self, "clear_pending_reservation"):
            self.clear_pending_reservation()
        else:
            if hasattr(self, "reservation_payment_id"):
                self.reservation_payment_id = ""
            if hasattr(self, "reservation_payment_amount"):
                self.reservation_payment_amount = ""
            if hasattr(self, "reservation_payment_routed"):
                self.reservation_payment_routed = False

    def _auto_allocate_mixed_amounts(self, total_override: float | None = None):
        if self.is_credit_mode:
            return
        return PaymentMixin._auto_allocate_mixed_amounts(self, total_override)

    @rx.event
    async def confirm_sale(self):
        self.is_loading = True
        self.is_processing_sale = True
        yield
        try:
            if not self.current_user["privileges"]["create_ventas"]:
                self.add_notification(
                    MSG.PERM_SALES, "error"
                )
                return
            block = self._require_active_subscription()
            if block:
                if isinstance(block, list):
                    for action in block:
                        yield action
                else:
                    yield block
                return

            if hasattr(self, "_require_cashbox_open"):
                denial = self._require_cashbox_open()
                if denial:
                    self.add_notification(
                        MSG.CASH_OPEN_REQUIRED_OP, "error"
                    )
                    return

            sale_total_guess = self.sale_total
            username = self.current_user.get("username", "desconocido")
            user_id = self.current_user.get("id")
            logger.info(
                "Inicio de venta usuario=%s id=%s total=%s",
                username,
                user_id,
                sale_total_guess,
            )
            self._refresh_payment_feedback(total_override=sale_total_guess)
            payment_validation_error = self._validate_payment_before_confirm(
                sale_total_guess,
                is_credit=self.is_credit_mode,
            )
            if payment_validation_error:
                self.add_notification(payment_validation_error, "warning")
                yield rx.toast(payment_validation_error, duration=3000)
                return

            payment_summary = self._generate_payment_summary()
            payment_label, payment_breakdown = self._payment_label_and_breakdown(
                sale_total_guess
            )

            payment_data = {
                "summary": payment_summary,
                "method": self.payment_method,
                "method_kind": self.payment_method_kind,
                "label": payment_label,
                "breakdown": payment_breakdown,
                "total": sale_total_guess,
                "cash": {
                    "amount": self._round_currency(max(self.payment_cash_amount, 0)),
                    "message": self.payment_cash_message,
                    "status": self.payment_cash_status,
                },
                "card": {"type": self.payment_card_type},
                "wallet": {
                    "provider": self.payment_wallet_provider
                    or self.payment_wallet_choice,
                    "choice": self.payment_wallet_choice,
                },
                # FIX 41: clamp negative mixed amounts at commit point
                "mixed": {
                    "cash": self._round_currency(max(self.payment_mixed_cash, 0)),
                    "card": self._round_currency(max(self.payment_mixed_card, 0)),
                    "wallet": self._round_currency(max(self.payment_mixed_wallet, 0)),
                    "non_cash_kind": self.payment_mixed_non_cash_kind,
                    "notes": self.payment_mixed_notes,
                    "message": self.payment_mixed_message,
                    "status": self.payment_mixed_status,
                },
            }
            client_id = None
            if isinstance(self.selected_client, dict):
                client_id = self.selected_client.get("id")
            try:
                initial_payment = Decimal(str(self.credit_initial_payment or "0"))
            except Exception:
                initial_payment = Decimal("0")
            # FIX 42: clamp negative initial payment to prevent credit bypass
            if initial_payment < 0:
                initial_payment = Decimal("0")
            payment_data.update(
                {
                    "client_id": client_id,
                    "is_credit": self.is_credit_mode,
                    "installments": self.credit_installments,
                    "interval_days": self.credit_interval_days,
                    "initial_payment": initial_payment,
                }
            )

            try:
                item_dtos = [SaleItemDTO(**item) for item in self.new_sale_items]
                payment_dto = PaymentInfoDTO(**payment_data)
            except Exception as exc:
                error_id = uuid.uuid4().hex[:8]
                logger.warning(
                    "Datos de venta inválidos [%s]: %s",
                    error_id,
                    str(exc),
                )
                self.add_notification(
                    MSG.SALE_INVALID_DATA.format(error_id=error_id), "error"
                )
                return

            reservation_id = None
            if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
                reservation_id = self.reservation_payment_id

            result = None
            async with get_async_session() as session:
                try:
                    result = await SaleService.process_sale(
                        session=session,
                        user_id=user_id,
                        company_id=self.current_user.get("company_id"),
                        branch_id=self._branch_id(),
                        items=item_dtos,
                        payment_data=payment_dto,
                        reservation_id=reservation_id,
                        currency_symbol=self.currency_symbol,
                    )
                    await session.commit()
                    logger.info(
                        "Venta confirmada exitosamente. ID: %s",
                        result.sale.id,
                    )
                except (ValueError, StockError) as exc:
                    await session.rollback()
                    logger.warning("Validacion de venta fallida: %s", exc)
                    self.add_notification(str(exc), "error")
                    return
                except Exception as exc:
                    await session.rollback()
                    error_id = uuid.uuid4().hex[:8]
                    logger.error(
                        "Error critico [%s] al confirmar venta: %s",
                        error_id,
                        str(exc),
                        exc_info=True,
                    )
                    self.add_notification(
                        MSG.SALE_PROCESS_ERROR.format(error_id=error_id),
                        "error",
                    )
                    return

            # ── Capturar datos fiscales ANTES de limpiar el state ──
            # _reset_credit_context() borra selected_client, por lo que
            # debemos extraer tipo de comprobante y datos del comprador aquí.
            fiscal_sale_id = result.sale.id
            fiscal_company_id = self.current_user.get("company_id")
            fiscal_branch_id = self._branch_id()

            # ── Si había un presupuesto pre-cargado, marcarlo como convertido ──
            _pending_quot = int(getattr(self, "_pending_quotation_id", 0) or 0)
            if _pending_quot:
                try:
                    from app.services.quotation_service import QuotationService as _QS
                    await _QS.mark_converted(
                        _pending_quot,
                        fiscal_sale_id,
                        int(fiscal_company_id or 0),
                        int(fiscal_branch_id or 0),
                    )
                except Exception:
                    pass  # non-critical: la venta ya fue registrada
                self._pending_quotation_id = 0

            receipt_type = self._determine_receipt_type(result.sale)
            buyer_doc_type, buyer_doc_number, buyer_name = (
                self._extract_buyer_info()
            )

            # Persistir receipt_type en la Sale para histórico/auditoría.
            # Usa getattr para compatibilidad si la columna aún no existe en la DB.
            _sale_receipt_type_db = getattr(result.sale, "receipt_type", None)
            if receipt_type and not _sale_receipt_type_db:
                try:
                    with rx.session() as sess:
                        from sqlmodel import select as sel_
                        from app.models.sales import Sale as Sale_
                        sale_obj = sess.exec(
                            sel_(Sale_).where(Sale_.id == fiscal_sale_id)
                        ).first()
                        if sale_obj and hasattr(sale_obj, "receipt_type"):
                            sale_obj.receipt_type = receipt_type
                            sess.add(sale_obj)
                            sess.commit()
                except Exception:
                    pass  # Non-critical — fiscal doc has the receipt_type

            # Actualizamos el estado visual (UI) de Reflex.
            self.last_sale_receipt = result.receipt_items
            self.last_sale_reservation_context = result.reservation_context
            self.last_sale_total = result.sale_total_display
            self.last_sale_timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self.last_payment_summary = result.payment_summary
            self.last_sale_id = str(result.sale.id)
            self.sale_receipt_ready = True
            self.show_sale_receipt_modal = True
            self.new_sale_items = []
            self._reset_sale_form()
            self._reset_payment_fields()
            self._reset_credit_context()
            self._refresh_payment_feedback()

            if hasattr(self, "reload_history"):
                self.reload_history()
            if hasattr(self, "_cashbox_update_trigger"):
                self._cashbox_update_trigger += 1

            self.add_notification(MSG.SALE_CONFIRMED, "success")

            # ── Fiscal document emission (fire-and-forget background) ──
            # Solo emitir si el tipo de comprobante NO es nota_venta (ticket
            # interno). Las notas de venta no requieren emisión fiscal.
            if receipt_type and receipt_type != ReceiptType.nota_venta:
                import asyncio
                asyncio.ensure_future(
                    self._fire_fiscal_emission(
                        fiscal_sale_id,
                        fiscal_company_id or 0,
                        fiscal_branch_id or 0,
                        receipt_type,
                        buyer_doc_type,
                        buyer_doc_number,
                        buyer_name,
                    )
                )
            return
        finally:
            self.is_processing_sale = False
            self.is_loading = False

    def _determine_receipt_type(self, sale) -> str:
        """Determina el tipo de comprobante fiscal para la venta.

        IMPORTANTE: Debe llamarse ANTES de _reset_credit_context()
        porque lee self.selected_client para detectar RUC/CUIT.

        Prioridad:
        1. Selección explícita del cajero en el UI (sale_receipt_type_selection).
        2. Campo receipt_type en la venta (si fue asignado programáticamente).
        3. Auto-detección por tipo de documento del cliente.
        4. Default: nota_venta (sin emisión fiscal).
        """
        # 1. Selección manual del usuario en el POS
        if self.sale_receipt_type_selection and self.sale_receipt_type_selection != "nota_venta":
            return self.sale_receipt_type_selection
        # 2. Campo explícito en la venta
        if hasattr(sale, "receipt_type") and sale.receipt_type:
            return sale.receipt_type
        # 3. Auto-detección por fiscal lookup result (RUC/CUIT consultado)
        if self.fiscal_lookup_result and isinstance(self.fiscal_lookup_result, dict):
            doc_type = self.fiscal_lookup_result.get("doc_type", "")
            if doc_type in ("RUC", "CUIT"):
                return ReceiptType.factura
            if doc_type == "DNI":
                return ReceiptType.boleta
        # 4. Auto-detección por RUC/CUIT del cliente seleccionado
        if self.selected_client and isinstance(self.selected_client, dict):
            dni = (self.selected_client.get("dni") or "").strip()
            if len(dni) == 11 and dni.isdigit():
                return ReceiptType.factura
        # 5. Default: nota_venta (ticket interno, sin emisión fiscal)
        return self.sale_receipt_type_selection or ReceiptType.nota_venta

    def _extract_buyer_info(self) -> tuple[str | None, str | None, str | None]:
        """Extrae datos del comprador para el documento fiscal.

        PRIORIDAD 1: Datos del lookup fiscal (SUNAT/AFIP — más autoritativos).
        PRIORIDAD 2: Datos del cliente seleccionado localmente.

        IMPORTANTE: Debe llamarse ANTES de _reset_credit_context()
        porque lee self.selected_client.

        Returns:
            (buyer_doc_type, buyer_doc_number, buyer_name)
        """
        # Prioridad 1: lookup fiscal result
        if self.fiscal_lookup_result and isinstance(self.fiscal_lookup_result, dict):
            doc_num = self.fiscal_lookup_result.get("doc_number", "")
            doc_type_name = self.fiscal_lookup_result.get("doc_type", "")
            legal_name = self.fiscal_lookup_result.get("legal_name", "")

            if doc_num:
                # Mapear tipo de documento a código fiscal
                if doc_type_name == "RUC":
                    fiscal_doc_type = "6"
                elif doc_type_name == "CUIT":
                    fiscal_doc_type = "80"
                elif doc_type_name == "DNI":
                    fiscal_doc_type = "1"
                else:
                    fiscal_doc_type = "0"
                return fiscal_doc_type, doc_num, legal_name or None

        # Prioridad 2: cliente seleccionado localmente
        if not self.selected_client or not isinstance(self.selected_client, dict):
            return None, None, None
        dni = (self.selected_client.get("dni") or "").strip()
        name = (self.selected_client.get("name") or "").strip()
        if not dni:
            return None, None, name or None
        # Clasificar tipo de documento
        if len(dni) == 11 and dni.isdigit():
            doc_type = "6"  # RUC (PE) / CUIT (AR) usa 80 internamente
        elif len(dni) == 8 and dni.isdigit():
            doc_type = "1"  # DNI peruano
        else:
            doc_type = "0"
        return doc_type, dni, name or None

    async def _fire_fiscal_emission(
        self,
        sale_id: int,
        company_id: int,
        branch_id: int,
        receipt_type: str,
        buyer_doc_type: str | None = None,
        buyer_doc_number: str | None = None,
        buyer_name: str | None = None,
    ):
        """Emite el documento fiscal de forma fire-and-forget.

        Se invoca via ``asyncio.ensure_future`` desde ``confirm_sale``
        para no bloquear la UI. Si billing no está configurado, retorna
        silenciosamente. Si falla, el FiscalDocument queda en estado
        ``error`` para reintento manual posterior.
        """
        try:
            fiscal_doc = await emit_fiscal_document(
                sale_id=sale_id,
                company_id=company_id,
                branch_id=branch_id,
                receipt_type=receipt_type,
                buyer_doc_type=buyer_doc_type,
                buyer_doc_number=buyer_doc_number,
                buyer_name=buyer_name,
            )
            if fiscal_doc is not None:
                if fiscal_doc.fiscal_status == "authorized":
                    logger.info(
                        "Documento fiscal %s autorizado para venta %s",
                        fiscal_doc.full_number,
                        sale_id,
                    )
                elif fiscal_doc.fiscal_status in ("error", "rejected"):
                    logger.warning(
                        "Documento fiscal con problemas: status=%s sale_id=%s errors=%s",
                        fiscal_doc.fiscal_status,
                        sale_id,
                        fiscal_doc.fiscal_errors,
                    )
        except Exception as exc:
            logger.exception(
                "Error en _fire_fiscal_emission | sale_id=%s: %s",
                sale_id,
                exc,
            )
