import reflex as rx
from app.schemas.sale_schemas import PaymentInfoDTO, SaleItemDTO
from app.services.sale_service import SaleService, StockError
from app.utils.logger import get_logger
from .mixin_state import MixinState
from .venta import CartMixin, PaymentMixin, ReceiptMixin



logger = get_logger("VentaState")
class VentaState(MixinState, CartMixin, PaymentMixin, ReceiptMixin):
    sale_form_key: int = 0

    @rx.event
    async def confirm_sale(self):
        if not self.current_user["privileges"]["create_ventas"]:
            return rx.toast("No tiene permisos para crear ventas.", duration=3000)

        if hasattr(self, "_require_cashbox_open"):
            denial = self._require_cashbox_open()
            if denial:
                return denial

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
                "provider": self.payment_wallet_provider or self.payment_wallet_choice,
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

        try:
            item_dtos = [SaleItemDTO(**item) for item in self.new_sale_items]
            payment_dto = PaymentInfoDTO(**payment_data)
        except Exception:
            return rx.toast("Datos de venta invalidos.", duration=3000)

        reservation_id = None
        if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
            reservation_id = self.reservation_payment_id

        try:
            result = await SaleService.process_sale(
                user_id=self.current_user.get("id"),
                items=item_dtos,
                payment_data=payment_dto,
                reservation_id=reservation_id,
            )
            logger.info(
                "✅ Venta confirmada exitosamente. ID: %s",
                result.sale.id,
            )
        except (ValueError, StockError) as exc:
            logger.warning("Validacion de venta fallida: %s", exc)
            return rx.toast(str(exc), duration=3000)
        except Exception:
            logger.error("Error critico al confirmar venta.", exc_info=True)
            return rx.toast("No se pudo procesar la venta.", duration=3000)

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
        self._refresh_payment_feedback()

        if hasattr(self, "reload_history"):
            self.reload_history()
        if hasattr(self, "_cashbox_update_trigger"):
            self._cashbox_update_trigger += 1

        return rx.toast("Venta confirmada.", duration=3000)
