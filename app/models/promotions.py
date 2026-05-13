"""Modelos de Ofertas y Promociones.

Motor de descuentos automáticos aplicado al carrito de ventas.
Soporta cuatro tipos:
  - PERCENTAGE       : descuento porcentual (ej: 15% off)
  - FIXED_AMOUNT     : descuento de monto fijo (ej: $10 off)
  - BUY_X_GET_Y      : lleva X paga Y (ej: 3x2)
  - NTH_UNIT_DISCOUNT: cada N unidades, la Nth tiene X% de descuento (ej: 2da unidad 70% off)

Scope de aplicación:
  - ALL      : aplica a cualquier producto
  - CATEGORY : aplica a una categoría específica
  - PRODUCT  : aplica a un producto específico (o variante)
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime, time
from decimal import Decimal

from sqlmodel import Field, Relationship, SQLModel
import sqlalchemy
from sqlalchemy import CheckConstraint, Numeric

from app.utils.timezone import utc_now_naive
from ._mixins import TenantMixin

if TYPE_CHECKING:
    from .inventory import Product
    from .auth import User


class PromotionType(str):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_X_GET_Y = "buy_x_get_y"
    NTH_UNIT_DISCOUNT = "nth_unit_discount"


class PromotionScope(str):
    ALL = "all"
    CATEGORY = "category"
    PRODUCT = "product"


class Promotion(TenantMixin, SQLModel, table=True):
    """Regla de promoción/descuento automático aplicada en la venta."""

    __tablename__ = "promotion"

    __table_args__ = (
        sqlalchemy.Index(
            "ix_promotion_tenant_active",
            "company_id",
            "branch_id",
            "is_active",
            "starts_at",
            "ends_at",
        ),
        sqlalchemy.Index(
            "ix_promotion_tenant_product",
            "company_id",
            "branch_id",
            "product_id",
        ),
        sqlalchemy.UniqueConstraint(
            "company_id",
            "coupon_code",
            name="uq_promotion_company_coupon_code",
        ),
        CheckConstraint("discount_value >= 0", name="ck_promotion_discount_nonneg"),
        CheckConstraint(
            "starts_at <= ends_at",
            name="ck_promotion_dates_order",
        ),
        CheckConstraint(
            "min_quantity >= 1",
            name="ck_promotion_min_qty_positive",
        ),
        CheckConstraint(
            "weekdays_mask BETWEEN 0 AND 127",
            name="ck_promotion_weekdays_mask_range",
        ),
        CheckConstraint(
            "min_cart_amount >= 0",
            name="ck_promotion_min_cart_amount_nonneg",
        ),
        CheckConstraint(
            "max_units_per_transaction IS NULL OR max_units_per_transaction >= 1",
            name="ck_promotion_max_units_per_tx_pos",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=150, index=True)
    description: Optional[str] = Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.Text)
    )

    # Tipo de descuento
    promotion_type: str = Field(
        default=PromotionType.PERCENTAGE,
        max_length=20,
        index=True,
    )

    # Ámbito de aplicación
    scope: str = Field(
        default=PromotionScope.ALL,
        max_length=20,
        index=True,
    )

    # Valor del descuento: % o monto según promotion_type
    discount_value: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2), nullable=False, server_default="0.00"),
    )

    # Para BUY_X_GET_Y: compra min_quantity → recibe free_quantity gratis
    min_quantity: int = Field(
        default=1,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer, nullable=False, server_default="1"
        ),
    )
    free_quantity: int = Field(
        default=0,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer, nullable=False, server_default="0"
        ),
    )

    # Límite de unidades que reciben el descuento por transacción.
    # NULL = sin límite. ej: "25% off, máx 8 unidades por ticket".
    max_units_per_transaction: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.Integer, nullable=True),
    )

    # Vigencia temporal
    starts_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False), nullable=False),
    )
    ends_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False), nullable=False),
    )

    is_active: bool = Field(
        default=True,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Boolean,
            nullable=False,
            server_default=sqlalchemy.text("1"),
            index=True,
        ),
    )

    # Días de la semana en los que aplica la promo. Bitmask:
    #   Lunes=1, Martes=2, Miércoles=4, Jueves=8, Viernes=16, Sábado=32, Domingo=64.
    # Default 127 = todos los días (compatibilidad hacia atrás).
    weekdays_mask: int = Field(
        default=127,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer, nullable=False, server_default="127"
        ),
    )

    # Banda horaria opcional. Si ambas son NULL, aplica todo el día.
    # Si time_from > time_to, el rango cruza medianoche (ej: 22:00 → 02:00).
    time_from: Optional[time] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.Time(timezone=False), nullable=True),
    )
    time_to: Optional[time] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.Time(timezone=False), nullable=True),
    )

    # Código de cupón. NULL = promo automática (siempre se evalúa).
    # No-NULL = sólo aplica si el cliente ingresa el código en el POS.
    # UNIQUE por company_id (NULL no choca consigo mismo en MySQL).
    coupon_code: Optional[str] = Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.String(40), nullable=True, index=True),
    )

    # Umbral de subtotal del carrito requerido para que aplique la promo.
    # 0 = sin umbral (default histórico, no rompe promos pre-migración).
    # >0 = la promo sólo dispara cuando SUM(qty × base_price) >= min_cart_amount.
    # Útil para campañas tipo "10% off si el carrito supera $1000".
    min_cart_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(
            Numeric(12, 2), nullable=False, server_default="0.00"
        ),
    )

    # Límite de usos (NULL = ilimitado)
    max_uses: Optional[int] = Field(default=None, sa_column=sqlalchemy.Column(sqlalchemy.Integer, nullable=True))
    current_uses: int = Field(
        default=0,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer, nullable=False, server_default="0"
        ),
    )

    created_at: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=False)),
    )

    # Scope PRODUCT: FK al producto específico
    product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Scope CATEGORY: nombre de categoría
    category: Optional[str] = Field(default=None, max_length=100, index=True)

    # Quién creó la promoción
    created_by_user_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    product: Optional["Product"] = Relationship()
    created_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Promotion.created_by_user_id]"}
    )


class PromotionProduct(SQLModel, table=True):
    """Asociación promoción ↔ producto para scope=PRODUCT multi-producto.

    Reemplaza la relación 1-a-1 de ``Promotion.product_id`` permitiendo
    que una misma regla aplique a varios SKUs distintos. Backward-compat:
    si no hay filas aquí para una promo, el motor cae al ``product_id``
    heredado en ``Promotion``.
    """

    __tablename__ = "promotion_product"
    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "promotion_id", "product_id",
            name="uq_promotion_product_pair",
        ),
        sqlalchemy.Index("ix_promotion_product_promo", "promotion_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    promotion_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("promotion.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    product_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
