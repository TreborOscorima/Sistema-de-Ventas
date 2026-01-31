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

Flujo típico:
    1. Usuario agrega productos al carrito (CartMixin)
    2. Selecciona método de pago (PaymentMixin)
    3. Opcionalmente selecciona cliente para crédito
    4. Confirma venta -> process_sale()
    5. Se genera recibo (ReceiptMixin)
"""
import reflex as rx
import uuid
from decimal import Decimal
from typing import Any
from sqlmodel import select
from sqlalchemy import or_

from app.models import Client
from app.schemas.sale_schemas import PaymentInfoDTO, SaleItemDTO
from app.services.sale_service import SaleService, StockError
from app.utils.db import get_async_session
from app.utils.logger import get_logger
from .mixin_state import MixinState
from .venta import CartMixin, PaymentMixin, ReceiptMixin


logger = get_logger("VentaState")


class VentaState(MixinState, CartMixin, PaymentMixin, ReceiptMixin):
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
    """
    sale_form_key: int = 0
    client_search_query: str = ""
    client_suggestions: list[dict] = []
    selected_client: dict | None = None
    is_credit_mode: bool = False
    credit_installments: int = 1
    credit_interval_days: int = 30
    credit_initial_payment: str = "0"
    is_processing_sale: bool = False

    @rx.var
    def selected_client_credit_available(self) -> float:
        if not self.selected_client:
            return 0.0
        balance = None
        client_id = None
        if isinstance(self.selected_client, dict):
            balance = self.selected_client.get("balance")
            client_id = self.selected_client.get("id")
        if balance is None and client_id:
            with rx.session() as session:
                company_id = self.current_user.get("company_id")
                branch_id = self._branch_id()
                if not company_id or not branch_id:
                    return 0.0
                client = session.exec(
                    select(Client)
                    .where(Client.id == client_id)
                    .where(Client.company_id == company_id)
                    .where(Client.branch_id == branch_id)
                ).first()
                if not client:
                    return 0.0
                balance = client.credit_limit - client.current_debt
        if balance is None:
            return 0.0
        available = float(balance)
        if available < 0:
            available = 0
        return self._round_currency(available)

    @rx.var
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
        return self._round_currency(float(financed))

    @rx.var
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
        like_search = f"%{term}%"
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
                .limit(6)
            ).all()
        self.client_suggestions = [
            {
                "id": client.id,
                "name": client.name,
                "dni": client.dni,
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
            selected["balance"] = self._round_currency(float(max(balance, 0)))
        elif isinstance(client_data, dict) and client_data:
            selected = dict(client_data)
        self.selected_client = dict(selected) if isinstance(selected, dict) else None
        self.client_search_query = ""
        self.client_suggestions = []

    @rx.event
    def clear_selected_client(self):
        self.selected_client = None

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
        self.client_search_query = ""
        self.client_suggestions = []
        self.is_credit_mode = False
        self.credit_initial_payment = ""
        self.credit_installments = 1
        self.credit_interval_days = 30
        self.payment_cash_amount = 0
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
        self.is_processing_sale = True
        yield
        try:
            if not self.current_user["privileges"]["create_ventas"]:
                yield rx.toast("No tiene permisos para crear ventas.", duration=3000)
                return

            if hasattr(self, "_require_cashbox_open"):
                denial = self._require_cashbox_open()
                if denial:
                    yield denial
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
                    "amount": self._round_currency(self.payment_cash_amount),
                    "message": self.payment_cash_message,
                    "status": self.payment_cash_status,
                },
                "card": {"type": self.payment_card_type},
                "wallet": {
                    "provider": self.payment_wallet_provider
                    or self.payment_wallet_choice,
                    "choice": self.payment_wallet_choice,
                },
                "mixed": {
                    "cash": self._round_currency(self.payment_mixed_cash),
                    "card": self._round_currency(self.payment_mixed_card),
                    "wallet": self._round_currency(self.payment_mixed_wallet),
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
                yield rx.toast(
                    f"Datos de venta inválidos. Código: {error_id}",
                    duration=4000,
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
                    yield rx.toast(str(exc), duration=3000)
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
                    yield rx.toast(
                        f"Error al procesar la venta. Código: {error_id}",
                        duration=5000,
                    )
                    return

            # Actualizamos el estado visual (UI) de Reflex.
            self.last_sale_receipt = result.receipt_items
            self.last_sale_reservation_context = result.reservation_context
            self.last_sale_total = result.sale_total_display
            self.last_sale_timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self.last_payment_summary = result.payment_summary
            self.sale_receipt_ready = True
            self.new_sale_items = []
            self._reset_sale_form()
            self._reset_payment_fields()
            self._reset_credit_context()
            self._refresh_payment_feedback()

            if hasattr(self, "reload_history"):
                self.reload_history()
            if hasattr(self, "_cashbox_update_trigger"):
                self._cashbox_update_trigger += 1

            yield rx.toast("Venta confirmada.", duration=3000)
            return
        finally:
            self.is_processing_sale = False
