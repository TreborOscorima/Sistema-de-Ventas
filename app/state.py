import reflex as rx
from typing import TypedDict, Union
import datetime
import uuid
import logging


class Product(TypedDict):
    id: str
    description: str
    stock: float
    unit: str
    purchase_price: float
    sale_price: float


class TransactionItem(TypedDict):
    temp_id: str
    description: str
    quantity: float
    unit: str
    price: float
    subtotal: float


class Movement(TypedDict):
    id: str
    timestamp: str
    type: str
    product_description: str
    quantity: float
    unit: str
    total: float


class State(rx.State):
    sidebar_open: bool = True
    current_page: str = "Ingreso"
    units: list[str] = ["Unidad", "Kg", "Litro", "Metro", "Caja"]
    inventory: dict[str, Product] = {}
    history: list[Movement] = []
    inventory_search_term: str = ""
    history_filter_type: str = "Todos"
    history_filter_product: str = ""
    history_filter_start_date: str = ""
    history_filter_end_date: str = ""
    staged_history_filter_type: str = "Todos"
    staged_history_filter_product: str = ""
    staged_history_filter_start_date: str = ""
    staged_history_filter_end_date: str = ""
    current_page_history: int = 1
    items_per_page: int = 10
    new_entry_item: TransactionItem = {
        "temp_id": "",
        "description": "",
        "quantity": 0,
        "unit": "Unidad",
        "price": 0,
        "subtotal": 0,
    }
    new_entry_items: list[TransactionItem] = []
    new_sale_item: TransactionItem = {
        "temp_id": "",
        "description": "",
        "quantity": 0,
        "unit": "Unidad",
        "price": 0,
        "subtotal": 0,
    }
    new_sale_items: list[TransactionItem] = []
    autocomplete_suggestions: list[str] = []

    @rx.var
    def entry_subtotal(self) -> float:
        return self.new_entry_item["quantity"] * self.new_entry_item["price"]

    @rx.var
    def entry_total(self) -> float:
        return sum((item["subtotal"] for item in self.new_entry_items))

    @rx.var
    def sale_subtotal(self) -> float:
        return self.new_sale_item["quantity"] * self.new_sale_item["price"]

    @rx.var
    def sale_total(self) -> float:
        return sum((item["subtotal"] for item in self.new_sale_items))

    @rx.var
    def inventory_list(self) -> list[Product]:
        if self.inventory_search_term:
            return sorted(
                [
                    p
                    for p in self.inventory.values()
                    if self.inventory_search_term.lower() in p["description"].lower()
                ],
                key=lambda p: p["description"],
            )
        return sorted(list(self.inventory.values()), key=lambda p: p["description"])

    @rx.var
    def filtered_history(self) -> list[Movement]:
        movements = self.history
        if self.history_filter_type != "Todos":
            movements = [m for m in movements if m["type"] == self.history_filter_type]
        if self.history_filter_product:
            movements = [
                m
                for m in movements
                if self.history_filter_product.lower()
                in m["product_description"].lower()
            ]
        if self.history_filter_start_date:
            try:
                start_date = datetime.datetime.fromisoformat(
                    self.history_filter_start_date
                )
                movements = [
                    m
                    for m in movements
                    if datetime.datetime.fromisoformat(m["timestamp"].split()[0])
                    >= start_date
                ]
            except ValueError as e:
                logging.exception(f"Error parsing start date: {e}")
        if self.history_filter_end_date:
            try:
                end_date = datetime.datetime.fromisoformat(self.history_filter_end_date)
                movements = [
                    m
                    for m in movements
                    if datetime.datetime.fromisoformat(m["timestamp"].split()[0])
                    <= end_date
                ]
            except ValueError as e:
                logging.exception(f"Error parsing end date: {e}")
        return sorted(movements, key=lambda m: m["timestamp"], reverse=True)

    @rx.var
    def paginated_history(self) -> list[Movement]:
        start_index = (self.current_page_history - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        return self.filtered_history[start_index:end_index]

    @rx.var
    def total_pages(self) -> int:
        total_items = len(self.filtered_history)
        return (total_items + self.items_per_page - 1) // self.items_per_page

    @rx.var
    def total_ingresos(self) -> float:
        return sum((m["total"] for m in self.history if m["type"] == "Ingreso"))

    @rx.var
    def total_ventas(self) -> float:
        return sum((m["total"] for m in self.history if m["type"] == "Venta"))

    @rx.var
    def ganancia_bruta(self) -> float:
        return self.total_ventas - self.total_ingresos

    @rx.var
    def total_movimientos(self) -> int:
        return len(self.history)

    @rx.var
    def productos_mas_vendidos(self) -> list[dict]:
        from collections import Counter

        sales = [m for m in self.history if m["type"] == "Venta"]
        product_counts = Counter((m["product_description"] for m in sales))
        top_products = product_counts.most_common(5)
        return [
            {"description": desc, "cantidad_vendida": qty} for desc, qty in top_products
        ]

    @rx.var
    def productos_stock_bajo(self) -> list[Product]:
        return sorted(
            [p for p in self.inventory.values() if p["stock"] <= 10],
            key=lambda p: p["stock"],
        )

    @rx.var
    def sales_by_day(self) -> list[dict]:
        from collections import defaultdict

        sales_data = defaultdict(lambda: {"ingresos": 0, "ventas": 0})
        for m in self.history:
            day = m["timestamp"].split(" ")[0]
            if m["type"] == "Ingreso":
                sales_data[day]["ingresos"] += m["total"]
            elif m["type"] == "Venta":
                sales_data[day]["ventas"] += m["total"]
        sorted_days = sorted(sales_data.keys())
        return [
            {
                "date": day,
                "ingresos": sales_data[day]["ingresos"],
                "ventas": sales_data[day]["ventas"],
            }
            for day in sorted_days
        ]

    @rx.event
    def set_history_page(self, page_num: int):
        if 1 <= page_num <= self.total_pages:
            self.current_page_history = page_num

    @rx.event
    def reset_history_filters(self):
        self.staged_history_filter_type = "Todos"
        self.staged_history_filter_product = ""
        self.staged_history_filter_start_date = ""
        self.staged_history_filter_end_date = ""
        self.history_filter_type = "Todos"
        self.history_filter_product = ""
        self.history_filter_start_date = ""
        self.history_filter_end_date = ""
        self.current_page_history = 1

    @rx.event
    def apply_history_filters(self):
        self.history_filter_type = self.staged_history_filter_type
        self.history_filter_product = self.staged_history_filter_product
        self.history_filter_start_date = self.staged_history_filter_start_date
        self.history_filter_end_date = self.staged_history_filter_end_date
        self.current_page_history = 1

    @rx.event
    def export_to_excel(self):
        import openpyxl
        import io

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Historial Movimientos"
        headers = [
            "Timestamp",
            "Type",
            "Product Description",
            "Quantity",
            "Unit",
            "Total",
        ]
        sheet.append(headers)
        for movement in self.filtered_history:
            sheet.append(
                [
                    movement["timestamp"],
                    movement["type"],
                    movement["product_description"],
                    movement["quantity"],
                    movement["unit"],
                    movement["total"],
                ]
            )
        excel_data = io.BytesIO()
        workbook.save(excel_data)
        excel_data.seek(0)
        return rx.download(
            data=excel_data.read(), filename="historial_movimientos.xlsx"
        )

    @rx.event
    def set_page(self, page: str):
        self.current_page = page
        self.sidebar_open = False

    @rx.event
    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    @rx.event
    def handle_entry_change(self, field: str, value: str):
        if field in ["quantity", "price"]:
            try:
                self.new_entry_item[field] = float(value)
            except ValueError as e:
                logging.exception(f"Error converting value to float: {e}")
                self.new_entry_item[field] = 0
        else:
            self.new_entry_item[field] = value
        self.new_entry_item["subtotal"] = (
            self.new_entry_item["quantity"] * self.new_entry_item["price"]
        )

    @rx.event
    def handle_sale_change(self, field: str, value: Union[str, float]):
        if field in ["quantity", "price"]:
            try:
                self.new_sale_item[field] = float(value)
            except ValueError as e:
                logging.exception(f"Error converting sale value to float: {e}")
                self.new_sale_item[field] = 0
        else:
            self.new_sale_item[field] = value
        self.new_sale_item["subtotal"] = (
            self.new_sale_item["quantity"] * self.new_sale_item["price"]
        )
        if field == "description":
            if value:
                self.autocomplete_suggestions = [
                    p["description"]
                    for p in self.inventory.values()
                    if value.lower() in p["description"].lower()
                ]
            else:
                self.autocomplete_suggestions = []

    @rx.event
    def select_product_for_sale(self, description: str):
        product_id = description.lower().strip()
        if product_id in self.inventory:
            product = self.inventory[product_id]
            self.new_sale_item = {
                "temp_id": "",
                "description": product["description"],
                "quantity": 1,
                "unit": product["unit"],
                "price": product["sale_price"],
                "subtotal": product["sale_price"],
            }
            self.autocomplete_suggestions = []

    @rx.event
    def add_item_to_entry(self):
        if (
            not self.new_entry_item["description"]
            or self.new_entry_item["quantity"] <= 0
            or self.new_entry_item["price"] <= 0
        ):
            return rx.toast(
                "Por favor, complete todos los campos correctamente.", duration=3000
            )
        item_copy = self.new_entry_item.copy()
        item_copy["temp_id"] = str(uuid.uuid4())
        self.new_entry_items.append(item_copy)
        self.new_entry_item = {
            "temp_id": "",
            "description": "",
            "quantity": 0,
            "unit": "Unidad",
            "price": 0,
            "subtotal": 0,
        }

    @rx.event
    def remove_item_from_entry(self, temp_id: str):
        self.new_entry_items = [
            item for item in self.new_entry_items if item["temp_id"] != temp_id
        ]

    @rx.event
    def confirm_entry(self):
        if not self.new_entry_items:
            return rx.toast("No hay productos para ingresar.", duration=3000)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in self.new_entry_items:
            product_id = item["description"].lower().strip()
            if product_id in self.inventory:
                self.inventory[product_id]["stock"] += item["quantity"]
                self.inventory[product_id]["purchase_price"] = item["price"]
            else:
                self.inventory[product_id] = {
                    "id": product_id,
                    "description": item["description"],
                    "stock": item["quantity"],
                    "unit": item["unit"],
                    "purchase_price": item["price"],
                    "sale_price": item["price"] * 1.25,
                }
            self.history.append(
                {
                    "id": str(uuid.uuid4()),
                    "timestamp": timestamp,
                    "type": "Ingreso",
                    "product_description": item["description"],
                    "quantity": item["quantity"],
                    "unit": item["unit"],
                    "total": item["subtotal"],
                }
            )
        self.new_entry_items = []
        return rx.toast("Ingreso de productos confirmado.", duration=3000)

    @rx.event
    def add_item_to_sale(self):
        if (
            not self.new_sale_item["description"]
            or self.new_sale_item["quantity"] <= 0
            or self.new_sale_item["price"] <= 0
        ):
            return rx.toast(
                "Por favor, busque un producto y complete los campos.", duration=3000
            )
        product_id = self.new_sale_item["description"].lower().strip()
        if product_id not in self.inventory:
            return rx.toast("Producto no encontrado en el inventario.", duration=3000)
        if self.inventory[product_id]["stock"] < self.new_sale_item["quantity"]:
            return rx.toast("Stock insuficiente para realizar la venta.", duration=3000)
        item_copy = self.new_sale_item.copy()
        item_copy["temp_id"] = str(uuid.uuid4())
        self.new_sale_items.append(item_copy)
        self.new_sale_item = {
            "temp_id": "",
            "description": "",
            "quantity": 0,
            "unit": "Unidad",
            "price": 0,
            "subtotal": 0,
        }

    @rx.event
    def remove_item_from_sale(self, temp_id: str):
        self.new_sale_items = [
            item for item in self.new_sale_items if item["temp_id"] != temp_id
        ]

    @rx.event
    def confirm_sale(self):
        if not self.new_sale_items:
            return rx.toast("No hay productos en la venta.", duration=3000)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in self.new_sale_items:
            product_id = item["description"].lower().strip()
            if product_id in self.inventory:
                if self.inventory[product_id]["stock"] >= item["quantity"]:
                    self.inventory[product_id]["stock"] -= item["quantity"]
                    self.history.append(
                        {
                            "id": str(uuid.uuid4()),
                            "timestamp": timestamp,
                            "type": "Venta",
                            "product_description": item["description"],
                            "quantity": item["quantity"],
                            "unit": item["unit"],
                            "total": item["subtotal"],
                        }
                    )
                else:
                    return rx.toast(
                        f"Stock insuficiente para {item['description']}", duration=3000
                    )
            else:
                return rx.toast(
                    f"Producto {item['description']} no encontrado.", duration=3000
                )
        self.new_sale_items = []
        return rx.toast("Venta confirmada.", duration=3000)