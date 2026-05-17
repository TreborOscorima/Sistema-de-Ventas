"""Generación de PDF para Órdenes de Compra.

Usa reportlab (incluido en requirements.txt). Devuelve bytes descargables.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List

from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_STATUS_LABELS = {
    "draft": "BORRADOR",
    "sent": "ENVIADA AL PROVEEDOR",
    "received": "RECIBIDA",
    "cancelled": "CANCELADA",
}

_STATUS_COLORS = {
    "draft": colors.HexColor("#f59e0b"),
    "sent": colors.HexColor("#3b82f6"),
    "received": colors.HexColor("#10b981"),
    "cancelled": colors.HexColor("#ef4444"),
}

_BRAND = colors.HexColor("#6366f1")
_BRAND_LIGHT = colors.HexColor("#eef2ff")
_SLATE_100 = colors.HexColor("#f1f5f9")
_SLATE_200 = colors.HexColor("#e2e8f0")
_SLATE_500 = colors.HexColor("#64748b")
_SLATE_800 = colors.HexColor("#1e293b")


def generate_po_pdf(
    company_info: Dict[str, Any],
    supplier_info: Dict[str, Any],
    po_info: Dict[str, Any],
) -> bytes:
    """Genera el PDF de una Orden de Compra y devuelve bytes.

    Args:
        company_info: {name, ruc, address, phone, branch_name, currency_symbol}
        supplier_info: {name, tax_id, email, phone, address}
        po_info: {id, status, created_at, notes, auto_generated, total_amount_str,
                  items: [{barcode, description, current_stock, min_stock_alert,
                           suggested_quantity, unit, unit_cost, subtotal}],
                  user_name}
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Orden de Compra #{po_info.get('id', '')}",
        author=company_info.get("name", "TUWAYKIAPP"),
    )

    styles = getSampleStyleSheet()

    def _style(name, **kwargs):
        return ParagraphStyle(name, parent=styles["Normal"], **kwargs)

    s_company = _style("company", fontSize=16, fontName="Helvetica-Bold",
                        textColor=_SLATE_800, spaceAfter=1)
    s_ruc = _style("ruc", fontSize=8, textColor=_SLATE_500, spaceAfter=1)
    s_po_title = _style("po_title", fontSize=14, fontName="Helvetica-Bold",
                         textColor=_BRAND, alignment=TA_RIGHT)
    s_po_meta = _style("po_meta", fontSize=8, textColor=_SLATE_500,
                        alignment=TA_RIGHT, leading=13)
    s_section = _style("section", fontSize=7.5, fontName="Helvetica-Bold",
                        textColor=_SLATE_500, spaceBefore=4, spaceAfter=3)
    s_body = _style("body", fontSize=9, textColor=_SLATE_800, leading=13)
    s_footer = _style("footer", fontSize=7, textColor=_SLATE_500, alignment=TA_CENTER)
    s_th = _style("th", fontSize=7.5, fontName="Helvetica-Bold",
                   textColor=colors.white, alignment=TA_CENTER)
    s_td = _style("td", fontSize=8, textColor=_SLATE_800)
    s_td_r = _style("td_r", fontSize=8, textColor=_SLATE_800, alignment=TA_RIGHT)
    s_td_c = _style("td_c", fontSize=8, textColor=_SLATE_800, alignment=TA_CENTER)
    s_total_label = _style("tot_l", fontSize=10, fontName="Helvetica-Bold",
                            textColor=_SLATE_800, alignment=TA_RIGHT)
    s_total_val = _style("tot_v", fontSize=14, fontName="Helvetica-Bold",
                          textColor=_BRAND, alignment=TA_RIGHT)
    s_sig = _style("sig", fontSize=8, textColor=_SLATE_500, alignment=TA_CENTER)

    po_id = po_info.get("id", 0)
    status_key = po_info.get("status", "draft")
    status_label = _STATUS_LABELS.get(status_key, status_key.upper())
    status_color = _STATUS_COLORS.get(status_key, colors.grey)
    auto = po_info.get("auto_generated", False)
    created_at = po_info.get("created_at", "")
    currency = (company_info.get("currency_symbol") or "$").strip()

    company_name = company_info.get("name", "")
    ruc = company_info.get("ruc", "")
    address = company_info.get("address", "")
    phone_c = company_info.get("phone", "") or ""
    branch = company_info.get("branch_name", "") or ""

    story: List = []

    # ── Cabecera ─────────────────────────────────────────────────────────────
    branch_line = f"<br/>Sucursal: {branch}" if branch else ""
    phone_line = f" · Tel: {phone_c}" if phone_c else ""
    left_content = [
        Paragraph(company_name, s_company),
        Paragraph(f"RUC: {ruc}{phone_line}<br/>{address}{branch_line}", s_ruc),
    ]
    right_content = [
        Paragraph(f"ORDEN DE COMPRA <b>#{po_id}</b>", s_po_title),
        Paragraph(
            f"Fecha: {created_at}<br/>"
            f"Tipo: {'Auto-generada' if auto else 'Manual'}",
            s_po_meta,
        ),
    ]
    header_tbl = Table(
        [[left_content, right_content]],
        colWidths=["58%", "42%"],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_tbl)

    # Status bar below header
    status_tbl = Table(
        [[Paragraph(f"  {status_label}  ", _style("sb", fontSize=8,
                                                    fontName="Helvetica-Bold",
                                                    textColor=colors.white))]],
        colWidths=[60 * mm],
    )
    status_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), status_color),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("TOPPADDING", (0, 0), (0, 0), 3),
        ("BOTTOMPADDING", (0, 0), (0, 0), 3),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(Spacer(1, 4))
    story.append(status_tbl)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND, spaceAfter=8))

    # ── Proveedor ────────────────────────────────────────────────────────────
    story.append(Paragraph("DATOS DEL PROVEEDOR", s_section))
    s = supplier_info
    lines = [f"<b>{s.get('name', '-')}</b>  ·  RUC/Tax ID: {s.get('tax_id', '-')}"]
    if s.get("email"):
        lines.append(f"Email: {s['email']}")
    if s.get("phone"):
        lines.append(f"Teléfono: {s['phone']}")
    if s.get("address"):
        lines.append(f"Dirección: {s['address']}")
    story.append(Paragraph("<br/>".join(lines), s_body))
    story.append(Spacer(1, 8))

    # ── Tabla de ítems ───────────────────────────────────────────────────────
    story.append(Paragraph("DETALLE DE PRODUCTOS A REPONER", s_section))

    col_w = [25 * mm, 52 * mm, 17 * mm, 17 * mm, 20 * mm, 14 * mm, 22 * mm, 22 * mm]
    headers = [
        "Código", "Producto",
        "Stock\nActual", "Stock\nMínimo", "Cant.\nPedida", "Unid.",
        f"Costo\nUnit. ({currency})", f"Subtotal\n({currency})",
    ]
    table_data = [[Paragraph(h, s_th) for h in headers]]

    items = po_info.get("items", [])
    for it in items:
        table_data.append([
            Paragraph(str(it.get("barcode", "")), s_td),
            Paragraph(str(it.get("description", "")), s_td),
            Paragraph(str(it.get("current_stock", "")), s_td_c),
            Paragraph(str(it.get("min_stock_alert", "")), s_td_c),
            Paragraph(f"<b>{it.get('suggested_quantity', '')}</b>", s_td_c),
            Paragraph(str(it.get("unit", "")), s_td_c),
            Paragraph(str(it.get("unit_cost", "")), s_td_r),
            Paragraph(f"<b>{it.get('subtotal', '')}</b>", s_td_r),
        ])

    items_tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    row_backgrounds = [
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _SLATE_100]),
    ]
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, _SLATE_200),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        *row_backgrounds,
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 8))

    # ── Notas ────────────────────────────────────────────────────────────────
    notes = po_info.get("notes", "")
    if notes:
        story.append(Paragraph("NOTAS", s_section))
        story.append(Paragraph(notes, s_body))
        story.append(Spacer(1, 8))

    # ── Total ────────────────────────────────────────────────────────────────
    total_str = po_info.get("total_amount_str", "0.00")
    total_tbl = Table(
        [
            ["", Paragraph("TOTAL ESTIMADO:", s_total_label)],
            ["", Paragraph(f"{currency} {total_str}", s_total_val)],
        ],
        colWidths=["62%", "38%"],
    )
    total_tbl.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, -1), _BRAND_LIGHT),
        ("BOX", (1, 0), (1, -1), 1, _BRAND),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (1, 0), (1, -1), 10),
        ("LEFTPADDING", (1, 0), (1, -1), 6),
    ]))
    story.append(total_tbl)
    story.append(Spacer(1, 14))

    # ── Código de barras (Code128 del ID de PO) ──────────────────────────────
    try:
        bc_value = f"PO-{po_id:06d}"
        bc = code128.Code128(bc_value, barHeight=14 * mm, barWidth=0.75, quiet=True)
        bc_tbl = Table(
            [[bc, Paragraph(
                f"<b>{bc_value}</b>",
                _style("bcl", fontSize=8, textColor=_SLATE_500, alignment=TA_CENTER),
            )]],
            colWidths=[bc.width + 6, "*"],
        )
        bc_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(bc_tbl)
        story.append(Spacer(1, 12))
    except Exception:
        pass

    # ── Líneas de firma ──────────────────────────────────────────────────────
    line = "_" * 32
    sig_tbl = Table(
        [
            [Paragraph(line, s_sig), Paragraph(line, s_sig)],
            [Paragraph("Solicitante", s_sig), Paragraph("Autorización", s_sig)],
        ],
        colWidths=["50%", "50%"],
    )
    sig_tbl.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(sig_tbl)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_SLATE_200, spaceAfter=4))

    # ── Pie de página ────────────────────────────────────────────────────────
    user_name = po_info.get("user_name", "Sistema")
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(
        f"Generado por: {user_name}  ·  {now_str}  ·  TUWAYKIAPP — Documento interno",
        s_footer,
    ))

    doc.build(story)
    return buffer.getvalue()
