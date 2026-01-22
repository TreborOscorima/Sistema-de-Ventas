"""Mixin de Caja Chica para CashState.

Este módulo gestiona los gastos menores (caja chica/petty cash):
- Registro de gastos con cantidad, unidad y costo
- Consulta y paginación de movimientos
- Cálculos automáticos de totales

No modifica lógica de negocio, solo agrupa funcionalidad relacionada.
"""
import datetime
from typing import Any, List

import reflex as rx
import sqlalchemy
from sqlmodel import select, desc

from app.models import CashboxLog as CashboxLogModel, User as UserModel
from app.utils.sanitization import sanitize_notes
from ..types import CashboxLogEntry


class PettyCashMixin:
    """Mixin para gestión de caja chica (gastos menores).
    
    Atributos requeridos del State padre:
        - current_user: dict con username y privileges
        - cashbox_is_open: bool indicando si la caja está abierta
        - _cashbox_update_trigger: int para forzar actualizaciones
        
    Atributos propios (deben declararse en CashState):
        - petty_cash_amount: str
        - petty_cash_quantity: str
        - petty_cash_unit: str
        - petty_cash_cost: str
        - petty_cash_reason: str
        - petty_cash_modal_open: bool
        - petty_cash_current_page: int
        - petty_cash_items_per_page: int
    """

    # =========================================================================
    # EVENTOS DE UI - Paginación y Modales
    # =========================================================================

    @rx.event
    def set_petty_cash_page(self, page: int):
        """Establece la página actual de movimientos de caja chica."""
        if 1 <= page <= self.petty_cash_total_pages:
            self.petty_cash_current_page = page

    @rx.event
    def prev_petty_cash_page(self):
        """Navega a la página anterior."""
        if self.petty_cash_current_page > 1:
            self.petty_cash_current_page -= 1

    @rx.event
    def next_petty_cash_page(self):
        """Navega a la página siguiente."""
        if self.petty_cash_current_page < self.petty_cash_total_pages:
            self.petty_cash_current_page += 1

    @rx.event
    def open_petty_cash_modal(self):
        """Abre el modal de registro de gasto."""
        self.petty_cash_modal_open = True

    @rx.event
    def close_petty_cash_modal(self):
        """Cierra el modal de registro de gasto."""
        self.petty_cash_modal_open = False

    # =========================================================================
    # EVENTOS DE FORMULARIO - Setters
    # =========================================================================

    @rx.event
    def set_petty_cash_amount(self, value: str | int | float):
        """Establece el monto total del gasto."""
        self.petty_cash_amount = str(value)

    @rx.event
    def set_petty_cash_quantity(self, value: Any):
        """Establece la cantidad y recalcula el total."""
        self.petty_cash_quantity = str(value)
        self._calculate_petty_cash_total()

    @rx.event
    def set_petty_cash_unit(self, value: str):
        """Establece la unidad de medida."""
        self.petty_cash_unit = value

    @rx.event
    def set_petty_cash_cost(self, value: Any):
        """Establece el costo unitario y recalcula el total."""
        self.petty_cash_cost = str(value)
        self._calculate_petty_cash_total()

    @rx.event
    def set_petty_cash_reason(self, value: str):
        """Establece el motivo del gasto (sanitizado)."""
        self.petty_cash_reason = sanitize_notes(value)

    # =========================================================================
    # LÓGICA DE CÁLCULO
    # =========================================================================

    def _calculate_petty_cash_total(self):
        """Calcula el monto total: cantidad × costo unitario."""
        try:
            qty = float(self.petty_cash_quantity) if self.petty_cash_quantity else 0
            cost = float(self.petty_cash_cost) if self.petty_cash_cost else 0
            self.petty_cash_amount = str(qty * cost)
        except ValueError:
            pass

    # =========================================================================
    # OPERACIÓN PRINCIPAL - Registro de Movimiento
    # =========================================================================

    @rx.event
    def add_petty_cash_movement(self):
        """Registra un nuevo gasto de caja chica en la base de datos."""
        if not self.current_user["privileges"]["manage_cashbox"]:
            return rx.toast("No tiene permisos para gestionar la caja.", duration=3000)
        if not self.cashbox_is_open:
            return rx.toast("Debe aperturar la caja para registrar movimientos.", duration=3000)
        
        try:
            amount = float(self.petty_cash_amount)
            if amount <= 0:
                return rx.toast("El monto total debe ser mayor a 0.", duration=3000)
            
            quantity = float(self.petty_cash_quantity) if self.petty_cash_quantity else 1.0
            cost = float(self.petty_cash_cost) if self.petty_cash_cost else amount
            
        except ValueError:
            return rx.toast("Valores numéricos inválidos.", duration=3000)
            
        if not self.petty_cash_reason:
            return rx.toast("Ingrese un motivo.", duration=3000)
            
        username = self.current_user["username"]
        
        with rx.session() as session:
            user = session.exec(select(UserModel).where(UserModel.username == username)).first()
            if not user:
                return rx.toast("Usuario no encontrado.", duration=3000)
                
            log = CashboxLogModel(
                user_id=user.id,
                action="gasto_caja_chica",
                amount=amount,
                quantity=quantity,
                unit=self.petty_cash_unit,
                cost=cost,
                notes=self.petty_cash_reason,
                timestamp=datetime.datetime.now()
            )
            session.add(log)
            session.commit()
            
        # Limpiar formulario
        self.petty_cash_amount = ""
        self.petty_cash_quantity = "1"
        self.petty_cash_cost = ""
        self.petty_cash_unit = "Unidad"
        self.petty_cash_reason = ""
        self.petty_cash_modal_open = False
        self._cashbox_update_trigger += 1
        return rx.toast("Movimiento registrado correctamente.", duration=3000)

    # =========================================================================
    # QUERIES Y FETCH
    # =========================================================================

    def _petty_cash_query(self):
        """Query base para obtener movimientos de caja chica."""
        return (
            select(CashboxLogModel, UserModel.username)
            .join(UserModel)
            .where(CashboxLogModel.action == "gasto_caja_chica")
            .order_by(desc(CashboxLogModel.timestamp))
        )

    def _petty_cash_count(self) -> int:
        """Cuenta total de movimientos de caja chica."""
        statement = (
            select(sqlalchemy.func.count())
            .select_from(CashboxLogModel)
            .where(CashboxLogModel.action == "gasto_caja_chica")
        )
        with rx.session() as session:
            return session.exec(statement).one()

    def _fetch_petty_cash(
        self, offset: int | None = None, limit: int | None = None
    ) -> List[CashboxLogEntry]:
        """Obtiene movimientos de caja chica con paginación opcional."""
        with rx.session() as session:
            statement = self._petty_cash_query()
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)
            results = session.exec(statement).all()

            filtered: List[CashboxLogEntry] = []
            for log, username in results:
                qty = log.quantity or 1.0
                cost = log.cost or log.amount

                # Formatear cantidad: entero si no hay decimales, si no 2 decimales
                fmt_qty = f"{int(qty)}" if qty % 1 == 0 else f"{qty:.2f}"

                entry: CashboxLogEntry = {
                    "id": str(log.id),
                    "action": log.action,
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": username,
                    "opening_amount": 0.0,
                    "closing_total": 0.0,
                    "totals_by_method": [],
                    "notes": log.notes,
                    "amount": log.amount,
                    "quantity": qty,
                    "unit": log.unit or "Unidad",
                    "cost": cost,
                    "formatted_amount": f"{log.amount:.2f}",
                    "formatted_cost": f"{cost:.2f}",
                    "formatted_quantity": fmt_qty,
                }
                filtered.append(entry)
            return filtered

    # =========================================================================
    # VARIABLES COMPUTADAS (rx.var)
    # =========================================================================

    @rx.var
    def petty_cash_movements(self) -> List[CashboxLogEntry]:
        """Lista paginada de movimientos de caja chica."""
        _ = self._cashbox_update_trigger
        page = max(self.petty_cash_current_page, 1)
        per_page = max(self.petty_cash_items_per_page, 1)
        offset = (page - 1) * per_page
        return self._fetch_petty_cash(offset=offset, limit=per_page)

    @rx.var
    def paginated_petty_cash_movements(self) -> List[CashboxLogEntry]:
        """Alias de petty_cash_movements para compatibilidad."""
        return self.petty_cash_movements

    @rx.var
    def petty_cash_total_pages(self) -> int:
        """Total de páginas de movimientos de caja chica."""
        _ = self._cashbox_update_trigger
        total = self._petty_cash_count()
        if total == 0:
            return 1
        return (total + self.petty_cash_items_per_page - 1) // self.petty_cash_items_per_page
