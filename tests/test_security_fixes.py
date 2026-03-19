"""Tests para fixes de seguridad aplicados en Sprints 0, 7, 13, 14.

Cubre:
- FIX 38: Tenant isolation (company_id/branch_id en queries)
- FIX 39: with_for_update en read-modify-write
- FIX 40: Info leakage — str(exc) no expuesto al usuario
- FIX 43: Precios negativos rechazados en canchas
"""
import ast
import re
import pytest


# ---------------------------------------------------------------------------
# Helpers para inspección estática de código fuente
# ---------------------------------------------------------------------------
def _read_source(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


BASE = "app/states"


# ---------------------------------------------------------------------------
# FIX 38a: SaleItem query in delete_product includes company_id
# ---------------------------------------------------------------------------
class TestTenantIsolationFix38:
    def test_delete_product_saleitem_has_company_id(self):
        """FIX 38a: SaleItem query must include company_id filter."""
        source = _read_source(f"{BASE}/inventory_state.py")
        # Find the SaleItem query block
        match = re.search(
            r"select\(SaleItem\).*?\.first\(\)",
            source,
            re.DOTALL,
        )
        assert match, "SaleItem query not found in inventory_state.py"
        query_block = match.group()
        assert "company_id" in query_block, (
            "SaleItem query in delete_product is missing company_id filter"
        )

    def test_category_deletion_has_company_id(self):
        """FIX 38b: Category deletion in delete_branch must filter by company_id."""
        source = _read_source(f"{BASE}/branches_state.py")
        # Find the Category select block near session.delete(cat)
        match = re.search(
            r"select\(Category\).*?\.all\(\)",
            source,
            re.DOTALL,
        )
        assert match, "Category query not found in branches_state.py"
        query_block = match.group()
        assert "company_id" in query_block, (
            "Category deletion in delete_branch is missing company_id filter"
        )

    def test_sale_detail_has_branch_id(self):
        """FIX 38c: Sale detail query must include branch_id."""
        source = _read_source(f"{BASE}/historial_state.py")
        # Look for the open_sale_detail query
        match = re.search(
            r"def open_sale_detail.*?\.first\(\)",
            source,
            re.DOTALL,
        )
        assert match, "open_sale_detail query not found"
        query_block = match.group()
        assert "branch_id" in query_block, (
            "Sale detail query in open_sale_detail is missing branch_id filter"
        )

    def test_cashbox_log_has_branch_id(self):
        """FIX 38d: CashboxLog query in _sale_log_payment_info must include branch_id."""
        source = _read_source(f"{BASE}/historial_state.py")
        match = re.search(
            r"def _sale_log_payment_info.*?\.all\(\)",
            source,
            re.DOTALL,
        )
        assert match, "_sale_log_payment_info query not found"
        query_block = match.group()
        assert "branch_id" in query_block, (
            "CashboxLog query is missing branch_id filter"
        )


# ---------------------------------------------------------------------------
# FIX 39: with_for_update on read-modify-write patterns
# ---------------------------------------------------------------------------
class TestConcurrencyFix39:
    def test_client_edit_uses_for_update(self):
        """FIX 39a: Client update must lock row before modifying credit fields."""
        source = _read_source(f"{BASE}/clientes_state.py")
        # Find the save_client method's SELECT query
        match = re.search(
            r"def save_client.*?session\.commit\(\)",
            source,
            re.DOTALL,
        )
        assert match, "save_client method not found"
        method_block = match.group()
        assert "with_for_update()" in method_block, (
            "Client SELECT in save_client is missing with_for_update()"
        )

    def test_product_edit_uses_for_update(self):
        """FIX 39b: Product update must lock row before modifying stock/price."""
        source = _read_source(f"{BASE}/inventory_state.py")
        # Find save_edited_product's product SELECT
        match = re.search(
            r"def save_edited_product.*?msg = .Producto actualizado",
            source,
            re.DOTALL,
        )
        assert match, "save_edited_product method not found"
        method_block = match.group()
        assert "with_for_update()" in method_block, (
            "Product SELECT in save_edited_product is missing with_for_update()"
        )


# ---------------------------------------------------------------------------
# FIX 40: Information leakage — no str(exc) in user-facing messages
# ---------------------------------------------------------------------------
class TestInfoLeakageFix40:
    def test_cuentas_pay_installment_no_str_exc(self):
        """FIX 40a: pay_installment must not expose str(exc) to user."""
        source = _read_source(f"{BASE}/cuentas_state.py")
        # Find the except block in pay_installment area
        match = re.search(
            r"except Exception as exc:.*?return",
            source,
            re.DOTALL,
        )
        assert match, "except block not found in cuentas_state"
        except_block = match.group()
        assert "str(exc)" not in except_block or "logger" in except_block, (
            "str(exc) should not appear in user-facing notification"
        )

    def test_report_error_no_str_e(self):
        """FIX 40b: report_error must not contain raw exception text."""
        source = _read_source(f"{BASE}/report_state.py")
        # Check that self.report_error = str(e) is not present
        assert "self.report_error = str(e)" not in source, (
            "report_state.py still exposes str(e) in report_error state var"
        )


# ---------------------------------------------------------------------------
# FIX 43: Field prices must reject negative values
# ---------------------------------------------------------------------------
class TestFieldPriceValidation:
    def test_add_field_price_rejects_negative(self):
        """FIX 43: add_field_price must validate price > 0."""
        source = _read_source(f"{BASE}/services_state.py")
        match = re.search(
            r"def add_field_price.*?session\.commit\(\)",
            source,
            re.DOTALL,
        )
        assert match, "add_field_price method not found"
        method_block = match.group()
        assert "price <= 0" in method_block or "price < 0" in method_block, (
            "add_field_price is missing negative price validation"
        )

    def test_update_field_price_rejects_negative(self):
        """FIX 43: update_field_price must validate price > 0."""
        source = _read_source(f"{BASE}/services_state.py")
        match = re.search(
            r"def update_field_price.*?session\.commit\(\)",
            source,
            re.DOTALL,
        )
        assert match, "update_field_price method not found"
        method_block = match.group()
        assert "price_val <= 0" in method_block or "price_val < 0" in method_block, (
            "update_field_price is missing negative price validation"
        )


# ---------------------------------------------------------------------------
# Logging: critical except blocks must have logger calls
# ---------------------------------------------------------------------------
class TestLoggingCoverage:
    @pytest.mark.parametrize(
        "file,marker",
        [
            ("ingreso_state.py", "confirm_entry failed"),
            ("inventory_state.py", "save_edited_product failed"),
            ("purchases_state.py", "save_purchase_edit failed"),
            ("purchases_state.py", "delete_purchase failed"),
            ("dashboard_state.py", "load_dashboard failed"),
            ("cuentas_state.py", "pay_installment failed"),
            ("clientes_state.py", "save_client failed"),
            ("clientes_state.py", "delete_client failed"),
        ],
    )
    def test_critical_except_has_logging(self, file, marker):
        """FIX 37: Critical except blocks must include logger.exception()."""
        source = _read_source(f"{BASE}/{file}")
        assert marker in source, (
            f"{file} is missing logger.exception with marker '{marker}'"
        )
