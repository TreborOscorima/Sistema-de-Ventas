import asyncio
import logging
import uuid
from typing import Any, Dict, List, TypedDict, Union

import reflex as rx
from decimal import Decimal, ROUND_HALF_UP

from sqlmodel import select as sql_select

from app.constants import PRODUCT_SUGGESTIONS_LIMIT
from app.models.inventory import Category, ProductBatch, ProductKit, ProductVariant
from app.services.sale_service import SaleService
from app.utils.barcode import clean_barcode, validate_barcode
from app.utils.db import get_async_session
from ..types import TransactionItem


class _VariantPickerCell(TypedDict):
    variant_id: int | None
    color: str
    stock: float
    sku: str
    is_placeholder: bool
    available: bool


class _VariantPickerRow(TypedDict):
    size: str
    cells: List[_VariantPickerCell]


class CartMixin:
    """Mixin para la gestión del carrito de ventas.

    Maneja búsqueda de productos, autocompletado, agregar/quitar ítems,
    validación de stock y aplicación de precios por nivel.
    """

    new_sale_item: Dict[str, Any] = {
        "temp_id": "",
        "barcode": "",
        "description": "",
        "category": "General",
        "quantity": 0,
        "unit": "Unidad",
        "price": 0,
        "sale_price": 0,
        "base_price": 0,
        "subtotal": 0,
        "product_id": None,
        "variant_id": None,
        "batch_id": None,
        "batch_number": "",
        "requires_batch": False,
        "kit_product_id": None,
        "kit_name": "",
        "promotion_name": "",
    }
    new_sale_items: List[Dict[str, Any]] = []
    autocomplete_suggestions: List[str] = []
    autocomplete_results: List[Dict[str, Any]] = []
    autocomplete_selected_index: int = -1
    selected_product: Dict[str, Any] | None = None
    last_scanned_label: str = ""
    product_grid_items: List[Dict[str, Any]] = []
    product_grid_search: str = ""
    wholesale_price_applied: bool = False

    # ── Selector manual de lote (POS) ───────────────────────────
    # Permite al cajero cambiar el lote auto-asignado por FEFO desde
    # el carrito (útil cuando el cliente pide un lote específico).
    batch_picker_open: bool = False
    batch_picker_temp_id: str = ""
    batch_picker_description: str = ""
    batch_picker_options: List[Dict[str, Any]] = []
    batch_picker_loading: bool = False

    # ── Selector visual de variante (POS) ───────────────────────
    # Grilla talla × color para productos con variantes (ropa/juguetería).
    # Se abre automáticamente al elegir un producto padre con variantes.
    variant_picker_open: bool = False
    variant_picker_product_id: int | None = None
    variant_picker_description: str = ""
    variant_picker_loading: bool = False
    variant_picker_colors: List[str] = []
    variant_picker_rows: List[_VariantPickerRow] = []

    # Visual feedback: precio resuelto desde lista asignada al cliente
    price_list_price_applied: bool = False
    # Visual feedback: promoción activa aplicada al ítem en carrito
    promotion_applied: bool = False
    promotion_name: str = ""

    # Cupón ingresado por el cajero/cliente. Vacío = sólo promos automáticas.
    # Se normaliza a mayúsculas en el setter.
    cart_coupon_code: str = ""
    cart_coupon_status: str = ""  # "", "applied", "invalid"
    cart_coupon_message: str = ""

    _autocomplete_debounce_seq: int = rx.field(default=0, is_var=False)

    async def _process_barcode(self, barcode: str):
        """Lógica compartida para procesar un código de barras."""
        company_id = None
        branch_id = None
        if hasattr(self, "current_user"):
            company_id = self.current_user.get("company_id")
        if hasattr(self, "_branch_id"):
            branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(
                "Empresa o sucursal no definida.",
                duration=3000,
            )
        product = await SaleService.get_product_by_barcode(
            barcode,
            int(company_id),
            int(branch_id),
        )
        if product:
            # Detectar kit: si tiene componentes, expandir en carrito
            prod_id = product.get("product_id") or product.get("id")
            if prod_id and not product.get("is_variant"):
                async with get_async_session() as session:
                    kit_exists = (
                        await session.exec(
                            sql_select(ProductKit.id)
                            .where(
                                ProductKit.kit_product_id == int(prod_id),
                                ProductKit.company_id == int(company_id),
                                ProductKit.branch_id == int(branch_id),
                            )
                            .limit(1)
                        )
                    ).first()
                if kit_exists:
                    return await self._add_kit_to_cart(
                        product, company_id, branch_id
                    )
            if self.new_sale_item.get("quantity", 0) <= 0:
                self.new_sale_item["quantity"] = 1
            self._set_last_scanned_label(product)
            return await self.add_item_to_sale(product_override=product)
        return rx.toast(
            "Producto no encontrado o sin stock disponible.",
            duration=3000,
        )

    @rx.event
    async def handle_barcode_form_submit(self, form_data: dict):
        """Maneja el submit del formulario de código de barras (Enter del scanner)."""
        barcode = str(form_data.get("barcode", "") or "").strip()
        if barcode:
            return await self._process_barcode(barcode)
        return await self.add_item_to_sale()

    @rx.event
    async def handle_key_down(self, key: str):
        if key == "Enter":
            barcode = str(self.new_sale_item.get("barcode", "") or "").strip()
            if barcode:
                return await self._process_barcode(barcode)
            return await self.add_item_to_sale()

    @rx.var(cache=True)
    def sale_subtotal(self) -> float:
        return self.new_sale_item["subtotal"]

    @rx.var(cache=True)
    def sale_total(self) -> float:
        # Evita lecturas a BD durante render reactivo. Usa estado ya cargado.
        reservation_balance = 0.0
        if hasattr(self, "reservation_payment_id") and self.reservation_payment_id:
            if hasattr(self, "reservation_payment_amount"):
                reservation_balance = self._safe_amount(
                    getattr(self, "reservation_payment_amount", "0")
                )
            if (
                reservation_balance <= 0
                and hasattr(self, "selected_reservation_balance")
            ):
                reservation_balance = self._round_currency(
                    float(getattr(self, "selected_reservation_balance", 0) or 0)
                )
            if reservation_balance < 0:
                reservation_balance = 0.0

        products_total = sum((item["subtotal"] for item in self.new_sale_items))
        return self._round_currency(products_total + reservation_balance)

    def _apply_item_rounding(self, item: TransactionItem):
        unit = item.get("unit", "")
        item["quantity"] = self._normalize_quantity_value(item.get("quantity", 0), unit)
        item["price"] = self._round_currency(item.get("price", 0))
        if "sale_price" in item:
            item["sale_price"] = self._round_currency(item.get("sale_price", 0))
        item["subtotal"] = self._round_currency(item["quantity"] * item["price"])

    def _product_value(self, product: Any, key: str, default: Any = None) -> Any:
        if isinstance(product, dict):
            return product.get(key, default)
        return getattr(product, key, default)

    def _set_last_scanned_label(self, product: Any):
        description = self._product_value(product, "description", "")
        unit = self._product_value(product, "unit", "")
        stock = self._product_value(product, "stock", 0)
        try:
            stock_display = self._normalize_quantity_value(stock, unit)
        except Exception:
            stock_display = stock
        price = self._round_currency(self._product_value(product, "sale_price", 0))
        currency = getattr(self, "currency_symbol", "S/")
        self.last_scanned_label = (
            f"{description} | Stock: {stock_display} | {currency}{price}"
        )

    async def _apply_price_tier(
        self,
        product: Any | None = None,
        quantity_override: float | Decimal | None = None,
    ) -> Decimal | None:
        """Resuelve el precio efectivo del ítem en el formulario de venta.

        Usa ``resolve_effective_price`` (la misma función que ``_recompute_cart_prices``
        y ``sale_service``) para garantizar que el precio del carrito siempre coincida
        con el que se cobrará al confirmar la venta.
        """
        from app.models import Product as ProductModel
        from app.services.pricing import PriceSource, resolve_effective_price

        product = product or self.selected_product
        if not product:
            return None
        product_id = self._product_value(
            product,
            "product_id",
            self._product_value(product, "id", None),
        )
        if not product_id:
            return None
        variant_id = self._product_value(product, "variant_id", None)
        if variant_id is None:
            variant_id = self.new_sale_item.get("variant_id")
        qty = quantity_override
        if qty is None:
            qty = self.new_sale_item.get("quantity", 0)
        if not qty or qty <= 0:
            return None
        company_id = self._company_id() if hasattr(self, "_company_id") else None
        branch_id = self._branch_id() if hasattr(self, "_branch_id") else None
        if not company_id or not branch_id:
            return None

        coupon_status = getattr(self, "cart_coupon_status", "")
        coupon = (
            getattr(self, "cart_coupon_code", "") or None
        ) if coupon_status == "applied" else None
        price_list_id = int(getattr(self, "_active_price_list_id", 0) or 0) or None

        # Subtotal pre-promo del carrito para evaluar promos con min_cart_amount.
        cart_subtotal_pre_promo = Decimal("0.00")
        for existing in self.new_sale_items:
            existing_qty = Decimal(str(existing.get("quantity") or 0))
            existing_base = Decimal(
                str(existing.get("base_price") or existing.get("sale_price") or 0)
            )
            cart_subtotal_pre_promo += existing_qty * existing_base
        qty_dec = Decimal(str(qty))

        try:
            async with get_async_session() as session:
                orm_product = (
                    await session.exec(
                        sql_select(ProductModel)
                        .where(ProductModel.id == int(product_id))
                        .where(ProductModel.company_id == int(company_id))
                        .where(ProductModel.branch_id == int(branch_id))
                    )
                ).first()
                if not orm_product:
                    return None

                # Primer pass: precio base sin promo para obtener el subtotal correcto.
                base_res = await resolve_effective_price(
                    session,
                    product=orm_product,
                    variant_id=int(variant_id) if variant_id else None,
                    quantity=qty_dec,
                    company_id=int(company_id),
                    branch_id=int(branch_id),
                    client_price_list_id=price_list_id,
                    coupon_code=None,
                    cart_subtotal=None,
                )
                cart_subtotal_pre_promo += qty_dec * base_res.base_price

                # Segundo pass: resolución completa con promo y subtotal real.
                resolution = await resolve_effective_price(
                    session,
                    product=orm_product,
                    variant_id=int(variant_id) if variant_id else None,
                    quantity=qty_dec,
                    company_id=int(company_id),
                    branch_id=int(branch_id),
                    client_price_list_id=price_list_id,
                    coupon_code=coupon,
                    cart_subtotal=cart_subtotal_pre_promo,
                )
        except Exception:
            logging.exception("Error resolving effective price for product %s", product_id)
            return None

        price_from_list = resolution.source == PriceSource.PRICE_LIST
        price_from_tier = resolution.source == PriceSource.TIER
        promo = resolution.applied_promotion
        promo_name = promo.name if promo else ""

        self.new_sale_item["price"] = self._round_currency(resolution.final_price)
        self.new_sale_item["sale_price"] = self._round_currency(resolution.final_price)
        self.new_sale_item["base_price"] = self._round_currency(resolution.base_price)
        self.new_sale_item["subtotal"] = self._round_currency(
            self.new_sale_item["quantity"] * self.new_sale_item["price"]
        )
        self.price_list_price_applied = price_from_list
        self.wholesale_price_applied = price_from_tier and not price_from_list
        self.promotion_applied = bool(promo_name)
        self.promotion_name = promo_name
        self.new_sale_item["promotion_name"] = promo_name

        return Decimal(str(resolution.final_price))

    def _fill_sale_item_from_product(
        self,
        product: Any,
        keep_quantity: bool = False,
    ):
        product_barcode = self._product_value(product, "barcode", "")
        description = self._product_value(product, "description", "")
        category = self._product_value(product, "category", "General")
        unit = self._product_value(product, "unit", "Unidad")
        sale_price = self._product_value(product, "sale_price", 0)
        product_id = self._product_value(product, "product_id", None)
        variant_id = self._product_value(product, "variant_id", None)
        if product_id is None:
            product_id = self._product_value(product, "id", None)

        quantity = (
            self.new_sale_item["quantity"]
            if keep_quantity and self.new_sale_item["quantity"] > 0
            else 1
        )

        self.new_sale_item["product_id"] = product_id
        self.new_sale_item["variant_id"] = variant_id
        self.new_sale_item["barcode"] = product_barcode
        self.new_sale_item["description"] = description
        self.new_sale_item["category"] = category
        self.new_sale_item["unit"] = unit
        self.new_sale_item["quantity"] = self._normalize_quantity_value(
            quantity, unit
        )
        self.new_sale_item["price"] = self._round_currency(sale_price)
        self.new_sale_item["sale_price"] = self._round_currency(sale_price)
        self.new_sale_item["subtotal"] = self._round_currency(
            self.new_sale_item["quantity"] * self.new_sale_item["price"]
        )
        if isinstance(product, dict):
            self.selected_product = dict(product)

        # Incrementa key para forzar re-render de inputs uncontrolled
        self.sale_form_key += 1

        if not keep_quantity:
            self.autocomplete_suggestions = []
            self.autocomplete_results = []

        logging.info(
            "[FILL-SALE] C▃igo corregido: escaneado incompleto  '%s' completo (producto: %s)",
            product_barcode,
            description,
        )

    async def _resolve_batch_info(self, product: Any, company_id: Any, branch_id: Any):
        """Resuelve información de lote FEFO para el ítem actual.

        Si la categoría del producto requiere lote obligatorio, busca
        el lote más próximo a vencer (FEFO) y lo asigna al ítem.
        """
        if not product or not company_id or not branch_id:
            return
        category = self._product_value(product, "category", "General")
        product_id = self._product_value(
            product, "product_id", self._product_value(product, "id", None)
        )
        variant_id = self._product_value(product, "variant_id", None)
        if not product_id:
            return

        try:
            async with get_async_session() as session:
                # Verificar si la categoría requiere lote
                cat_row = (
                    await session.exec(
                        sql_select(Category)
                        .where(Category.company_id == int(company_id))
                        .where(Category.branch_id == int(branch_id))
                        .where(Category.name == category)
                    )
                ).first()
                requires = bool(cat_row and cat_row.requires_batch)
                self.new_sale_item["requires_batch"] = requires

                if not requires:
                    return

                # Buscar lote FEFO (primero por variante, luego por producto)
                if variant_id:
                    batch_q = sql_select(ProductBatch).where(
                        ProductBatch.product_variant_id == int(variant_id),
                        ProductBatch.stock > 0,
                        ProductBatch.company_id == int(company_id),
                        ProductBatch.branch_id == int(branch_id),
                    )
                else:
                    batch_q = sql_select(ProductBatch).where(
                        ProductBatch.product_id == int(product_id),
                        ProductBatch.stock > 0,
                        ProductBatch.company_id == int(company_id),
                        ProductBatch.branch_id == int(branch_id),
                    )
                batch_q = batch_q.order_by(
                    ProductBatch.expiration_date.is_(None),
                    ProductBatch.expiration_date.asc(),
                    ProductBatch.id.asc(),
                ).limit(1)
                batch = (await session.exec(batch_q)).first()
                if batch:
                    self.new_sale_item["batch_id"] = batch.id
                    self.new_sale_item["batch_number"] = batch.batch_number or ""
        except Exception:
            logging.exception("Error resolviendo lote FEFO para item")

    async def _add_kit_to_cart(self, kit_product, company_id, branch_id):
        """Expande un kit en sus componentes y los agrega al carrito.

        Cada componente se agrega como ítem separado para trazabilidad
        individual en SaleItem y descuento de stock uno a uno.
        El precio del kit (Product.sale_price) se distribuye proporcionalmente
        según el peso (sale_price × qty) de cada componente.
        """
        from app.models import Product as ProductModel

        kit_id = self._product_value(kit_product, "product_id", None) or self._product_value(kit_product, "id", None)
        kit_name = self._product_value(kit_product, "description", "Kit")
        kit_price = Decimal(str(self._product_value(kit_product, "sale_price", 0) or 0))

        async with get_async_session() as session:
            components = (
                await session.exec(
                    sql_select(ProductKit).where(
                        ProductKit.kit_product_id == int(kit_id),
                        ProductKit.company_id == int(company_id),
                        ProductKit.branch_id == int(branch_id),
                    )
                )
            ).all()
            if not components:
                return rx.toast("Kit sin componentes configurados.", duration=3000)

            component_ids = [c.component_product_id for c in components]
            products = (
                await session.exec(
                    sql_select(ProductModel).where(
                        ProductModel.id.in_(component_ids),
                        ProductModel.company_id == int(company_id),
                        ProductModel.branch_id == int(branch_id),
                    )
                )
            ).all()
            product_map = {p.id: p for p in products}

            for comp in components:
                if comp.component_product_id not in product_map:
                    return rx.toast(
                        f"Componente del kit no encontrado (ID: {comp.component_product_id}).",
                        duration=3000,
                    )

            # Validar stock de cada componente (considerando lo ya en carrito)
            for comp in components:
                p = product_map[comp.component_product_id]
                available = await SaleService.get_available_stock(
                    int(p.id), None, int(company_id), int(branch_id),
                )
                needed = float(comp.quantity)
                in_cart = sum(
                    float(item.get("quantity", 0))
                    for item in self.new_sale_items
                    if item.get("product_id") == p.id and not item.get("variant_id")
                )
                if float(available or 0) < needed + in_cart:
                    return rx.toast(
                        f"Stock insuficiente de '{p.description}' para armar el kit.",
                        duration=3000,
                    )

            # Calcular peso proporcional para distribuir precio del kit
            total_weight = sum(
                float(product_map[c.component_product_id].sale_price or 0) * float(c.quantity)
                for c in components
            )

            items_added = []
            remaining_price = kit_price

            for i, comp in enumerate(components):
                p = product_map[comp.component_product_id]
                qty = float(comp.quantity)

                if i == len(components) - 1:
                    component_subtotal = remaining_price
                elif total_weight > 0:
                    weight = Decimal(str(float(p.sale_price or 0) * qty))
                    component_subtotal = (kit_price * weight / Decimal(str(total_weight))).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    remaining_price -= component_subtotal
                else:
                    component_subtotal = (kit_price / len(components)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    remaining_price -= component_subtotal

                unit_price = (component_subtotal / Decimal(str(qty))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                item = {
                    "temp_id": str(uuid.uuid4()),
                    "barcode": p.barcode or "",
                    "description": p.description or "",
                    "category": p.category or "General",
                    "quantity": self._normalize_quantity_value(qty, p.unit or "Unidad"),
                    "unit": p.unit or "Unidad",
                    "price": float(unit_price),
                    "sale_price": float(unit_price),
                    "base_price": float(unit_price),
                    "subtotal": float(component_subtotal),
                    "product_id": p.id,
                    "variant_id": None,
                    "batch_id": None,
                    "batch_number": "",
                    "requires_batch": False,
                    "kit_product_id": int(kit_id),
                    "kit_name": str(kit_name),
                    "promotion_name": "",
                }
                self._apply_item_rounding(item)
                items_added.append(item)

        self.new_sale_items = [*self.new_sale_items, *items_added]
        self._reset_sale_form()
        self._refresh_payment_feedback()
        return [
            rx.toast(
                f"Kit '{kit_name}' agregado ({len(items_added)} componentes)",
                duration=2000,
            ),
            rx.call_script(
                "setTimeout(() => { const el = document.getElementById('venta_barcode_input'); if (el) { el.focus(); el.select(); } }, 0);"
            ),
        ]

    @rx.event
    async def open_batch_picker(self, temp_id: str):
        """Abre el modal de selección manual de lote para un ítem del carrito.

        Carga todos los lotes disponibles (stock > 0) del producto/variante,
        ordenados FEFO (vencimiento ascendente). El cajero puede elegir uno
        distinto al que asignó FEFO automáticamente.
        """
        item = next(
            (it for it in self.new_sale_items if it.get("temp_id") == temp_id),
            None,
        )
        if not item:
            return rx.toast("Producto no encontrado en el carrito.", duration=3000)

        product_id = item.get("product_id")
        variant_id = item.get("variant_id")
        if not product_id and not variant_id:
            return rx.toast(
                "El producto no tiene identificador de stock.", duration=3000
            )

        company_id = None
        branch_id = None
        if hasattr(self, "current_user"):
            company_id = self.current_user.get("company_id")
        if hasattr(self, "_branch_id"):
            branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa o sucursal no definida.", duration=3000)

        self.batch_picker_temp_id = temp_id
        self.batch_picker_description = str(item.get("description", "") or "")
        self.batch_picker_options = []
        self.batch_picker_loading = True
        self.batch_picker_open = True
        try:
            async with get_async_session() as session:
                if variant_id:
                    batch_q = sql_select(ProductBatch).where(
                        ProductBatch.product_variant_id == int(variant_id),
                        ProductBatch.stock > 0,
                        ProductBatch.company_id == int(company_id),
                        ProductBatch.branch_id == int(branch_id),
                    )
                else:
                    batch_q = sql_select(ProductBatch).where(
                        ProductBatch.product_id == int(product_id),
                        ProductBatch.product_variant_id.is_(None),
                        ProductBatch.stock > 0,
                        ProductBatch.company_id == int(company_id),
                        ProductBatch.branch_id == int(branch_id),
                    )
                batch_q = batch_q.order_by(
                    ProductBatch.expiration_date.is_(None),
                    ProductBatch.expiration_date.asc(),
                    ProductBatch.id.asc(),
                )
                batches = (await session.exec(batch_q)).all()
                current_batch_id = item.get("batch_id")
                self.batch_picker_options = [
                    {
                        "id": b.id,
                        "batch_number": b.batch_number or "",
                        "expiration_date": (
                            b.expiration_date.strftime("%Y-%m-%d")
                            if b.expiration_date
                            else ""
                        ),
                        "stock": float(b.stock or 0),
                        "is_current": b.id == current_batch_id,
                    }
                    for b in batches
                ]
        except Exception:
            logging.exception("Error cargando lotes disponibles para el selector")
            self.batch_picker_options = []
        finally:
            self.batch_picker_loading = False

    @rx.event
    def close_batch_picker(self):
        """Cierra el modal selector de lote y limpia el estado."""
        self.batch_picker_open = False
        self.batch_picker_temp_id = ""
        self.batch_picker_description = ""
        self.batch_picker_options = []
        self.batch_picker_loading = False

    @rx.event
    def select_batch_for_item(self, batch_id: int):
        """Aplica el lote seleccionado al ítem activo del carrito."""
        temp_id = self.batch_picker_temp_id
        if not temp_id:
            self.close_batch_picker()
            return
        try:
            target_id = int(batch_id)
        except (TypeError, ValueError):
            return rx.toast("Lote inválido.", duration=3000)

        chosen = next(
            (
                opt
                for opt in self.batch_picker_options
                if int(opt.get("id", 0)) == target_id
            ),
            None,
        )
        if not chosen:
            return rx.toast("Lote no disponible.", duration=3000)

        items = list(self.new_sale_items)
        updated = False
        for idx, item in enumerate(items):
            if item.get("temp_id") == temp_id:
                new_item = item.copy()
                new_item["batch_id"] = target_id
                new_item["batch_number"] = chosen.get("batch_number", "") or ""
                new_item["requires_batch"] = True
                items[idx] = new_item
                updated = True
                break
        if not updated:
            self.close_batch_picker()
            return rx.toast(
                "El producto ya no está en el carrito.", duration=3000
            )
        self.new_sale_items = items
        self.close_batch_picker()
        return rx.toast(
            f"Lote {chosen.get('batch_number', '')} asignado",
            duration=2000,
        )

    @rx.event
    async def open_variant_picker(self, product_id: int):
        """Abre el modal grilla talla×color para un producto con variantes.

        Carga todas las variantes del producto y las organiza en una matriz
        donde las filas son las tallas y las columnas son los colores.
        """
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            return rx.toast("Producto inválido.", duration=3000)

        company_id = None
        branch_id = None
        if hasattr(self, "current_user"):
            company_id = self.current_user.get("company_id")
        if hasattr(self, "_branch_id"):
            branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa o sucursal no definida.", duration=3000)

        self.variant_picker_open = True
        self.variant_picker_loading = True
        self.variant_picker_product_id = pid
        self.variant_picker_description = ""
        self.variant_picker_colors = []
        self.variant_picker_rows = []

        try:
            from app.models import Product as ProductModel
            async with get_async_session() as session:
                product = (
                    await session.exec(
                        sql_select(ProductModel).where(
                            ProductModel.id == pid,
                            ProductModel.company_id == int(company_id),
                            ProductModel.branch_id == int(branch_id),
                        )
                    )
                ).first()
                if not product:
                    self.close_variant_picker()
                    return rx.toast("Producto no encontrado.", duration=3000)
                self.variant_picker_description = product.description or ""

                variants = (
                    await session.exec(
                        sql_select(ProductVariant)
                        .where(
                            ProductVariant.product_id == pid,
                            ProductVariant.company_id == int(company_id),
                            ProductVariant.branch_id == int(branch_id),
                        )
                        .order_by(
                            ProductVariant.size,
                            ProductVariant.color,
                            ProductVariant.id,
                        )
                    )
                ).all()
                if not variants:
                    self.close_variant_picker()
                    return rx.toast(
                        "Este producto no tiene variantes registradas.",
                        duration=3000,
                    )

                # Construir matriz: detectar tallas y colores únicos
                # preservando el orden del query (ordenado por size, color).
                sizes_order: List[str] = []
                colors_order: List[str] = []
                cell_lookup: Dict[tuple, ProductVariant] = {}
                for v in variants:
                    size = (v.size or "").strip() or "—"
                    color = (v.color or "").strip() or "—"
                    if size not in sizes_order:
                        sizes_order.append(size)
                    if color not in colors_order:
                        colors_order.append(color)
                    cell_lookup[(size, color)] = v

                rows: List[Dict[str, Any]] = []
                for size in sizes_order:
                    row_cells: List[Dict[str, Any]] = []
                    for color in colors_order:
                        v = cell_lookup.get((size, color))
                        if v:
                            stock = float(v.stock or 0)
                            row_cells.append(
                                {
                                    "color": color,
                                    "variant_id": v.id,
                                    "sku": v.sku or "",
                                    "stock": stock,
                                    "available": stock > 0,
                                    "is_placeholder": False,
                                }
                            )
                        else:
                            row_cells.append(
                                {
                                    "color": color,
                                    "variant_id": 0,
                                    "sku": "",
                                    "stock": 0.0,
                                    "available": False,
                                    "is_placeholder": True,
                                }
                            )
                    rows.append({"size": size, "cells": row_cells})

                self.variant_picker_colors = colors_order
                self.variant_picker_rows = rows
        except Exception:
            logging.exception("Error cargando variantes para el selector visual")
            self.variant_picker_rows = []
            self.variant_picker_colors = []
        finally:
            self.variant_picker_loading = False

    @rx.event
    def close_variant_picker(self):
        """Cierra el modal selector visual de variante y limpia el state."""
        self.variant_picker_open = False
        self.variant_picker_product_id = None
        self.variant_picker_description = ""
        self.variant_picker_colors = []
        self.variant_picker_rows = []
        self.variant_picker_loading = False

    @rx.event
    async def select_variant_for_sale(self, variant_id: int):
        """Agrega la variante elegida al carrito desde el modal grilla.

        Busca el SKU en las celdas cargadas y delega en el flujo estándar
        de procesamiento por código de barras (que maneja stock, lotes,
        precio mayorista, etc.).
        """
        try:
            target_id = int(variant_id)
        except (TypeError, ValueError):
            return rx.toast("Variante inválida.", duration=3000)
        if target_id <= 0:
            return rx.toast("Variante no disponible.", duration=3000)

        sku = ""
        for row in self.variant_picker_rows:
            for cell in row.get("cells", []):
                if int(cell.get("variant_id", 0) or 0) == target_id:
                    if cell.get("is_placeholder"):
                        return rx.toast(
                            "Esa combinación no existe.", duration=3000
                        )
                    if not cell.get("available"):
                        return rx.toast(
                            "Sin stock para esa variante.", duration=3000
                        )
                    sku = str(cell.get("sku", "") or "")
                    break
            if sku:
                break

        if not sku:
            return rx.toast("SKU no encontrado.", duration=3000)

        self.close_variant_picker()
        return await self._process_barcode(sku)

    def _reset_sale_form(self):
        self.sale_form_key += 1
        self.new_sale_item = {
            "temp_id": "",
            "barcode": "",
            "description": "",
            "category": "General",
            "quantity": 0,
            "unit": "Unidad",
            "price": 0,
            "sale_price": 0,
            "base_price": 0,
            "subtotal": 0,
            "product_id": None,
            "variant_id": None,
            "batch_id": None,
            "batch_number": "",
            "requires_batch": False,
            "kit_product_id": None,
            "kit_name": "",
            "promotion_name": "",
        }
        self.autocomplete_suggestions = []
        self.autocomplete_results = []
        self.autocomplete_selected_index = -1
        self.selected_product = None
        self.last_scanned_label = ""
        self.wholesale_price_applied = False
        self.price_list_price_applied = False
        self.promotion_applied = False
        self.promotion_name = ""

    async def handle_sale_change(self, field: str, value: Union[str, float]):
        try:
            if field in ["quantity", "price"]:
                numeric = float(value) if value else 0
                if field == "quantity":
                    self.new_sale_item[field] = self._normalize_quantity_value(
                        numeric, self.new_sale_item.get("unit", "")
                    )
                    await self._apply_price_tier()
                else:
                    self.new_sale_item[field] = self._round_currency(numeric)
            else:
                self.new_sale_item[field] = value
                if field == "unit":
                    self.new_sale_item["quantity"] = self._normalize_quantity_value(
                        self.new_sale_item["quantity"], value
                    )
            self.new_sale_item["subtotal"] = self._round_currency(
                self.new_sale_item["quantity"] * self.new_sale_item["price"]
            )
            if field == "description":
                self.selected_product = None
                if value and len(str(value)) > 1:
                    company_id = None
                    branch_id = None
                    if hasattr(self, "current_user"):
                        company_id = self.current_user.get("company_id")
                    if hasattr(self, "_branch_id"):
                        branch_id = self._branch_id()
                    if not company_id or not branch_id:
                        self.autocomplete_suggestions = []
                        self.autocomplete_results = []
                        return
                    # Debounce: espera 200ms antes de consultar la BD.
                    # Si el usuario sigue escribiendo, el seq anterior se invalida
                    # y la consulta nunca se ejecuta (ahorra ~4 queries por palabra).
                    self._autocomplete_debounce_seq += 1
                    seq = self._autocomplete_debounce_seq
                    await asyncio.sleep(0.2)
                    if seq != self._autocomplete_debounce_seq:
                        return
                    search = str(value).lower()
                    results = await SaleService.search_products(
                        search,
                        int(company_id),
                        int(branch_id),
                        limit=PRODUCT_SUGGESTIONS_LIMIT,
                    )
                    # Verificar que no hubo otro keystroke durante la búsqueda
                    if seq != self._autocomplete_debounce_seq:
                        return
                    self.autocomplete_results = results
                    self.autocomplete_selected_index = 0 if results else -1
                    self.autocomplete_suggestions = [
                        str(result.get("description", "")).strip()
                        for result in results
                        if result.get("description")
                    ]
                else:
                    self.autocomplete_suggestions = []
                    self.autocomplete_results = []
                    self.autocomplete_selected_index = -1
            elif field == "barcode":
                self.selected_product = None
                if not value or not str(value).strip():
                    self.new_sale_item["barcode"] = ""
                    self.new_sale_item["description"] = ""
                    self.new_sale_item["quantity"] = 0
                    self.new_sale_item["price"] = 0
                    self.new_sale_item["subtotal"] = 0
                    self.autocomplete_suggestions = []
                    self.autocomplete_results = []
                    self.autocomplete_selected_index = -1
                    self.last_scanned_label = ""
                else:
                    code = clean_barcode(str(value))
                    if validate_barcode(code):
                        company_id = None
                        branch_id = None
                        if hasattr(self, "current_user"):
                            company_id = self.current_user.get("company_id")
                        if hasattr(self, "_branch_id"):
                            branch_id = self._branch_id()
                        if not company_id or not branch_id:
                            self.autocomplete_suggestions = []
                            self.autocomplete_results = []
                            self.autocomplete_selected_index = -1
                            return
                        product = await SaleService.get_product_by_barcode(
                            code,
                            int(company_id),
                            int(branch_id),
                        )
                        if product:
                            self._fill_sale_item_from_product(
                                product, keep_quantity=False
                            )
                            await self._apply_price_tier(product)
                            self.autocomplete_suggestions = []
                            self.autocomplete_results = []
                            self.autocomplete_selected_index = -1
                            return
        except ValueError as e:
            logging.exception(f"Error parsing sale value: {e}")

    @rx.event
    async def handle_autocomplete_keydown(self, key: str):
        if not self.autocomplete_results:
            return
        total = len(self.autocomplete_results)
        if key in ("ArrowDown", "ArrowRight"):
            if self.autocomplete_selected_index < 0:
                self.autocomplete_selected_index = 0
            else:
                self.autocomplete_selected_index = min(
                    self.autocomplete_selected_index + 1, total - 1
                )
            return
        if key in ("ArrowUp", "ArrowLeft"):
            if self.autocomplete_selected_index < 0:
                self.autocomplete_selected_index = 0
            else:
                self.autocomplete_selected_index = max(
                    self.autocomplete_selected_index - 1, 0
                )
            return
        if key in ("Enter", "NumpadEnter"):
            idx = self.autocomplete_selected_index
            if idx < 0:
                idx = 0
            if 0 <= idx < total:
                return await self.select_product_for_sale(
                    self.autocomplete_results[idx]
                )
        if key == "Escape":
            self.autocomplete_suggestions = []
            self.autocomplete_results = []
            self.autocomplete_selected_index = -1

    @rx.event
    async def process_sale_barcode_from_input(self, barcode_value):
        self.new_sale_item["barcode"] = str(barcode_value) if barcode_value else ""

        if not barcode_value or not str(barcode_value).strip():
            self.new_sale_item["description"] = ""
            self.new_sale_item["quantity"] = 0
            self.new_sale_item["price"] = 0
            self.new_sale_item["subtotal"] = 0
            self.autocomplete_suggestions = []
            self.autocomplete_results = []
            return

        code = clean_barcode(str(barcode_value))
        if validate_barcode(code):
            company_id = None
            branch_id = None
            if hasattr(self, "current_user"):
                company_id = self.current_user.get("company_id")
            if hasattr(self, "_branch_id"):
                branch_id = self._branch_id()
            if not company_id or not branch_id:
                return
            product = await SaleService.get_product_by_barcode(
                code,
                int(company_id),
                int(branch_id),
            )
            if product:
                if self.new_sale_item.get("quantity", 0) <= 0:
                    self.new_sale_item["quantity"] = 1
                self._fill_sale_item_from_product(product, keep_quantity=True)
                await self._apply_price_tier(product)
                self.autocomplete_suggestions = []
                self.autocomplete_results = []
                return await self.add_item_to_sale(product_override=product)

    @rx.event
    async def select_product_for_sale(self, description: str | dict):
        if isinstance(description, dict):
            if description.get("description") or description.get("barcode"):
                self._fill_sale_item_from_product(description)
                self.selected_product = dict(description)
                self.autocomplete_suggestions = []
                self.autocomplete_results = []
                self.autocomplete_selected_index = -1
                return
        if isinstance(description, dict):
            description = (
                description.get("value")
                or description.get("description")
                or description.get("label")
                or ""
            )
        desc = description.strip()
        if desc:
            company_id = None
            branch_id = None
            if hasattr(self, "current_user"):
                company_id = self.current_user.get("company_id")
            if hasattr(self, "_branch_id"):
                branch_id = self._branch_id()
            if not company_id or not branch_id:
                self.autocomplete_suggestions = []
                self.autocomplete_results = []
                return
            product = None
            if self.autocomplete_results:
                for candidate in self.autocomplete_results:
                    if candidate.get("description") == desc:
                        product = candidate
                        break
            if product is None:
                results = await SaleService.search_products(
                    desc,
                    int(company_id),
                    int(branch_id),
                    limit=PRODUCT_SUGGESTIONS_LIMIT,
                )
                for candidate in results:
                    if candidate.get("description") == desc:
                        product = candidate
                        break
                if product is None and results:
                    product = results[0]
            if product:
                self._fill_sale_item_from_product(product)
                await self._apply_price_tier(product)
                self.selected_product = dict(product) if isinstance(product, dict) else None
        self.autocomplete_suggestions = []
        self.autocomplete_results = []
        self.autocomplete_selected_index = -1

    @rx.var(cache=True)
    def autocomplete_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, result in enumerate(self.autocomplete_results):
            row = dict(result)
            row["index"] = index
            rows.append(row)
        return rows

    @rx.event
    async def add_item_to_sale(self, product_override: dict | None = None):
        if not self.current_user["privileges"]["create_ventas"]:
            return rx.toast("No tiene permisos para crear ventas.", duration=3000)
        self.sale_receipt_ready = False

        if product_override:
            if (
                not self.new_sale_item.get("description")
                or self.new_sale_item.get("price", 0) <= 0
            ):
                self._fill_sale_item_from_product(product_override, keep_quantity=True)
            self.selected_product = dict(product_override)
        elif self.selected_product:
            product_override = self.selected_product
            if (
                not self.new_sale_item.get("description")
                or self.new_sale_item.get("price", 0) <= 0
            ):
                self._fill_sale_item_from_product(product_override, keep_quantity=True)
        if product_override:
            await self._apply_price_tier(product_override)

        description = self.new_sale_item["description"].strip()
        barcode = str(self.new_sale_item.get("barcode", "") or "").strip()

        existing_index = None
        existing_item = None
        for idx, item in enumerate(self.new_sale_items):
            item_barcode = str(item.get("barcode", "") or "").strip()
            item_description = str(item.get("description", "") or "").strip()
            if barcode and item_barcode == barcode:
                existing_index = idx
                existing_item = item
                break
            if item_description == description:
                existing_index = idx
                existing_item = item
                break

        existing_qty = float(existing_item["quantity"]) if existing_item else 0.0
        new_qty = float(self.new_sale_item["quantity"])
        total_qty = existing_qty + new_qty
        company_id = None
        branch_id = None
        if hasattr(self, "current_user"):
            company_id = self.current_user.get("company_id")
        if hasattr(self, "_branch_id"):
            branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast(
                "Empresa o sucursal no definida.",
                duration=3000,
            )

        product = None
        if product_override:
            product = product_override
        elif barcode:
            product = await SaleService.get_product_by_barcode(
                barcode,
                int(company_id),
                int(branch_id),
            )
            if not product and description:
                results = await SaleService.search_products(
                    description,
                    int(company_id),
                    int(branch_id),
                    limit=PRODUCT_SUGGESTIONS_LIMIT,
                )
                for candidate in results:
                    if candidate.get("description") == description:
                        product = candidate
                        break
                if product is None and results:
                    product = results[0]
        else:
            results = await SaleService.search_products(
                description,
                int(company_id),
                int(branch_id),
                limit=PRODUCT_SUGGESTIONS_LIMIT,
            )
            for candidate in results:
                if candidate.get("description") == description:
                    product = candidate
                    break
            if product is None and results:
                product = results[0]

        if product:
            if not self.new_sale_item["description"] or self.new_sale_item["price"] <= 0:
                self._fill_sale_item_from_product(product, keep_quantity=True)
                await self._apply_price_tier(product)
            if isinstance(product, dict):
                self.selected_product = dict(product)

        if (
            not self.new_sale_item["description"]
            or self.new_sale_item["quantity"] <= 0
            or self.new_sale_item["price"] <= 0
        ):
            return rx.toast(
                "Por favor, busque un producto y complete los campos.", duration=3000
            )

        if not product:
            return rx.toast(
                "Producto no encontrado en el inventario.", duration=3000
            )
        if not barcode:
            self.new_sale_item["barcode"] = self._product_value(
                product, "barcode", ""
            )
            barcode = self.new_sale_item["barcode"]
        if not self.new_sale_item.get("product_id"):
            self.new_sale_item["product_id"] = self._product_value(
                product,
                "product_id",
                self._product_value(product, "id", None),
            )
        if self.new_sale_item.get("variant_id") is None:
            self.new_sale_item["variant_id"] = self._product_value(
                product, "variant_id", None
            )
        await self._apply_price_tier(product, quantity_override=total_qty)
        product_id = self.new_sale_item.get("product_id") or self._product_value(
            product,
            "product_id",
            self._product_value(product, "id", None),
        )
        variant_id = self._product_value(product, "variant_id", None)
        available_stock = await SaleService.get_available_stock(
            int(product_id) if product_id else None,
            int(variant_id) if variant_id else None,
            int(company_id),
            int(branch_id),
        )
        product_stock = Decimal(str(available_stock or 0))
        if product_stock < Decimal(str(total_qty)):
            remaining = max(product_stock - Decimal(str(existing_qty)), Decimal("0"))
            unit = self._product_value(
                product,
                "unit",
                self.new_sale_item.get("unit", ""),
            )
            in_cart_display = self._normalize_quantity_value(existing_qty, unit)
            remaining_display = self._normalize_quantity_value(remaining, unit)
            return rx.toast(
                f"Stock insuficiente: ya tienes {in_cart_display} en el carrito y solo quedan {remaining_display} disponibles.",
                duration=3000,
            )

        # Verificar si la categoría requiere lote y autoasignar lote FEFO
        await self._resolve_batch_info(product, company_id, branch_id)

        if existing_item is not None:
            updated_item = existing_item.copy()
            unit = updated_item.get("unit", "")
            updated_item["quantity"] = self._normalize_quantity_value(
                existing_qty + new_qty, unit
            )
            updated_item["price"] = self.new_sale_item.get(
                "price", updated_item.get("price", 0)
            )
            updated_item["subtotal"] = self._round_currency(
                updated_item["quantity"] * updated_item["price"]
            )
            # Preservar info de lote del ítem original
            for k in ("batch_id", "batch_number", "requires_batch"):
                if k not in updated_item:
                    updated_item[k] = self.new_sale_item.get(k)
            items = list(self.new_sale_items)
            items[existing_index] = updated_item
            self.new_sale_items = items
            await self._recompute_cart_prices()
            self._reset_sale_form()
            self._refresh_payment_feedback()
            return [
                rx.toast(
                    f"Cantidad actualizada a {updated_item['quantity']}",
                    duration=2000,
                ),
                rx.call_script(
                    "setTimeout(() => { const el = document.getElementById('venta_barcode_input'); if (el) { el.focus(); el.select(); } }, 0);"
                ),
            ]

        item_copy = self.new_sale_item.copy()
        item_copy["temp_id"] = str(uuid.uuid4())
        self._apply_item_rounding(item_copy)
        self.new_sale_items.append(item_copy)
        await self._recompute_cart_prices()
        self._reset_sale_form()
        self._refresh_payment_feedback()
        return [
            rx.toast(
                f"Producto '{item_copy['description']}' agregado",
                duration=2000,
            ),
            rx.call_script(
                "setTimeout(() => { const el = document.getElementById('venta_barcode_input'); if (el) { el.focus(); el.select(); } }, 0);"
            ),
        ]

    @rx.event
    async def remove_item_from_sale(self, temp_id: str):
        self.new_sale_items = [
            item for item in self.new_sale_items if item["temp_id"] != temp_id
        ]
        self.sale_receipt_ready = False
        await self._recompute_cart_prices()
        self._refresh_payment_feedback()
        self.sale_receipt_ready = False

    @rx.event
    def clear_sale_items(self):
        self.new_sale_items = []
        self._reset_sale_form()
        self.sale_receipt_ready = False
        self._refresh_payment_feedback()

    @rx.event
    async def load_product_grid(self, search: str = ""):
        """Carga productos para el grid visual (ropa/juguetería)."""
        company_id = None
        branch_id = None
        if hasattr(self, "current_user"):
            company_id = self.current_user.get("company_id")
        if hasattr(self, "_branch_id"):
            branch_id = self._branch_id()
        if not company_id or not branch_id:
            self.product_grid_items = []
            return
        self.product_grid_search = search or ""
        try:
            from app.models import Product as ProductModel
            from app.utils.sanitization import escape_like as _esc
            async with get_async_session() as session:
                q = sql_select(ProductModel).where(
                    ProductModel.company_id == int(company_id),
                    ProductModel.branch_id == int(branch_id),
                ).order_by(ProductModel.description).limit(60)
                if search and search.strip():
                    like = f"%{_esc(search.strip())}%"
                    q = q.where(
                        ProductModel.description.ilike(like)
                        | ProductModel.barcode.ilike(like)
                        | ProductModel.category.ilike(like)
                    )
                products = (await session.exec(q)).all()
                self.product_grid_items = [
                    {
                        "product_id": p.id,
                        "barcode": p.barcode or "",
                        "description": p.description or "",
                        "sale_price": float(p.sale_price or 0),
                        "stock": float(p.stock or 0),
                        "sin_stock": float(p.stock or 0) <= 0,
                        "category": p.category or "General",
                    }
                    for p in products
                ]
        except Exception:
            logging.exception("Error cargando grid de productos")
            self.product_grid_items = []

    @rx.event
    async def add_product_to_sale_by_id(self, product_id: int):
        """Agrega un producto al carrito desde el grid visual.

        Si el producto tiene variantes (talla/color), abre el selector
        visual en lugar de agregar el producto raíz directamente.
        """
        company_id = None
        branch_id = None
        if hasattr(self, "current_user"):
            company_id = self.current_user.get("company_id")
        if hasattr(self, "_branch_id"):
            branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa o sucursal no definida.", duration=3000)
        try:
            from app.models import Product as ProductModel
            async with get_async_session() as session:
                p = (
                    await session.exec(
                        sql_select(ProductModel).where(
                            ProductModel.id == int(product_id),
                            ProductModel.company_id == int(company_id),
                            ProductModel.branch_id == int(branch_id),
                        )
                    )
                ).first()
                if not p:
                    return rx.toast("Producto no encontrado.", duration=3000)

                # Detectar variantes: si existen, abrir el selector visual
                # en lugar de agregar el producto raíz al carrito.
                variant_exists = (
                    await session.exec(
                        sql_select(ProductVariant.id)
                        .where(
                            ProductVariant.product_id == int(product_id),
                            ProductVariant.company_id == int(company_id),
                            ProductVariant.branch_id == int(branch_id),
                        )
                        .limit(1)
                    )
                ).first()
                if variant_exists:
                    return await self.open_variant_picker(int(product_id))

                # Detectar kit: si tiene componentes, expandir en carrito
                kit_exists = (
                    await session.exec(
                        sql_select(ProductKit.id)
                        .where(
                            ProductKit.kit_product_id == int(product_id),
                            ProductKit.company_id == int(company_id),
                            ProductKit.branch_id == int(branch_id),
                        )
                        .limit(1)
                    )
                ).first()
                if kit_exists:
                    kit_payload = {
                        "id": p.id,
                        "product_id": p.id,
                        "description": p.description,
                        "sale_price": p.sale_price,
                    }
                    return await self._add_kit_to_cart(
                        kit_payload, company_id, branch_id
                    )

                payload = {
                    "id": p.id,
                    "product_id": p.id,
                    "variant_id": None,
                    "is_variant": False,
                    "barcode": p.barcode,
                    "description": p.description,
                    "category": p.category,
                    "unit": p.unit,
                    "sale_price": p.sale_price,
                    "purchase_price": p.purchase_price,
                    "stock": p.stock,
                }
                self.new_sale_item["quantity"] = 1
                return await self.add_item_to_sale(product_override=payload)
        except Exception:
            logging.exception("Error agregando producto desde grid")
            return rx.toast("Error al agregar producto.", duration=3000)

    @rx.event
    async def search_product_grid(self, value: str):
        """Búsqueda dentro del grid visual."""
        return await self.load_product_grid(search=value)

    # ── Cupón de descuento ───────────────────────────────────────

    @rx.event
    def set_cart_coupon_input(self, value: str):
        """Setter del input mientras el cajero tipea (sin validar)."""
        self.cart_coupon_code = value.upper().strip()
        if self.cart_coupon_status:
            self.cart_coupon_status = ""
            self.cart_coupon_message = ""

    @rx.event
    async def apply_cart_coupon(self):
        """Valida el cupón contra la BD y, si es válido, recompone precios."""
        from app.models import Promotion
        from app.utils.tenant import set_tenant_context
        from sqlmodel import select

        code = (self.cart_coupon_code or "").strip().upper()
        if not code:
            self.cart_coupon_status = "invalid"
            self.cart_coupon_message = "Ingresá un código de cupón."
            return rx.toast("Ingresá un código.", duration=2500)

        company_id = self.current_user.get("company_id") if hasattr(self, "current_user") else None
        branch_id = self._branch_id() if hasattr(self, "_branch_id") else None
        if not company_id:
            return

        set_tenant_context(company_id, branch_id)
        now = self._display_now().replace(tzinfo=None)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        with rx.session() as session:
            promo = session.exec(
                select(Promotion)
                .where(Promotion.company_id == company_id)
                .where(Promotion.branch_id == branch_id)
                .where(Promotion.coupon_code == code)
                .where(Promotion.is_active == True)  # noqa: E712
                .where(Promotion.starts_at <= now)
                .where(Promotion.ends_at >= today_start)
            ).first()

        if not promo:
            self.cart_coupon_status = "invalid"
            self.cart_coupon_message = "Cupón inválido o vencido."
            return rx.toast("Cupón inválido o vencido.", duration=3000)

        if promo.max_uses is not None and (promo.current_uses or 0) >= promo.max_uses:
            self.cart_coupon_status = "invalid"
            self.cart_coupon_message = "El cupón ya alcanzó su límite de usos."
            return rx.toast("El cupón está agotado.", duration=3000)

        # Validar restricciones de día de semana
        mask = getattr(promo, "weekdays_mask", 127) or 127
        weekday_bit = 1 << now.weekday()
        if not (mask & weekday_bit):
            self.cart_coupon_status = "invalid"
            self.cart_coupon_message = "El cupón no aplica este día de la semana."
            return rx.toast("El cupón no aplica hoy.", duration=3000)

        # Validar franja horaria
        time_from = getattr(promo, "time_from", None)
        time_to = getattr(promo, "time_to", None)
        if time_from is not None and time_to is not None:
            cur_t = now.time()
            if time_from <= time_to:
                in_window = time_from <= cur_t <= time_to
            else:
                in_window = cur_t >= time_from or cur_t <= time_to
            if not in_window:
                from_str = time_from.strftime("%H:%M")
                to_str = time_to.strftime("%H:%M")
                self.cart_coupon_status = "invalid"
                self.cart_coupon_message = f"El cupón solo aplica de {from_str} a {to_str}."
                return rx.toast(self.cart_coupon_message, duration=3500)

        # Validar monto mínimo de carrito antes de marcar como aplicado.
        min_cart = Decimal(str(getattr(promo, "min_cart_amount", None) or 0))
        if min_cart > 0:
            cart_sub = Decimal("0.00")
            for it in self.new_sale_items:
                it_qty = Decimal(str(it.get("quantity") or 0))
                it_base = Decimal(str(it.get("base_price") or it.get("sale_price") or 0))
                cart_sub += it_qty * it_base
            if cart_sub < min_cart:
                currency = getattr(self, "currency_symbol", "S/")
                self.cart_coupon_status = "invalid"
                self.cart_coupon_message = (
                    f"El carrito debe superar {currency} {min_cart:.2f} para aplicar este cupón."
                )
                return rx.toast(self.cart_coupon_message, duration=3500)

        self.cart_coupon_status = "applied"
        self.cart_coupon_message = f"Cupón '{promo.name}' aplicado."
        await self._recompute_cart_prices()
        return rx.toast(self.cart_coupon_message, duration=2500)

    @rx.event
    async def clear_cart_coupon(self):
        """Limpia el cupón aplicado y recompone precios."""
        self.cart_coupon_code = ""
        self.cart_coupon_status = ""
        self.cart_coupon_message = ""
        await self._recompute_cart_prices()

    async def _recompute_cart_prices(self):
        """Re-resuelve precio efectivo de cada ítem del carrito tras
        aplicar/quitar cupón. Llama a ``resolve_effective_price`` para
        recomponer desde la jerarquía completa (price_list > tier > sale_price)
        en vez de partir del precio cacheado del item — esto evita acumular
        descuentos cuando el cupón se aplica sobre un ítem que ya tenía promo.

        Hace dos pasadas: la primera computa precios base sin promo para
        obtener el subtotal pre-promo; la segunda aplica promos pasando ese
        subtotal como contexto, lo que permite evaluar ``min_cart_amount``
        coherentemente sobre todo el carrito (no por ítem aislado).
        """
        from app.models import Product
        from app.services.pricing import resolve_effective_price
        from sqlmodel import select

        company_id = self.current_user.get("company_id") if hasattr(self, "current_user") else None
        branch_id = self._branch_id() if hasattr(self, "_branch_id") else None
        if not company_id or not self.new_sale_items:
            return

        client_pl_id = getattr(self, "client_price_list_id", None)
        coupon = self.cart_coupon_code if self.cart_coupon_status == "applied" else None
        local_now = self._display_now().replace(tzinfo=None)

        async with get_async_session() as session:
            # ── Pasada 1: precios base + subtotal pre-promo. ──
            # Se omite cart_subtotal a propósito (None) para que la pasada 1
            # NO dispare promos con umbral; solo nos interesa el base_price.
            base_resolutions: list[tuple[Decimal, Decimal] | None] = []
            cart_subtotal_pre_promo = Decimal("0.00")
            for item in self.new_sale_items:
                product_id = item.get("product_id")
                if not product_id:
                    base_resolutions.append(None)
                    continue
                product = (
                    await session.exec(
                        select(Product)
                        .where(Product.id == int(product_id))
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                    )
                ).first()
                if not product:
                    base_resolutions.append(None)
                    continue
                qty = Decimal(str(item.get("quantity") or 0))
                resolution = await resolve_effective_price(
                    session,
                    product=product,
                    variant_id=item.get("variant_id"),
                    quantity=qty,
                    company_id=int(company_id),
                    branch_id=int(branch_id),
                    client_price_list_id=client_pl_id,
                    now=local_now,
                    coupon_code=None,
                    cart_subtotal=None,
                )
                base_resolutions.append((qty, resolution.base_price))
                cart_subtotal_pre_promo += qty * resolution.base_price

            # ── Pasada 2: aplicar promo con cart_subtotal completo. ──
            for item, prepared in zip(self.new_sale_items, base_resolutions):
                if prepared is None:
                    continue
                qty, base_price = prepared
                product_id = item.get("product_id")
                product = (
                    await session.exec(
                        select(Product)
                        .where(Product.id == int(product_id))
                        .where(Product.company_id == company_id)
                        .where(Product.branch_id == branch_id)
                    )
                ).first()
                if not product:
                    continue
                resolution = await resolve_effective_price(
                    session,
                    product=product,
                    variant_id=item.get("variant_id"),
                    quantity=qty,
                    company_id=int(company_id),
                    branch_id=int(branch_id),
                    client_price_list_id=client_pl_id,
                    now=local_now,
                    coupon_code=coupon,
                    cart_subtotal=cart_subtotal_pre_promo,
                )
                item["price"] = self._round_currency(resolution.final_price)
                item["sale_price"] = self._round_currency(resolution.base_price)
                item["base_price"] = self._round_currency(resolution.base_price)
                item["subtotal"] = self._round_currency(qty * Decimal(str(item["price"])))
                applied_promo = resolution.applied_promotion
                item["promotion_name"] = applied_promo.name if applied_promo else ""
        self.new_sale_items = list(self.new_sale_items)
