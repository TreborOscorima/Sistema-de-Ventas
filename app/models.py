import reflex as rx
from typing import Optional, List, Dict
from datetime import datetime
from sqlmodel import Field, Relationship, JSON, Column
import sqlalchemy

class User(rx.Model, table=True):
    """Modelo de Usuario con privilegios en JSON."""
    username: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    role: str = Field(default="empleado")
    is_active: bool = Field(default=True)
    
    # Almacenamos los privilegios como un objeto JSON para flexibilidad
    # Ejemplo: {"view_ventas": True, "create_ventas": False}
    privileges: Dict = Field(default={}, sa_column=Column(JSON))

    # Relaciones
    sales: List["Sale"] = Relationship(back_populates="user")
    sessions: List["CashboxSession"] = Relationship(back_populates="user")
    logs: List["CashboxLog"] = Relationship(back_populates="user")
    reservations: List["FieldReservation"] = Relationship(back_populates="user")

class Product(rx.Model, table=True):
    """Modelo de Producto de Inventario."""
    barcode: str = Field(unique=True, index=True, nullable=False)
    description: str = Field(nullable=False)
    category: str = Field(default="General", index=True)
    stock: float = Field(default=0.0)
    unit: str = Field(default="Unidad")
    purchase_price: float = Field(default=0.0)
    sale_price: float = Field(default=0.0)
    
    # Relaciones
    sale_items: List["SaleItem"] = Relationship(back_populates="product")

class Sale(rx.Model, table=True):
    """Cabecera de Venta."""
    timestamp: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False), server_default=sqlalchemy.func.now())
    )
    total_amount: float = Field(default=0.0)
    payment_method: str = Field(default="Efectivo")
    
    # Detalles complejos del pago (JSON o Texto)
    payment_details: str = Field(default="") 
    
    is_deleted: bool = Field(default=False)
    delete_reason: Optional[str] = Field(default=None)
    
    # Claves Foráneas
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Relaciones
    user: Optional[User] = Relationship(back_populates="sales")
    items: List["SaleItem"] = Relationship(back_populates="sale")

class SaleItem(rx.Model, table=True):
    """Detalle de Venta (TransactionItem)."""
    quantity: float = Field(default=1.0)
    unit_price: float = Field(default=0.0)
    subtotal: float = Field(default=0.0)
    
    # Guardamos snapshot del producto por si se borra o cambia el original
    product_name_snapshot: str = Field(default="")
    product_barcode_snapshot: str = Field(default="")

    # Claves Foráneas
    sale_id: int = Field(foreign_key="sale.id")
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    
    # Relaciones
    sale: Optional[Sale] = Relationship(back_populates="items")
    product: Optional[Product] = Relationship(back_populates="sale_items")

class CashboxSession(rx.Model, table=True):
    """Sesión de Caja (Apertura/Cierre)."""
    opening_time: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False))
    )
    closing_time: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False))
    )
    opening_amount: float = Field(default=0.0)
    closing_amount: float = Field(default=0.0)
    is_open: bool = Field(default=True)
    
    # Claves Foráneas
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Relaciones
    user: Optional[User] = Relationship(back_populates="sessions")

class CashboxLog(rx.Model, table=True):
    """Log de movimientos de caja."""
    timestamp: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False))
    )
    action: str = Field(nullable=False) # apertura, cierre, etc.
    amount: float = Field(default=0.0)
    notes: str = Field(default="")
    
    # Claves Foráneas
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Relaciones
    user: Optional[User] = Relationship(back_populates="logs")

class FieldReservation(rx.Model, table=True):
    """Reserva de Canchas Deportivas."""
    client_name: str = Field(nullable=False)
    client_dni: Optional[str] = Field(default=None)
    client_phone: Optional[str] = Field(default=None)
    
    sport: str = Field(default="Futbol") # Futbol, Voley
    field_name: str = Field(nullable=False)
    
    # Fechas importantes (DateTime)
    start_datetime: datetime = Field(
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False))
    )
    end_datetime: datetime = Field(
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False))
    )
    
    total_amount: float = Field(default=0.0)
    paid_amount: float = Field(default=0.0)
    status: str = Field(default="pendiente") # pendiente, pagado, cancelado
    
    # Claves Foráneas
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Campos de auditoría y cancelación
    cancellation_reason: Optional[str] = Field(default=None)
    delete_reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False))
    )
    
    # Relaciones
    user: Optional[User] = Relationship(back_populates="reservations")

class Category(rx.Model, table=True):
    """Categorias de productos."""
    name: str = Field(unique=True, index=True, nullable=False)

class StockMovement(rx.Model, table=True):
    """Movimientos de Stock (Ingresos, Ajustes)."""
    timestamp: datetime = Field(
        default_factory=datetime.now,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False))
    )
    type: str = Field(nullable=False) # Ingreso, Ajuste
    quantity: float = Field(default=0.0)
    description: str = Field(default="")
    
    # Claves Foráneas
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Relaciones
    product: Optional[Product] = Relationship()
    user: Optional[User] = Relationship()

class Unit(rx.Model, table=True):
    """Unidades de medida."""
    name: str = Field(unique=True, index=True, nullable=False)
    allows_decimal: bool = Field(default=False)

class PaymentMethod(rx.Model, table=True):
    """Metodos de pago configurables."""
    method_id: str = Field(unique=True, index=True, nullable=False) # 'cash', 'card', etc.
    name: str = Field(nullable=False)
    description: str = Field(default="")
    kind: str = Field(default="other") # cash, card, wallet, mixed, other
    enabled: bool = Field(default=True)

class Currency(rx.Model, table=True):
    """Monedas disponibles."""
    code: str = Field(unique=True, index=True, nullable=False) # PEN, USD
    name: str = Field(nullable=False)
    symbol: str = Field(nullable=False)

class FieldPrice(rx.Model, table=True):
    """Precios de alquiler de canchas."""
    sport: str = Field(nullable=False) # Futbol, Voley
    name: str = Field(nullable=False) # "Hora Dia", "Hora Noche"
    price: float = Field(default=0.0)
