"""Modelos de Ofertas y Promociones.

Motor de descuentos automáticos aplicado al carrito de ventas.
Soporta tres tipos:
  - PERCENTAGE  : descuento porcentual (ej: 15% off)
  - FIXED_AMOUNT: descuento de monto fijo (ej: $10 off)
  - BUY_X_GET_Y : lleva X paga Y (ej: 3x2)

Scope de aplicación:
  - ALL      : aplica a cualquier producto
  - CATEGORY : aplica a una categoría específica
  - PRODUCT  : aplica a un producto específico (o variante)
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
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


class PromotionScope(str):
    ALL = "all"
    CATEGORY = "category"
    PRODUCT = "product"


class Promotion(TenantMixin, rx.Model, table=True):
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
        CheckConstraint("discount_value >= 0", name="ck_promotion_discount_nonneg"),
        CheckConstraint(
            "starts_at <= ends_at",
            name="ck_promotion_dates_order",
        ),
        CheckConstraint(
            "min_quantity >= 1",
            name="ck_promotion_min_qty_positive",
        ),
    )

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
