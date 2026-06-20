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
    "sent": "ENVIADO AL PROVEEDOR",
    "received": "RECIBIDO",
    "cancelled": "CANCELADO",
}

_NAVY         = colors.HexColor("#1e3a5f")   # header tablas
_GRAY_50      = colors.HexColor("#F9FAFB")   # fila alterna
_GRAY_200     = colors.HexColor("#E5E7EB")   # bordes
_GRAY_400     = colors.HexColor("#9CA3AF")   # texto muy secundario
_GRAY_500     = colors.HexColor("#6B7280")   # texto secundario
_GRAY_700     = colors.HexColor("#374151")   # texto medio
_GRAY_800     = colors.HexColor("#1F2937")   # texto principal
_WHITE        = colors.white

# Aliases de compatibilidad con el resto del código
_BRAND        = _NAVY
_BRAND_DARK   = _NAVY
_BRAND_LIGHT  = _GRAY_50
_SLATE_50     = _GRAY_50
_SLATE_100    = _GRAY_50
_SLATE_200    = _GRAY_200
_SLATE_400    = _GRAY_400
_SLATE_500    = _GRAY_500
_SLATE_700    = _GRAY_700
_SLATE_800    = _GRAY_800


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
    PAGE_W = A4[0]
    MARGIN = 15 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Orden de Compra #{po_info.get('id', '')}",
        author=company_info.get("name", "TUWAYKIAPP"),
    )

    styles = getSampleStyleSheet()

    def _s(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    # ── Estilos ──────────────────────────────────────────────────────────────
    s_company   = _s("company", fontSize=15, fontName="Helvetica-Bold",
                     textColor=_SLATE_800, spaceAfter=2, leading=18)
    s_ruc       = _s("ruc", fontSize=7.5, textColor=_SLATE_500, leading=12)
    s_po_label  = _s("po_label", fontSize=7.5, fontName="Helvetica-Bold",
                     textColor=_GRAY_500, alignment=TA_RIGHT, spaceAfter=1)
    s_po_num    = _s("po_num", fontSize=18, fontName="Helvetica-Bold",
                     textColor=_GRAY_800, alignment=TA_RIGHT, leading=20)
    s_po_meta   = _s("po_meta", fontSize=7.5, textColor=_GRAY_500,
                     alignment=TA_RIGHT, leading=12)
    s_section   = _s("section", fontSize=7, fontName="Helvetica-Bold",
                     textColor=_GRAY_700, spaceBefore=2, spaceAfter=2,
                     leftIndent=0)
    s_body      = _s("body", fontSize=8.5, textColor=_SLATE_800, leading=14)
    s_body_sm   = _s("body_sm", fontSize=7.5, textColor=_SLATE_500, leading=12)
    s_footer    = _s("footer", fontSize=6.5, textColor=_SLATE_400, alignment=TA_CENTER)
    s_th        = _s("th", fontSize=7.5, fontName="Helvetica-Bold",
                     textColor=_WHITE, alignment=TA_CENTER, leading=10)
    s_td        = _s("td", fontSize=8, textColor=_SLATE_800, leading=11)
    s_td_r      = _s("td_r", fontSize=8, textColor=_SLATE_800, alignment=TA_RIGHT, leading=11)
    s_td_c      = _s("td_c", fontSize=8, textColor=_SLATE_800, alignment=TA_CENTER, leading=11)
    s_td_bold_c = _s("td_bc", fontSize=8, fontName="Helvetica-Bold",
                     textColor=_SLATE_800, alignment=TA_CENTER, leading=11)
    s_td_bold_r = _s("td_br", fontSize=8, fontName="Helvetica-Bold",
                     textColor=_GRAY_800, alignment=TA_RIGHT, leading=11)
    s_total_lbl = _s("tot_l", fontSize=9, fontName="Helvetica-Bold",
                     textColor=_GRAY_500, alignment=TA_RIGHT)
    s_total_val = _s("tot_v", fontSize=16, fontName="Helvetica-Bold",
                     textColor=_GRAY_800, alignment=TA_RIGHT)
    s_sig_label = _s("sig_l", fontSize=7, textColor=_SLATE_400, alignment=TA_CENTER)
    s_sig_field = _s("sig_f", fontSize=7.5, textColor=_SLATE_700, alignment=TA_CENTER)
    s_bc_ref    = _s("bc_ref", fontSize=9, fontName="Helvetica-Bold",
                     textColor=_SLATE_700, alignment=TA_CENTER)
    s_bc_sub    = _s("bc_sub", fontSize=6.5, textColor=_SLATE_400, alignment=TA_CENTER)
    s_items_cnt = _s("items_cnt", fontSize=7.5, textColor=_SLATE_500, alignment=TA_RIGHT)

    # ── Datos ────────────────────────────────────────────────────────────────
    po_id       = po_info.get("id", 0)
    status_key  = po_info.get("status", "draft")
    status_lbl  = _STATUS_LABELS.get(status_key, status_key.upper())
    auto        = po_info.get("auto_generated", False)
    created_at  = po_info.get("created_at", "")
    currency    = (company_info.get("currency_symbol") or "$").strip()
    items       = po_info.get("items", [])
    n_items     = len(items)

    company_name = company_info.get("name", "")
    ruc          = company_info.get("ruc", "")
    address      = company_info.get("address", "") or ""
    phone_c      = company_info.get("phone", "") or ""
    branch       = company_info.get("branch_name", "") or ""

    story: List = []
    CONTENT_W = PAGE_W - 2 * MARGIN

    # ── CABECERA ─────────────────────────────────────────────────────────────
    phone_line  = f" · Tel: {phone_c}" if phone_c else ""
    branch_line = f"Sucursal: {branch}" if branch else ""
    ruc_line    = f"RUC: {ruc}{phone_line}" if ruc else phone_line.lstrip(" · ")

    # Franja de color lateral izquierda simulada con borde en tabla
    left_cell = [
        Paragraph(company_name, s_company),
        Paragraph(ruc_line, s_ruc),
    ]
    if address:
        left_cell.append(Paragraph(address, s_ruc))
    if branch_line:
        left_cell.append(Paragraph(branch_line, s_ruc))

    right_cell = [
        Paragraph("ORDEN DE COMPRA", s_po_label),
        Paragraph(f"#{po_id:04d}", s_po_num),
        Paragraph(
            f"Fecha: <b>{created_at}</b><br/>"
            f"Tipo: {'Auto-generada' if auto else 'Manual'}",
            s_po_meta,
        ),
    ]

    header_tbl = Table(
        [[left_cell, right_cell]],
        colWidths=[CONTENT_W * 0.58, CONTENT_W * 0.42],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (0, -1), 0),
        ("RIGHTPADDING",  (1, 0), (1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6))

    # ── BARRA DE ESTADO ───────────────────────────────────────────────────────
    status_tbl = Table(
        [[
            Paragraph(
                f"Estado: <b>{status_lbl}</b>",
                _s("sb", fontSize=8.5, textColor=_GRAY_700),
            ),
            Paragraph(
                f"PO-{po_id:06d}",
                _s("sb_r", fontSize=8.5, textColor=_GRAY_500, alignment=TA_RIGHT),
            ),
        ]],
        colWidths=[CONTENT_W * 0.7, CONTENT_W * 0.3],
    )
    status_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _GRAY_50),
        ("BOX",           (0, 0), (-1, -1), 0.5, _GRAY_200),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(status_tbl)
    story.append(Spacer(1, 10))

    # ── PROVEEDOR ────────────────────────────────────────────────────────────
    story.append(Paragraph("DATOS DEL PROVEEDOR", s_section))

    s = supplier_info
    sup_lines = [f"<b>{s.get('name', '-')}</b>"]
    if s.get("tax_id"):
        sup_lines[0] += f"  ·  RUC/Tax ID: {s['tax_id']}"
    detail_parts = []
    if s.get("email"):
        detail_parts.append(f"✉ {s['email']}")
    if s.get("phone"):
        detail_parts.append(f"✆ {s['phone']}")
    if detail_parts:
        sup_lines.append("  ·  ".join(detail_parts))
    if s.get("address"):
        sup_lines.append(f"📍 {s['address']}")

    sup_tbl = Table(
        [[Paragraph("<br/>".join(sup_lines), s_body)]],
        colWidths=[CONTENT_W],
    )
    sup_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _SLATE_50),
        ("BOX",           (0, 0), (-1, -1), 0.5, _SLATE_200),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(sup_tbl)
    story.append(Spacer(1, 10))

    # ── TABLA DE ÍTEMS ───────────────────────────────────────────────────────
    story.append(Paragraph("DETALLE DE PRODUCTOS A REPONER", s_section))

    col_w = [26*mm, 54*mm, 16*mm, 16*mm, 19*mm, 13*mm, 21*mm, 21*mm]
    headers = [
        "Código", "Producto",
        "Stock\nActual", "Stock\nMín.", "Cant.\nPedida", "Unid.",
        f"P. Unit.\n({currency})", f"Subtotal\n({currency})",
    ]
    table_data = [[Paragraph(h, s_th) for h in headers]]

    for i, it in enumerate(items):
        row_style = s_td
        table_data.append([
            Paragraph(str(it.get("barcode", "")), row_style),
            Paragraph(str(it.get("description", "")), row_style),
            Paragraph(str(int(it.get("current_stock", 0)) if float(it.get("current_stock", 0)) == int(float(it.get("current_stock", 0))) else it.get("current_stock", "")), s_td_c),
            Paragraph(str(int(it.get("min_stock_alert", 0)) if float(it.get("min_stock_alert", 0)) == int(float(it.get("min_stock_alert", 0))) else it.get("min_stock_alert", "")), s_td_c),
            Paragraph(f"<b>{int(it.get('suggested_quantity', 0)) if float(it.get('suggested_quantity', 0)) == int(float(it.get('suggested_quantity', 0))) else it.get('suggested_quantity', '')}</b>", s_td_bold_c),
            Paragraph(str(it.get("unit", "")), s_td_c),
            Paragraph(str(it.get("unit_cost", "")), s_td_r),
            Paragraph(f"<b>{it.get('subtotal', '')}</b>", s_td_bold_r),
        ])

    items_tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    row_bgs = [("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _SLATE_50])]
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _BRAND),
        ("TEXTCOLOR",     (0, 0), (-1, 0), _WHITE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0), (-1, -1), 0.3, _SLATE_200),
        ("LINEBELOW",     (0, 0), (-1, 0), 0, _BRAND),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        *row_bgs,
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 6))

    # ── NOTAS ────────────────────────────────────────────────────────────────
    notes = po_info.get("notes", "")
    if notes:
        story.append(Paragraph("NOTAS", s_section))
        notes_tbl = Table(
            [[Paragraph(notes, s_body)]],
            colWidths=[CONTENT_W],
        )
        notes_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), _SLATE_50),
            ("LINEBEFORE",    (0, 0), (0, -1), 3, _SLATE_400),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(notes_tbl)
        story.append(Spacer(1, 6))

    # ── TOTAL + CONTEO ───────────────────────────────────────────────────────
    total_str  = po_info.get("total_amount_str", "0.00")
    items_text = f"{n_items} producto{'s' if n_items != 1 else ''}"

    total_tbl = Table(
        [
            [
                Paragraph(f"{items_text} en esta orden", s_items_cnt),
                Paragraph("TOTAL ESTIMADO", s_total_lbl),
            ],
            [
                "",
                Paragraph(f"{currency} {total_str}", s_total_val),
            ],
        ],
        colWidths=[CONTENT_W * 0.55, CONTENT_W * 0.45],
    )
    total_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (1, 0), (1, -1), _GRAY_50),
        ("BOX",           (1, 0), (1, -1), 0.5, _GRAY_200),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (1, 0), (1, -1), 12),
        ("LEFTPADDING",   (1, 0), (1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("VALIGN",        (0, 0), (0, -1), "BOTTOM"),
    ]))
    story.append(total_tbl)
    story.append(Spacer(1, 16))

    # ── CÓDIGO DE BARRAS (centrado) ──────────────────────────────────────────
    try:
        bc_value = f"PO-{po_id:06d}"
        bc = code128.Code128(bc_value, barHeight=12 * mm, barWidth=0.8, quiet=True)
        bc_w = bc.width

        bc_tbl = Table(
            [[
                "",
                [
                    bc,
                    Spacer(1, 2),
                    Paragraph(bc_value, s_bc_ref),
                    Paragraph("Referencia interna de orden", s_bc_sub),
                ],
                "",
            ]],
            colWidths=[(CONTENT_W - bc_w) / 2, bc_w, (CONTENT_W - bc_w) / 2],
        )
        bc_tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (1, 0), (1, 0), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(bc_tbl)
        story.append(Spacer(1, 16))
    except Exception:
        pass

    # ── FIRMAS ───────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.4, color=_SLATE_200, spaceAfter=0))
    story.append(Spacer(1, 10))

    sig_line = HRFlowable(width="75%", thickness=0.8, color=_SLATE_400)

    def _sig_block(title, fields):
        """Construye un bloque de firma con línea y campos."""
        rows = [[sig_line]]
        rows.append([Paragraph(f"<b>{title}</b>", _s("st", fontSize=8,
                                fontName="Helvetica-Bold", textColor=_SLATE_700,
                                alignment=TA_CENTER))])
        for label in fields:
            rows.append([Paragraph(label, s_sig_label)])
        return Table(rows, colWidths=["100%"])

    sig_l = _sig_block("Solicitante", ["Nombre: ___________________________",
                                        "Cargo:   ___________________________",
                                        "Fecha:   ___________________________"])
    sig_r = _sig_block("Autorización", ["Nombre: ___________________________",
                                         "Cargo:   ___________________________",
                                         "Fecha:   ___________________________"])

    sigs_tbl = Table([[sig_l, "", sig_r]], colWidths=["46%", "8%", "46%"])
    sigs_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(sigs_tbl)
    story.append(Spacer(1, 12))

    # ── PIE DE PÁGINA ────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.4, color=_SLATE_200, spaceAfter=5))
    user_name = po_info.get("user_name", "Sistema")
    now_str   = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(
        f"Generado por: <b>{user_name}</b>  ·  {now_str}  ·  TUWAYKIAPP  ·  Documento interno — No válido como comprobante fiscal",
        s_footer,
    ))

    doc.build(story)
    return buffer.getvalue()
