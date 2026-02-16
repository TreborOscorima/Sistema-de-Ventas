import logging
import uuid
from typing import Any, Dict, List, Union

import reflex as rx
from decimal import Decimal

from app.services.sale_service import SaleService
from app.utils.barcode import clean_barcode, validate_barcode
from ..types import TransactionItem


class CartMixin:
    new_sale_item: Dict[str, Any] = {
        "temp_id": "",
        "barcode": "",
        "description": "",
        "category": "General",
        "quantity": 0,
        "unit": "Unidad",
        "price": 0,
        "sale_price": 0,
        "subtotal": 0,
        "product_id": None,
        "variant_id": None,
    }
    new_sale_items: List[Dict[str, Any]] = []
    autocomplete_suggestions: List[str] = []
    autocomplete_results: List[Dict[str, Any]] = []
    autocomplete_selected_index: int = -1
    selected_product: Dict[str, Any] | None = None
    last_scanned_label: str = ""

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
        qty = quantity_override
        if qty is None:
            qty = self.new_sale_item.get("quantity", 0)
        if not qty or qty <= 0:
            return None
        company_id = self._company_id() if hasattr(self, "_company_id") else None
        branch_id = self._branch_id() if hasattr(self, "_branch_id") else None
        if not company_id or not branch_id:
            return None
        tier_price = await SaleService.calculate_item_price(
            int(product_id),
            Decimal(str(qty)),
            int(company_id),
            int(branch_id),
        )
        if tier_price and tier_price > 0:
            self.new_sale_item["price"] = self._round_currency(tier_price)
            self.new_sale_item["sale_price"] = self._round_currency(tier_price)
            self.new_sale_item["subtotal"] = self._round_currency(
                self.new_sale_item["quantity"] * self.new_sale_item["price"]
            )
        return tier_price

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

        if not keep_quantity:
            self.autocomplete_suggestions = []
            self.autocomplete_results = []

        logging.info(
            "[FILL-SALE] C▃igo corregido: escaneado incompleto  '%s' completo (producto: %s)",
            product_barcode,
            description,
        )

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
            "subtotal": 0,
            "product_id": None,
            "variant_id": None,
        }
        self.autocomplete_suggestions = []
        self.autocomplete_results = []
        self.autocomplete_selected_index = -1
        self.selected_product = None
        self.last_scanned_label = ""

    @rx.event
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
                    search = str(value).lower()
                    results = await SaleService.search_products(
                        search,
                        int(company_id),
                        int(branch_id),
                        limit=5,
                    )
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
                    limit=5,
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
                    limit=5,
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
                limit=5,
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
            items = list(self.new_sale_items)
            items[existing_index] = updated_item
            self.new_sale_items = items
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
    def remove_item_from_sale(self, temp_id: str):
        self.new_sale_items = [
            item for item in self.new_sale_items if item["temp_id"] != temp_id
        ]
        self.sale_receipt_ready = False
        self._refresh_payment_feedback()
        self.sale_receipt_ready = False

    @rx.event
    def clear_sale_items(self):
        self.new_sale_items = []
        self._reset_sale_form()
        self.sale_receipt_ready = False
        self._refresh_payment_feedback()
