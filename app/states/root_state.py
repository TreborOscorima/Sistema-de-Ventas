"""
Estado raíz del sistema que combina todos los estados modulares.

Este módulo utiliza herencia múltiple (Mixins) para componer el estado
principal de la aplicación a partir de estados especializados.
"""
import datetime

from app.utils.timezone import country_today_start
from app.utils.tenant import set_tenant_context
from typing import Any

import reflex as rx
from sqlalchemy import func
from sqlmodel import select

from app.models import SaleInstallment
from .auth_state import AuthState
from .ui_state import UIState
from .config_state import ConfigState
from .branches_state import BranchesState
from .inventory_state import InventoryState
from .ingreso_state import IngresoState
from .purchases_state import PurchasesState
from .suppliers_state import SuppliersState
from .venta_state import VentaState
from .cash_state import CashState
from .historial_state import HistorialState
from .services_state import ServicesState
from .cuentas_state import CuentasState
from .clientes_state import ClientesState
from .dashboard_state import DashboardState
from .report_state import ReportState
from .register_state import RegisterState
from .venta import CartMixin, PaymentMixin, ReceiptMixin, RecentMovesMixin

_mixins = [
    ReportState,
    DashboardState,
    ServicesState,
    CuentasState,
    ClientesState,
    SuppliersState,
    PurchasesState,
    HistorialState,
    CashState,
    VentaState,
    IngresoState,
    InventoryState,
    BranchesState,
    ConfigState,
    UIState,
    RegisterState,
    AuthState,
]

@rx.event
def check_overdue_alerts(self):
    company_id = self._company_id() if hasattr(self, "_company_id") else None
    branch_id = self._branch_id() if hasattr(self, "_branch_id") else None
    if not company_id:
        self.overdue_alerts_count = 0
        return
    # Asegura contexto tenant antes de cualquier SELECT.
    set_tenant_context(company_id, branch_id)
    with rx.session() as session:
        settings = {}
        if hasattr(self, "_company_settings_snapshot"):
            settings = self._company_settings_snapshot()
        country_code = settings.get("country_code") or getattr(
            self, "selected_country_code", None
        )
        timezone = settings.get("timezone")
        now = country_today_start(country_code, timezone=timezone)
        statement = (
            select(func.count())
            .select_from(SaleInstallment)
            .where(SaleInstallment.due_date < now)
            .where(func.lower(SaleInstallment.status).not_in(["paid", "completed"]))
        )
        if company_id:
            statement = statement.where(SaleInstallment.company_id == company_id)
        if branch_id:
            statement = statement.where(SaleInstallment.branch_id == branch_id)
        count = session.exec(
            statement.execution_options(
                tenant_company_id=company_id,
                tenant_branch_id=branch_id,
            )
        ).one()
    self.overdue_alerts_count = int(count or 0)

_class_dict = {
    "__module__": __name__,
    "__qualname__": "RootState",
    "__doc__": """
    Estado raiz que combina todos los estados modulares via herencia multiple (Mixins).
    Todos los sub-estados son mixins independientes que heredan de MixinState.
    """,
    "__annotations__": {},
}

for _mixin in _mixins:
    if _mixin is VentaState:
        for _venta_mixin in (CartMixin, PaymentMixin, ReceiptMixin, RecentMovesMixin):
            if hasattr(_venta_mixin, "__annotations__"):
                _class_dict["__annotations__"].update(_venta_mixin.__annotations__)
            for _name, _value in _venta_mixin.__dict__.items():
                if _name.startswith("__"):
                    continue
                _class_dict[_name] = _value

    # Unir anotaciones
    if hasattr(_mixin, "__annotations__"):
        _class_dict["__annotations__"].update(_mixin.__annotations__)
    
    # Unir atributos y metodos
    for _name, _value in _mixin.__dict__.items():
        if _name.startswith("__"): continue
        _class_dict[_name] = _value

_class_dict["__annotations__"]["overdue_alerts_count"] = int
_class_dict["overdue_alerts_count"] = 0
_class_dict["__annotations__"]["is_loading"] = bool
_class_dict["is_loading"] = False
_class_dict["check_overdue_alerts"] = check_overdue_alerts

# Crear RootState dinamicamente para que BaseStateMeta procese todos los metodos mixin
RootState = type("RootState", (*_mixins, rx.State), _class_dict)

