import io

import app.utils.exports as exports


def test_create_pdf_report_skips_internal_control_keys(monkeypatch):
    tables = []

    class FakeParagraph(str):
        def __new__(cls, text, style=None):
            return super().__new__(cls, text)

    class FakeDoc:
        def __init__(self, *args, **kwargs):
            self.width = 500

        def build(self, elements):
            self.elements = elements

    class FakeTable:
        def __init__(self, data, *args, **kwargs):
            self.data = data
            tables.append(data)

        def setStyle(self, style):
            self.style = style

    monkeypatch.setattr(exports, "SimpleDocTemplate", FakeDoc)
    monkeypatch.setattr(exports, "Table", FakeTable)
    monkeypatch.setattr(exports, "Paragraph", FakeParagraph)
    monkeypatch.setattr(exports, "Spacer", lambda *args, **kwargs: None)

    buffer = io.BytesIO()
    exports.create_pdf_report(
        buffer,
        "Reporte",
        [[1, "Venta"]],
        ["N°", "Detalle"],
        {
            "Fecha Cierre": "2026-03-07",
            "column_widths": [0.5, 0.5],
            "wrap_columns": [1],
        },
    )

    info_table = tables[0]
    rendered_text = " ".join(cell for row in info_table for cell in row)

    assert "Fecha Cierre" in rendered_text
    assert "Column Widths" not in rendered_text
    assert "Wrap Columns" not in rendered_text
