import reflex as rx
from .auth_state import AuthState
from .ui_state import UIState
from .config_state import ConfigState
from .inventory_state import InventoryState
from .ingreso_state import IngresoState
from .venta_state import VentaState
from .cash_state import CashState
from .historial_state import HistorialState
from .services_state import ServicesState

import reflex as rx
from .auth_state import AuthState
from .ui_state import UIState
from .config_state import ConfigState
from .inventory_state import InventoryState
from .ingreso_state import IngresoState
from .venta_state import VentaState
from .cash_state import CashState
from .historial_state import HistorialState
from .services_state import ServicesState

_mixins = [
    ServicesState,
    HistorialState,
    CashState,
    VentaState,
    IngresoState,
    InventoryState,
    ConfigState,
    UIState,
    AuthState,
]

_class_dict = {
    "__module__": __name__,
    "__qualname__": "RootState",
    "__doc__": """
    Root state that combines all modular states via multiple inheritance (Mixins).
    All sub-states are now independent mixins inheriting from MixinState.
    """,
    "__annotations__": {},
}

for _mixin in _mixins:
    # Merge annotations
    if hasattr(_mixin, "__annotations__"):
        _class_dict["__annotations__"].update(_mixin.__annotations__)
    
    # Merge attributes and methods
    for _name, _value in _mixin.__dict__.items():
        if _name.startswith("__"): continue
        _class_dict[_name] = _value

# Create RootState dynamically to ensure BaseStateMeta processes all mixin methods
RootState = type("RootState", (*_mixins, rx.State), _class_dict)

