"""Inventory State — paquete compuesto por mixins de responsabilidad única.

InventoryState se construye combinando mixins vía herencia múltiple.
El orden de herencia es importante: MRO resuelve de izquierda a derecha.
"""
from typing import List, Dict, Any

import reflex as rx
from app.constants import DEFAULT_ITEMS_PER_PAGE, INVENTORY_RECENT_LIMIT
from ..mixin_state import MixinState
from ..types import InventoryAdjustment

from ._search_mixin import SearchMixin
from ._product_mixin import ProductMixin
from ._adjustment_mixin import AdjustmentMixin
from ._export_mixin import ExportMixin
from ._label_mixin import LabelMixin

# Re-export constants for backwards compatibility (dashboard_state, etc.)
DEFAULT_LOW_STOCK_THRESHOLD = 5
LOW_STOCK_THRESHOLD = DEFAULT_LOW_STOCK_THRESHOLD


class InventoryState(
    LabelMixin,
    ExportMixin,
    AdjustmentMixin,
    ProductMixin,
    SearchMixin,
    MixinState,
):
    """Estado de gestión de inventario y productos.

    Maneja productos, categorías, ajustes de stock y reportes.
    Los productos se persisten en BD, no en memoria de estado.
    """

    # ── State variables (shared across mixins) ───────────────────
    new_category_name: str = ""
    new_category_input_key: int = 0
    inventory_search_term: str = ""
    inventory_current_page: int = 1
    inventory_items_per_page: int = DEFAULT_ITEMS_PER_PAGE
    inventory_recent_limit: int = INVENTORY_RECENT_LIMIT

    editing_product: Dict[str, Any] = {
        "id": None,
        "barcode": "",
        "description": "",
        "category": "",
        "stock": 0,
        "unit": "",
        "purchase_price": 0,
        "sale_price": 0,
    }
    is_editing_product: bool = False
    show_variants: bool = False
    show_wholesale: bool = False
    show_batches: bool = False
    show_attributes: bool = False
    show_kit_components: bool = False
    confirm_disable_wholesale: bool = False
    variants: List[Dict[str, Any]] = []
    price_tiers: List[Dict[str, Any]] = []
    batches: List[Dict[str, Any]] = []
    attributes: List[Dict[str, Any]] = []
    kit_components: List[Dict[str, Any]] = []
    stock_details_open: bool = False
    stock_details_title: str = ""
    stock_details_mode: str = "simple"
    selected_product_details: List[Dict[str, Any]] = []

    inventory_check_modal_open: bool = False
    inventory_check_status: str = "perfecto"
    inventory_adjustment_notes: str = ""
    inventory_adjustment_item: InventoryAdjustment = {
        "temp_id": "",
        "barcode": "",
        "description": "",
        "category": "",
        "unit": "",
        "current_stock": 0,
        "adjust_quantity": 0,
        "reason": "",
        "product_id": None,
        "variant_id": None,
    }
    inventory_adjustment_items: List[InventoryAdjustment] = []
    inventory_adjustment_suggestions: List[Dict[str, Any]] = []
    categories: List[str] = ["General"]
    _categories_loaded_once: bool = rx.field(default=False, is_var=False)
    categories_panel_expanded: bool = False
    show_inactive_products: bool = False
    _inventory_update_trigger: int = 0
    inventory_list: list[dict] = []
    inventory_total_pages: int = 1
    inventory_total_products: int = 0
    inventory_in_stock_count: int = 0
    inventory_low_stock_count: int = 0
    inventory_out_of_stock_count: int = 0

    # ── Importación masiva ──
    import_modal_open: bool = False
    import_preview_rows: list[dict] = []
    import_errors: list[str] = []
    import_stats: dict = {"new": 0, "updated": 0, "errors": 0, "total": 0}
    import_processing: bool = False
    import_file_name: str = ""


__all__ = ["InventoryState"]
