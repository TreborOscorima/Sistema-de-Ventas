from typing import TypedDict, List, Dict, Union

class Product(TypedDict):
    id: str
    barcode: str
    description: str
    category: str
    stock: float
    unit: str
    purchase_price: float
    sale_price: float

class TransactionItem(TypedDict):
    temp_id: str
    barcode: str
    description: str
    category: str
    quantity: float
    unit: str
    price: float
    sale_price: float
    subtotal: float

class Movement(TypedDict):
    id: str
    timestamp: str
    type: str
    product_description: str
    quantity: float
    unit: str
    total: float
    payment_method: str
    payment_details: str
    user: str
    sale_id: str

class CurrencyOption(TypedDict):
    code: str
    name: str
    symbol: str

class PaymentMethodConfig(TypedDict):
    id: str
    name: str
    description: str
    kind: str
    enabled: bool

class PaymentBreakdownItem(TypedDict):
    label: str
    amount: float

class FieldPrice(TypedDict):
    id: str
    sport: str
    name: str
    price: float

class FieldReservation(TypedDict):
    id: str
    client_name: str
    dni: str
    phone: str
    sport: str
    sport_label: str
    field_name: str
    start_datetime: str
    end_datetime: str
    advance_amount: float
    total_amount: float
    paid_amount: float
    status: str
    created_at: str
    cancellation_reason: str
    delete_reason: str

class ServiceLogEntry(TypedDict):
    id: str
    timestamp: str
    type: str
    sport: str
    client_name: str
    field_name: str
    amount: float
    status: str
    notes: str
    reservation_id: str

class ReservationReceipt(TypedDict):
    cliente: str
    deporte: str
    campo: str
    horario: str
    monto_adelanto: str
    monto_total: str
    saldo: str
    estado: str

class CashboxSale(TypedDict):
    sale_id: str
    timestamp: str
    user: str
    payment_method: str
    payment_label: str
    payment_breakdown: List[PaymentBreakdownItem]
    payment_details: str
    total: float
    service_total: float
    items: List[TransactionItem]
    is_deleted: bool
    delete_reason: str

class CashboxSession(TypedDict):
    opening_amount: float
    opening_time: str
    closing_time: str
    is_open: bool
    opened_by: str

class CashboxLogEntry(TypedDict):
    id: str
    action: str
    timestamp: str
    user: str
    opening_amount: float
    closing_total: float
    totals_by_method: List[Dict[str, float]]
    notes: str

class InventoryAdjustment(TypedDict):
    temp_id: str
    barcode: str
    description: str
    category: str
    unit: str
    current_stock: float
    adjust_quantity: float
    reason: str

class Privileges(TypedDict):
    view_ingresos: bool
    create_ingresos: bool
    view_ventas: bool
    create_ventas: bool
    view_inventario: bool
    edit_inventario: bool
    view_historial: bool
    export_data: bool
    view_cashbox: bool
    manage_cashbox: bool
    delete_sales: bool
    manage_users: bool
    view_servicios: bool
    manage_reservations: bool
    manage_config: bool

class NewUser(TypedDict):
    username: str
    password: str
    confirm_password: str
    role: str
    privileges: Privileges

class User(TypedDict):
    username: str
    password_hash: str
    role: str
    privileges: Privileges

