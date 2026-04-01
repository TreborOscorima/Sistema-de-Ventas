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
from .purchases import Purchase, PurchaseItem, Supplier
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
)
from .client import Client
# billing DESPUÉS de sales — FiscalDocument.sale necesita que Sale
# esté registrado en el class registry de SQLAlchemy.
from .billing import CompanyBillingConfig, FiscalDocument
from .lookup_cache import DocumentLookupCache
from .platform_config import PlatformBillingSettings

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
    "Sale",
    "SaleItem",
    "SalePayment",
    "SaleInstallment",
    "Client",
    "CashboxSession",
    "CashboxLog",
    "FieldReservation",
    "PaymentMethod",
    "Currency",
    "CompanySettings",
    "OwnerAuditLog",
    "CompanyBillingConfig",
    "FiscalDocument",
    "DocumentLookupCache",
    "PlatformBillingSettings",
]
