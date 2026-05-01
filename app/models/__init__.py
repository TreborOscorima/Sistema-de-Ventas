from .auth import Permission, Role, RolePermission, User, UserBranch
from .company import Branch, Company
from .owner import OwnerAuditLog
from .inventory import (
    Category,
    FieldPrice,
    PriceTier,
    Product,
    ProductAttribute,
    ProductBatch,
    ProductKit,
    ProductVariant,
    StockMovement,
    Unit,
)
from .purchases import (
    Purchase,
    PurchaseItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)
from .sales import (
    CashboxLog,
    CashboxSession,
    CompanySettings,
    Currency,
    FieldReservation,
    PaymentMethod,
    Sale,
    SaleItem,
    SalePayment,
    SaleInstallment,
    SaleReturn,
    SaleReturnItem,
)
# PriceList ANTES de Client — Client.price_list_id referencia pricelist.id
from .price_lists import PriceList, PriceListItem
from .client import Client
# billing DESPUÉS de sales — FiscalDocument.sale necesita que Sale
# esté registrado en el class registry de SQLAlchemy.
from .billing import CompanyBillingConfig, FiscalDocument
from .lookup_cache import DocumentLookupCache
from .platform_config import PlatformBillingSettings
# Presupuestos DESPUÉS de sales y client (FK a sale.id y client.id)
from .quotations import Quotation, QuotationItem
# Promociones: FK opcional a product.id
from .promotions import Promotion, PromotionProduct

__all__ = [
    "Permission",
    "Role",
    "RolePermission",
    "User",
    "UserBranch",
    "Company",
    "Branch",
    "Category",
    "FieldPrice",
    "PriceTier",
    "Product",
    "ProductAttribute",
    "ProductBatch",
    "ProductKit",
    "ProductVariant",
    "StockMovement",
    "Unit",
    "Supplier",
    "Purchase",
    "PurchaseItem",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "PurchaseOrderStatus",
    "Sale",
    "SaleItem",
    "SalePayment",
    "SaleInstallment",
    "PriceList",
    "PriceListItem",
    "Client",
    "CashboxSession",
    "CashboxLog",
    "FieldReservation",
    "PaymentMethod",
    "Currency",
    "CompanySettings",
    "OwnerAuditLog",
    "SaleReturn",
    "SaleReturnItem",
    "CompanyBillingConfig",
    "FiscalDocument",
    "DocumentLookupCache",
    "PlatformBillingSettings",
    "Quotation",
    "QuotationItem",
    "Promotion",
    "PromotionProduct",
]
