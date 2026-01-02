import reflex as rx
from app.schemas.sale_schemas import PaymentInfoDTO, SaleItemDTO
from app.services.sale_service import SaleService, StockError
from .mixin_state import MixinState
from .venta import CartMixin, PaymentMixin, ReceiptMixin

# ✅ NUEVO: Importamos el gestor de sesión asíncrona (el "Carril Rápido")
from app.utils.db import get_async_session 

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

        # ✅ BLOQUE CRÍTICO ACTUALIZADO (CARRIL RÁPIDO)
        # Usamos async with para abrir la conexión asíncrona segura
        async with get_async_session() as session:
            try:
                # Pasamos la 'session' explícitamente al servicio
                result = await SaleService.process_sale(
                    session=session,  # <--- Esto es vital
                    user_id=self.current_user.get("id"),
                    items=item_dtos,
                    payment_data=payment_dto,
                    reservation_id=reservation_id,
                )
                
                # Si todo sale bien, confirmamos la transacción en la BD
                await session.commit() 

            except (ValueError, StockError) as exc:
                # Si falla por lógica de negocio (stock, validación), cancelamos
                await session.rollback()
                return rx.toast(str(exc), duration=3000)
            except Exception as e:
                # Si falla por error técnico, cancelamos y logueamos
                await session.rollback()
                print(f"Error crítico en venta: {e}")
                return rx.toast("No se pudo procesar la venta.", duration=3000)

        # Si llegamos aquí, la venta se guardó correctamente en la BD.
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