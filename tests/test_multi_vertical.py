"""Tests para funcionalidades multi-vertical (multi-rubro).

Cubre:
    - ProductAttribute (atributos dinámicos EAV)
    - Category.requires_batch (flag para rubros con lotes obligatorios)
    - Product.min_stock_alert (umbral configurable por producto)
    - CompanySettings.business_vertical (rubro del negocio)
    - inventory_state: stock_is_low respeta min_stock_alert
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-multi-vertical")
os.environ.setdefault("TENANT_STRICT", "0")


# ═════════════════════════════════════════════════════════════
# PRODUCT ATTRIBUTE MODEL
# ═════════════════════════════════════════════════════════════


class TestProductAttributeModel:
    """Tests para el modelo ProductAttribute (EAV ligero)."""

    def test_model_exists(self):
        from app.models.inventory import ProductAttribute
        assert ProductAttribute is not None

    def test_model_importable_from_init(self):
        from app.models import ProductAttribute
        assert ProductAttribute is not None

    def test_has_required_fields(self):
        from app.models.inventory import ProductAttribute
        fields = ProductAttribute.model_fields
        assert "product_id" in fields
        assert "attribute_name" in fields
        assert "attribute_value" in fields
        assert "company_id" in fields
        assert "branch_id" in fields

    def test_default_attribute_value(self):
        from app.models.inventory import ProductAttribute
        attr = ProductAttribute(
            product_id=1,
            attribute_name="material",
            company_id=1,
            branch_id=1,
        )
        assert attr.attribute_value == ""

    def test_ferreteria_attributes(self):
        """Ferretería: atributos dinámicos como material, calibre, rosca."""
        from app.models.inventory import ProductAttribute
        attrs = [
            ProductAttribute(product_id=1, attribute_name="material",
                             attribute_value="acero inoxidable",
                             company_id=1, branch_id=1),
            ProductAttribute(product_id=1, attribute_name="calibre",
                             attribute_value='1/2"',
                             company_id=1, branch_id=1),
            ProductAttribute(product_id=1, attribute_name="rosca",
                             attribute_value="fina",
                             company_id=1, branch_id=1),
        ]
        assert attrs[0].attribute_name == "material"
        assert attrs[1].attribute_value == '1/2"'
        assert attrs[2].attribute_value == "fina"

    def test_farmacia_attributes(self):
        """Farmacia: principio activo, laboratorio, dosaje."""
        from app.models.inventory import ProductAttribute
        attr = ProductAttribute(
            product_id=10,
            attribute_name="principio_activo",
            attribute_value="ibuprofeno 400mg",
            company_id=1,
            branch_id=1,
        )
        assert attr.attribute_name == "principio_activo"
        assert "ibuprofeno" in attr.attribute_value

    def test_product_has_attributes_relationship(self):
        from app.models.inventory import Product
        assert hasattr(Product, "attributes")


# ═════════════════════════════════════════════════════════════
# CATEGORY.REQUIRES_BATCH
# ═════════════════════════════════════════════════════════════


class TestCategoryRequiresBatch:
    """Tests para Category.requires_batch (GAP-02)."""

    def test_field_exists(self):
        from app.models.inventory import Category
        fields = Category.model_fields
        assert "requires_batch" in fields

    def test_default_false(self):
        from app.models.inventory import Category
        cat = Category(name="General", company_id=1, branch_id=1)
        assert cat.requires_batch is False

    def test_farmacia_requires_batch(self):
        """Categoría farmacia debe requerir lote obligatorio."""
        from app.models.inventory import Category
        cat = Category(
            name="Medicamentos",
            company_id=1,
            branch_id=1,
            requires_batch=True,
        )
        assert cat.requires_batch is True

    def test_ferreteria_no_requires_batch(self):
        """Ferretería no requiere lotes."""
        from app.models.inventory import Category
        cat = Category(
            name="Tornillos",
            company_id=1,
            branch_id=1,
            requires_batch=False,
        )
        assert cat.requires_batch is False


# ═════════════════════════════════════════════════════════════
# PRODUCT.MIN_STOCK_ALERT
# ═════════════════════════════════════════════════════════════


class TestProductMinStockAlert:
    """Tests para Product.min_stock_alert (GAP-05)."""

    def test_field_exists(self):
        from app.models.inventory import Product
        fields = Product.model_fields
        assert "min_stock_alert" in fields

    def test_default_is_5(self):
        from app.models.inventory import Product
        p = Product(
            barcode="TEST001",
            description="Test",
            company_id=1,
            branch_id=1,
        )
        assert p.min_stock_alert == Decimal("5.0000")

    def test_custom_threshold(self):
        """Un producto de ferretería con stock masivo puede tener umbral alto."""
        from app.models.inventory import Product
        p = Product(
            barcode="TORN-001",
            description="Tornillo 1/4",
            company_id=1,
            branch_id=1,
            min_stock_alert=Decimal("100.0000"),
        )
        assert p.min_stock_alert == Decimal("100.0000")

    def test_fractional_threshold(self):
        """Bodega: umbral de 0.5 kg para producto fraccionado."""
        from app.models.inventory import Product
        p = Product(
            barcode="QUESO-001",
            description="Queso fresco",
            company_id=1,
            branch_id=1,
            min_stock_alert=Decimal("0.5000"),
        )
        assert p.min_stock_alert == Decimal("0.5000")


# ═════════════════════════════════════════════════════════════
# COMPANYSETTINGS.BUSINESS_VERTICAL
# ═════════════════════════════════════════════════════════════


class TestBusinessVertical:
    """Tests para CompanySettings.business_vertical (GAP-03)."""

    def test_field_exists(self):
        from app.models.sales import CompanySettings
        fields = CompanySettings.model_fields
        assert "business_vertical" in fields

    def test_default_general(self):
        from app.models.sales import CompanySettings
        cs = CompanySettings(company_id=1, branch_id=1)
        assert cs.business_vertical == "general"

    def test_valid_verticals(self):
        """Todos los rubros válidos deben ser asignables."""
        from app.models.sales import CompanySettings
        for vertical in [
            "general", "bodega", "ferreteria", "farmacia",
            "ropa", "jugueteria", "restaurante", "supermercado",
        ]:
            cs = CompanySettings(
                company_id=1, branch_id=1,
                business_vertical=vertical,
            )
            assert cs.business_vertical == vertical

    def test_config_state_has_business_vertical(self):
        """ConfigState debe tener selected_business_vertical."""
        from app.states.config_state import ConfigState
        assert hasattr(ConfigState, "selected_business_vertical")


# ═════════════════════════════════════════════════════════════
# INVENTORY STATE — stock_is_low respeta min_stock_alert
# ═════════════════════════════════════════════════════════════


class TestStockAlertInventoryState:
    """Tests para inventory_state usando min_stock_alert per-producto."""

    def test_low_stock_threshold_alias_exists(self):
        """LOW_STOCK_THRESHOLD debe existir como alias de compatibilidad."""
        from app.states.inventory_state import LOW_STOCK_THRESHOLD
        assert LOW_STOCK_THRESHOLD == 5

    def test_default_low_stock_threshold(self):
        from app.states.inventory_state import DEFAULT_LOW_STOCK_THRESHOLD
        assert DEFAULT_LOW_STOCK_THRESHOLD == 5

    def test_row_uses_min_stock_alert(self):
        """_inventory_row_from_product debe respetar min_stock_alert."""
        from app.states.inventory_state import InventoryState
        state = InventoryState.__new__(InventoryState)

        product = MagicMock()
        product.id = 1
        product.barcode = "TEST001"
        product.description = "Tornillo"
        product.category = "Ferretería"
        product.stock = Decimal("50")
        product.min_stock_alert = Decimal("100")  # umbral alto
        product.unit = "Unidad"
        product.purchase_price = Decimal("1.00")
        product.sale_price = Decimal("2.00")

        row = state._inventory_row_from_product(product)
        # 50 <= 100 → es stock bajo
        assert row["stock_is_low"] is True

    def test_row_not_low_when_above_threshold(self):
        """Producto con stock sobre su umbral personalizado no es stock bajo."""
        from app.states.inventory_state import InventoryState
        state = InventoryState.__new__(InventoryState)

        product = MagicMock()
        product.id = 2
        product.barcode = "LAPI-001"
        product.description = "Lapicero"
        product.category = "General"
        product.stock = Decimal("20")
        product.min_stock_alert = Decimal("5")  # umbral bajo
        product.unit = "Unidad"
        product.purchase_price = Decimal("0.50")
        product.sale_price = Decimal("1.00")

        row = state._inventory_row_from_product(product)
        # 20 > 5 → no es stock bajo
        assert row["stock_is_low"] is False

    def test_row_uses_default_when_no_min_stock_alert(self):
        """Si min_stock_alert es None/0, usa DEFAULT_LOW_STOCK_THRESHOLD (5)."""
        from app.states.inventory_state import InventoryState
        state = InventoryState.__new__(InventoryState)

        product = MagicMock()
        product.id = 3
        product.barcode = "OLD-001"
        product.description = "Producto antiguo"
        product.category = "General"
        product.stock = Decimal("3")
        product.min_stock_alert = None  # no configurado
        product.unit = "Unidad"
        product.purchase_price = Decimal("1.00")
        product.sale_price = Decimal("2.00")

        row = state._inventory_row_from_product(product)
        # 3 <= 5 (default) → es stock bajo
        assert row["stock_is_low"] is True


# ═════════════════════════════════════════════════════════════
# MIGRATION VALIDATION
# ═════════════════════════════════════════════════════════════


class TestMultiVerticalMigration:
    """Verifica que la migración existe y tiene la cadena correcta."""

    def test_migration_file_exists(self):
        import importlib.util
        import os
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "alembic", "versions",
            "l6m7n8o9p0q1_add_multi_vertical_fields.py",
        )
        spec = importlib.util.spec_from_file_location("migration_l6", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod.revision == "l6m7n8o9p0q1"
        assert mod.down_revision == "k5l6m7n8o9p0"

    def test_migration_has_upgrade(self):
        import importlib.util
        import os
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "alembic", "versions",
            "l6m7n8o9p0q1_add_multi_vertical_fields.py",
        )
        spec = importlib.util.spec_from_file_location("migration_l6b", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert callable(mod.upgrade)
        assert callable(mod.downgrade)
