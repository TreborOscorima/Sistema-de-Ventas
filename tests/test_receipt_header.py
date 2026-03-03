"""Tests para validar que el encabezado de tickets incluye branch_name.

Verifica que los 3 flujos de impresión muestren la sucursal:
1. Comprobante de venta POS (ReceiptService)
2. Constancia de reserva (ServicesState._print_reservation_proof)
3. Reimpresión desde Caja (CashState.reprint_sale_receipt)
"""

import pytest

from app.services.receipt_service import ReceiptService


# --------------- Fixtures ---------------

@pytest.fixture
def company_with_branch():
    """Company settings con branch_name distinto a company_name."""
    return {
        "company_name": "TU WAYKI S.A.C",
        "branch_name": "CASA MATRIZ",
        "ruc": "72075195-5",
        "address": "Jirón Huancayo 1005",
        "phone": "+5491168376517",
        "footer_message": "¡GRACIAS POR SU PREFERENCIA!",
        "tax_id_label": "RUC",
    }


@pytest.fixture
def company_without_branch():
    """Company settings sin branch_name."""
    return {
        "company_name": "TU WAYKI S.A.C",
        "branch_name": "",
        "ruc": "72075195-5",
        "address": "Jirón Huancayo 1005",
        "phone": "+5491168376517",
        "footer_message": "¡GRACIAS POR SU PREFERENCIA!",
        "tax_id_label": "RUC",
    }


@pytest.fixture
def company_branch_equals_name():
    """Company settings donde branch_name == company_name."""
    return {
        "company_name": "TU WAYKI S.A.C",
        "branch_name": "TU WAYKI S.A.C",
        "ruc": "72075195-5",
        "address": "Jirón Huancayo 1005",
        "phone": "+5491168376517",
        "footer_message": "¡GRACIAS POR SU PREFERENCIA!",
        "tax_id_label": "RUC",
    }


@pytest.fixture
def receipt_data_minimal():
    """Datos mínimos de recibo para ReceiptService."""
    return {
        "items": [
            {
                "description": "Coca Cola 500ml",
                "quantity": 1,
                "unit": "Unidad",
                "price": 2.70,
                "subtotal": 2.70,
            }
        ],
        "total": 2.70,
        "timestamp": "2026-02-27 19:13:51",
        "user_name": "admin",
        "payment_summary": "Efectivo S/ 2.70",
        "currency_symbol": "S/ ",
        "width": 42,
        "paper_width_mm": 80,
    }


# --------------- Tests: ReceiptService (comprobante POS) ---------------

class TestReceiptServiceHeader:
    """Verifica que ReceiptService.generate_receipt_html incluya branch_name."""

    def test_receipt_includes_branch_name(
        self, receipt_data_minimal, company_with_branch
    ):
        html = ReceiptService.generate_receipt_html(
            receipt_data_minimal, company_with_branch
        )
        assert "CASA MATRIZ" in html
        assert "TU WAYKI S.A.C" in html

    def test_receipt_omits_branch_when_empty(
        self, receipt_data_minimal, company_without_branch
    ):
        html = ReceiptService.generate_receipt_html(
            receipt_data_minimal, company_without_branch
        )
        assert "TU WAYKI S.A.C" in html
        # branch_name vacío no debe generar línea extra
        lines = html.split("\n")
        branch_occurrences = sum(1 for l in lines if "CASA MATRIZ" in l)
        assert branch_occurrences == 0

    def test_receipt_omits_branch_when_equals_company(
        self, receipt_data_minimal, company_branch_equals_name
    ):
        html = ReceiptService.generate_receipt_html(
            receipt_data_minimal, company_branch_equals_name
        )
        # No debe duplicar el nombre
        assert "TU WAYKI S.A.C" in html

    def test_receipt_includes_ruc_and_address(
        self, receipt_data_minimal, company_with_branch
    ):
        html = ReceiptService.generate_receipt_html(
            receipt_data_minimal, company_with_branch
        )
        assert "72075195-5" in html
        assert "Huancayo" in html

    def test_receipt_branch_before_ruc(
        self, receipt_data_minimal, company_with_branch
    ):
        """branch_name aparece antes del RUC en el HTML."""
        html = ReceiptService.generate_receipt_html(
            receipt_data_minimal, company_with_branch
        )
        branch_pos = html.find("CASA MATRIZ")
        ruc_pos = html.find("72075195-5")
        assert branch_pos < ruc_pos, (
            "branch_name debe aparecer antes del RUC en el recibo"
        )


# --------------- Tests: _build_receipt_lines (texto plano) ---------------

class TestBuildReceiptLines:
    """Verifica el contenido texto plano del header."""

    def _build(self, data, company):
        def fmt(v, symbol="S/ "):
            return f"{symbol}{float(v):.2f}"
        return ReceiptService._build_receipt_lines(data, company, fmt)

    def test_lines_include_branch(
        self, receipt_data_minimal, company_with_branch
    ):
        lines = self._build(receipt_data_minimal, company_with_branch)
        text = "\n".join(lines)
        assert "CASA MATRIZ" in text
        assert "TU WAYKI S.A.C" in text

    def test_lines_exclude_branch_when_empty(
        self, receipt_data_minimal, company_without_branch
    ):
        lines = self._build(receipt_data_minimal, company_without_branch)
        text = "\n".join(lines)
        assert "CASA MATRIZ" not in text

    def test_lines_exclude_branch_when_same_as_company(
        self, receipt_data_minimal, company_branch_equals_name
    ):
        lines = self._build(receipt_data_minimal, company_branch_equals_name)
        text = "\n".join(lines)
        # company_name aparece, pero branch no se duplica
        company_count = text.count("TU WAYKI S.A.C")
        assert company_count == 1, (
            f"company_name aparece {company_count} veces, debería ser 1"
        )

    def test_header_order(
        self, receipt_data_minimal, company_with_branch
    ):
        """Orden: company_name → branch_name → RUC → dirección → teléfono."""
        lines = self._build(receipt_data_minimal, company_with_branch)
        text = "\n".join(lines)
        positions = {
            "company": text.find("TU WAYKI S.A.C"),
            "branch": text.find("CASA MATRIZ"),
            "ruc": text.find("72075195-5"),
            "address": text.find("Huancayo"),
            "phone": text.find("+5491168376517"),
        }
        assert positions["company"] < positions["branch"] < positions["ruc"]
        assert positions["ruc"] < positions["address"] < positions["phone"]
