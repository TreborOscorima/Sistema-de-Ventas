import reflex as rx
from typing import TypedDict, Union
import datetime
import uuid
import logging
import bcrypt
from app.states.auth_state import AuthState, User, Privileges


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


class NewUser(TypedDict):
    username: str
    password: str
    confirm_password: str
    role: str
    privileges: Privileges


class State(AuthState):
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
    show_user_form: bool = False
    editing_user: User | None = None
    new_user_data: NewUser = {
        "username": "",
        "password": "",
        "confirm_password": "",
        "role": "Usuario",
        "privileges": {
            "view_ingresos": False,
            "create_ingresos": False,
            "view_ventas": False,
            "create_ventas": False,
            "view_inventario": False,
            "edit_inventario": False,
            "view_historial": False,
            "export_data": False,
            "manage_users": False,
        },
    }

    @rx.var
    def current_user(self) -> User:
        if not self.token:
            return self._guest_user()
        user = self.users.get(self.token)
        if user:
            return user
        return self._guest_user()

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
        if not self.current_user["privileges"]["view_inventario"]:
            return []
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
        if not self.current_user["privileges"]["view_historial"]:
            return []
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
        if total_items == 0:
            return 1
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

    @rx.var
    def user_list(self) -> list[User]:
        if not self.current_user["privileges"]["manage_users"]:
            return []
        return sorted(list(self.users.values()), key=lambda u: u["username"])

    @rx.event
    def set_page(self, page: str):
        self.current_page = page
        if self.sidebar_open:
            pass

    @rx.event
    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    @rx.event
    def handle_entry_change(self, field: str, value: str):
        try:
            if field in ["quantity", "price"]:
                self.new_entry_item[field] = float(value) if value else 0
            else:
                self.new_entry_item[field] = value
            self.new_entry_item["subtotal"] = (
                self.new_entry_item["quantity"] * self.new_entry_item["price"]
            )
        except ValueError as e:
            logging.exception(f"Error parsing entry value: {e}")

    @rx.event
    def add_item_to_entry(self):
        if not self.current_user["privileges"]["create_ingresos"]:
            return rx.toast("No tiene permisos para crear ingresos.", duration=3000)
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
        if not self.current_user["privileges"]["create_ingresos"]:
            return rx.toast("No tiene permisos para crear ingresos.", duration=3000)
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
    def handle_sale_change(self, field: str, value: Union[str, float]):
        try:
            if field in ["quantity", "price"]:
                self.new_sale_item[field] = float(value) if value else 0
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
                        if str(value).lower() in p["description"].lower()
                    ][:5]
                else:
                    self.autocomplete_suggestions = []
        except ValueError as e:
            logging.exception(f"Error parsing sale value: {e}")

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
    def add_item_to_sale(self):
        if not self.current_user["privileges"]["create_ventas"]:
            return rx.toast("No tiene permisos para crear ventas.", duration=3000)
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
        if not self.current_user["privileges"]["create_ventas"]:
            return rx.toast("No tiene permisos para crear ventas.", duration=3000)
        if not self.new_sale_items:
            return rx.toast("No hay productos en la venta.", duration=3000)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in self.new_sale_items:
            product_id = item["description"].lower().strip()
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
                    f"Stock insuficiente para {item['description']}.", duration=3000
                )
        self.new_sale_items = []
        return rx.toast("Venta confirmada.", duration=3000)

    @rx.event
    def set_history_page(self, page_num: int):
        if 1 <= page_num <= self.total_pages:
            self.current_page_history = page_num

    @rx.event
    def apply_history_filters(self):
        self.history_filter_type = self.staged_history_filter_type
        self.history_filter_product = self.staged_history_filter_product
        self.history_filter_start_date = self.staged_history_filter_start_date
        self.history_filter_end_date = self.staged_history_filter_end_date
        self.current_page_history = 1

    @rx.event
    def reset_history_filters(self):
        self.staged_history_filter_type = "Todos"
        self.staged_history_filter_product = ""
        self.staged_history_filter_start_date = ""
        self.staged_history_filter_end_date = ""
        self.apply_history_filters()

    @rx.event
    def export_to_excel(self):
        if not self.current_user["privileges"]["export_data"]:
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)
        import openpyxl
        from io import BytesIO

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Historial Movimientos"
        headers = ["Fecha y Hora", "Tipo", "Descripción", "Cantidad", "Unidad", "Total"]
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
        file_stream = BytesIO()
        workbook.save(file_stream)
        file_stream.seek(0)
        return rx.download(
            data=file_stream.read(), filename="historial_movimientos.xlsx"
        )

    def _reset_new_user_form(self):
        self.new_user_data = {
            "username": "",
            "password": "",
            "confirm_password": "",
            "role": "Usuario",
            "privileges": {
                "view_ingresos": False,
                "create_ingresos": False,
                "view_ventas": False,
                "create_ventas": False,
                "view_inventario": False,
                "edit_inventario": False,
                "view_historial": False,
                "export_data": False,
                "manage_users": False,
            },
        }
        self.editing_user = None

    @rx.event
    def show_create_user_form(self):
        self._reset_new_user_form()
        self.show_user_form = True

    @rx.event
    def show_edit_user_form(self, user: User):
        self.new_user_data = {
            "username": user["username"],
            "password": "",
            "confirm_password": "",
            "role": user["role"],
            "privileges": user["privileges"].copy(),
        }
        self.editing_user = user
        self.show_user_form = True

    @rx.event
    def hide_user_form(self):
        self.show_user_form = False
        self._reset_new_user_form()

    @rx.event
    def handle_new_user_change(self, field: str, value: str):
        self.new_user_data[field] = value

    @rx.event
    def toggle_privilege(self, privilege: str):
        self.new_user_data["privileges"][privilege] = not self.new_user_data[
            "privileges"
        ][privilege]

    @rx.event
    def save_user(self):
        if not self.current_user["privileges"]["manage_users"]:
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        username = self.new_user_data["username"].lower().strip()
        if not username:
            return rx.toast("El nombre de usuario no puede estar vacío.", duration=3000)
        if self.editing_user:
            user_to_update = self.users.get(self.editing_user["username"])
            if not user_to_update:
                return rx.toast("Usuario a editar no encontrado.", duration=3000)
            if self.new_user_data["password"]:
                if (
                    self.new_user_data["password"]
                    != self.new_user_data["confirm_password"]
                ):
                    return rx.toast("Las contraseñas no coinciden.", duration=3000)
                password_hash = bcrypt.hashpw(
                    self.new_user_data["password"].encode(), bcrypt.gensalt()
                ).decode()
                user_to_update["password_hash"] = password_hash
            user_to_update["role"] = self.new_user_data["role"]
            user_to_update["privileges"] = self.new_user_data["privileges"].copy()
            self.hide_user_form()
            return rx.toast(f"Usuario {username} actualizado.", duration=3000)
        else:
            if username in self.users:
                return rx.toast("El nombre de usuario ya existe.", duration=3000)
            if not self.new_user_data["password"]:
                return rx.toast("La contraseña no puede estar vacía.", duration=3000)
            if self.new_user_data["password"] != self.new_user_data["confirm_password"]:
                return rx.toast("Las contraseñas no coinciden.", duration=3000)
            password_hash = bcrypt.hashpw(
                self.new_user_data["password"].encode(), bcrypt.gensalt()
            ).decode()
            self.users[username] = {
                "username": username,
                "password_hash": password_hash,
                "role": self.new_user_data["role"],
                "privileges": self.new_user_data["privileges"].copy(),
            }
            self.hide_user_form()
            return rx.toast(f"Usuario {username} creado.", duration=3000)

    @rx.event
    def delete_user(self, username: str):
        if not self.current_user["privileges"]["manage_users"]:
            return rx.toast("No tiene permisos para eliminar usuarios.", duration=3000)
        if username == "admin":
            return rx.toast("No se puede eliminar al superadmin.", duration=3000)
        if username == self.current_user["username"]:
            return rx.toast("No puedes eliminar tu propio usuario.", duration=3000)
        if self.users.pop(username, None):
            return rx.toast(f"Usuario {username} eliminado.", duration=3000)
        return rx.toast(f"Usuario {username} no encontrado.", duration=3000)