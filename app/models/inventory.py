from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

import reflex as rx
from sqlmodel import Field, Relationship
import sqlalchemy
from sqlalchemy import CheckConstraint, Numeric

from app.enums import SportType
from app.utils.timezone import utc_now_naive

from ._mixins import TenantMixin

if TYPE_CHECKING:
    from .auth import User
    from .sales import SaleItem


class Product(TenantMixin, rx.Model, table=True):
    """Modelo de producto de inventario."""

    __tablename__ = "product"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "barcode",
            name="uq_product_company_branch_barcode",
        ),
        sqlalchemy.Index(
            "ix_product_search",
            "category",
            "description",
        ),
        sqlalchemy.Index(
            "ix_product_tenant_category",
            "company_id",
            "branch_id",
            "category",
        ),
        sqlalchemy.Index(
            "ix_product_tenant_barcode",
            "company_id",
            "branch_id",
            "barcode",
        ),
    )

    __mapper_args__ = {"eager_defaults": True}

    barcode: str = Field(index=True, nullable=False)
    description: str = Field(nullable=False, index=True)
    category: str = Field(default="General", index=True)
    stock: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    unit: str = Field(default="Unidad")
    purchase_price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    sale_price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
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
    location: Optional[str] = Field(default=None)
    min_stock_alert: Decimal = Field(
        default=Decimal("5.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4), nullable=False, server_default="5.0000"),
    )
    # Proveedor preferido para reposición automática (nullable: no todos los
    # productos tienen proveedor fijo).
    default_supplier_id: Optional[int] = Field(
        default=None,
        foreign_key="supplier.id",
        index=True,
    )

    # ── Campos fiscales (para facturación electrónica SUNAT/AFIP) ──
    # tax_included=True → precio incluye impuesto (IGV/IVA)
    # tax_rate=18.00 → IGV 18% Perú / IVA 21% Argentina
    # tax_category → "gravado", "exonerado", "inafecto", "gratuito"
    tax_included: bool = Field(default=True)
    tax_rate: Decimal = Field(
        default=Decimal("18.00"),
        sa_column=sqlalchemy.Column(Numeric(5, 2), nullable=False, server_default="18.00"),
    )
    tax_category: str = Field(default="gravado", max_length=20)

    # Auditoría de cambio de precio: permite filtrar productos con precio
    # modificado esta semana en el generador masivo de etiquetas.
    sale_price_updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
            nullable=True,
            index=True,
        ),
    )

    sale_items: List["SaleItem"] = Relationship(
        back_populates="product",
        sa_relationship_kwargs={"foreign_keys": "[SaleItem.product_id]"},
    )
    variants: List["ProductVariant"] = Relationship(back_populates="product")
    batches: List["ProductBatch"] = Relationship(back_populates="product")
    price_tiers: List["PriceTier"] = Relationship(back_populates="product")
    kit_components: List["ProductKit"] = Relationship(
        back_populates="kit_product",
        sa_relationship_kwargs={"foreign_keys": "[ProductKit.kit_product_id]"},
    )
    part_of_kits: List["ProductKit"] = Relationship(
        back_populates="component_product",
        sa_relationship_kwargs={"foreign_keys": "[ProductKit.component_product_id]"},
    )
    attributes: List["ProductAttribute"] = Relationship(back_populates="product")


class ProductVariant(TenantMixin, rx.Model, table=True):
    """Variantes de producto (talla/color)."""

    __tablename__ = "productvariant"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "sku",
            name="uq_productvariant_company_branch_sku",
        ),
        sqlalchemy.Index(
            "ix_productvariant_tenant_product",
            "company_id",
            "branch_id",
            "product_id",
        ),
    )

    product_id: int = Field(foreign_key="product.id", index=True)
    sku: str = Field(index=True, nullable=False)
    size: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default=None)
    stock: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    # Umbral de alerta de stock bajo por variante.
    # NULL = heredar del Product padre (Product.min_stock_alert).
    # Permite que una talla XL escasa dispare alerta aunque el producto raíz tenga stock.
    min_stock_alert: Optional[Decimal] = Field(
        default=None,
        sa_column=sqlalchemy.Column(Numeric(10, 4), nullable=True),
    )

    product: "Product" = Relationship(back_populates="variants")
    batches: List["ProductBatch"] = Relationship(back_populates="product_variant")
    price_tiers: List["PriceTier"] = Relationship(back_populates="product_variant")
    sale_items: List["SaleItem"] = Relationship(back_populates="product_variant")


class ProductBatch(TenantMixin, rx.Model, table=True):
    """Lotes con vencimiento (FEFO)."""

    __tablename__ = "productbatch"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "product_id",
            "product_variant_id",
            "batch_number",
            name="uq_productbatch_company_branch_product_batch",
        ),
        sqlalchemy.Index(
            "ix_productbatch_tenant_variant",
            "company_id",
            "branch_id",
            "product_variant_id",
        ),
        sqlalchemy.Index(
            "ix_productbatch_tenant_product",
            "company_id",
            "branch_id",
            "product_id",
        ),
    )

    batch_number: str = Field(index=True, nullable=False)
    expiration_date: Optional[datetime] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False), index=True
        ),
    )
    stock: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    product_id: Optional[int] = Field(default=None, foreign_key="product.id", index=True)
    product_variant_id: Optional[int] = Field(
        default=None,
        foreign_key="productvariant.id",
        index=True,
    )

    product: Optional["Product"] = Relationship(back_populates="batches")
    product_variant: Optional["ProductVariant"] = Relationship(
        back_populates="batches"
    )
    sale_items: List["SaleItem"] = Relationship(back_populates="product_batch")


class ProductKit(TenantMixin, rx.Model, table=True):
    """Definicion de kits (producto compuesto)."""

    __tablename__ = "productkit"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "kit_product_id",
            "component_product_id",
            name="uq_productkit_company_branch_component",
        ),
        CheckConstraint("quantity > 0", name="ck_productkit_quantity_positive"),
    )

    # ondelete CASCADE: si se borra el producto-kit o el componente,
    # la relación de explosión pierde sentido → limpia automáticamente.
    kit_product_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    component_product_id: int = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    quantity: Decimal = Field(
        default=Decimal("1.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )

    kit_product: "Product" = Relationship(
        back_populates="kit_components",
        sa_relationship_kwargs={"foreign_keys": "[ProductKit.kit_product_id]"},
    )
    component_product: "Product" = Relationship(
        back_populates="part_of_kits",
        sa_relationship_kwargs={"foreign_keys": "[ProductKit.component_product_id]"},
    )


class PriceTier(TenantMixin, rx.Model, table=True):
    """Escalas de precios por cantidad."""

    __tablename__ = "pricetier"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "product_id",
            "product_variant_id",
            "min_quantity",
            name="uq_pricetier_company_branch_product_minqty",
        ),
    )

    min_quantity: int = Field(nullable=False)
    unit_price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    product_variant_id: Optional[int] = Field(
        default=None,
        foreign_key="productvariant.id",
    )

    product: Optional["Product"] = Relationship(back_populates="price_tiers")
    product_variant: Optional["ProductVariant"] = Relationship(
        back_populates="price_tiers"
    )


class ProductAttribute(TenantMixin, rx.Model, table=True):
    """Atributos dinámicos por producto/variante (EAV ligero).

    Permite atributos específicos por rubro sin modificar el schema:
    - Ferretería: material=acero, calibre=1/2", rosca=fina
    - Farmacia: principio_activo=ibuprofeno, laboratorio=Bayer, dosaje=400mg
    - Ropa: temporada=verano, marca=Nike (talla/color ya están en ProductVariant)
    - Juguetería: edad_minima=3, marca=Hasbro
    """

    __tablename__ = "productattribute"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "product_id",
            "attribute_name",
            name="uq_productattribute_product_attr",
        ),
        sqlalchemy.Index(
            "ix_productattribute_tenant_product",
            "company_id",
            "branch_id",
            "product_id",
        ),
        sqlalchemy.Index(
            "ix_productattribute_name_value",
            "company_id",
            "attribute_name",
            "attribute_value",
        ),
    )

    product_id: int = Field(foreign_key="product.id", index=True, nullable=False)
    attribute_name: str = Field(max_length=100, index=True, nullable=False)
    attribute_value: str = Field(max_length=500, nullable=False, default="")

    product: Optional["Product"] = Relationship(back_populates="attributes")


class Category(TenantMixin, rx.Model, table=True):
    """Categorias de productos."""

    __tablename__ = "category"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "name",
            name="uq_category_company_branch_name",
        ),
    )

    name: str = Field(nullable=False)
    requires_batch: bool = Field(default=False)


class StockMovement(TenantMixin, rx.Model, table=True):
    """Movimientos de stock (ingresos, ajustes)."""

    __tablename__ = "stockmovement"

    __table_args__ = (
        sqlalchemy.Index(
            "ix_stockmovement_tenant_timestamp",
            "company_id",
            "branch_id",
            "timestamp",
        ),
        sqlalchemy.Index(
            "ix_stockmovement_tenant_product",
            "company_id",
            "branch_id",
            "product_id",
        ),
    )

    timestamp: datetime = Field(
        default_factory=utc_now_naive,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=False),
        ),
    )
    type: str = Field(nullable=False, index=True)
    quantity: Decimal = Field(
        default=Decimal("0.0000"),
        sa_column=sqlalchemy.Column(Numeric(10, 4)),
    )
    description: str = Field(default="")

    # SET NULL: preservamos la historia de movimientos aunque se borre el
    # producto o el usuario (compliance contable / auditoría).
    product_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("product.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    user_id: Optional[int] = Field(
        default=None,
        sa_column=sqlalchemy.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    product: Optional["Product"] = Relationship()
    user: Optional["User"] = Relationship()


class Unit(TenantMixin, rx.Model, table=True):
    """Unidades de medida."""

    __tablename__ = "unit"

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "company_id",
            "branch_id",
            "name",
            name="uq_unit_company_branch_name",
        ),
    )

    name: str = Field(index=True, nullable=False)
    allows_decimal: bool = Field(default=False)


class FieldPrice(TenantMixin, rx.Model, table=True):
    """Precios de alquiler de canchas."""

    __tablename__ = "fieldprice"

    sport: SportType = Field(nullable=False)
    name: str = Field(nullable=False)
    price: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=sqlalchemy.Column(Numeric(10, 2)),
    )
