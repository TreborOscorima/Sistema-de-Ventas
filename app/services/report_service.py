"""
Servicio de Reportes Contables y Financieros.

Genera reportes profesionales para evaluaciones administrativas,
contables y financieras con el nivel de detalle requerido.
"""
import io
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any

import openpyxl
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.chart import PieChart, BarChart, Reference

from sqlmodel import select, func
from sqlalchemy import and_, or_
from sqlalchemy.orm import selectinload

from app.models import Sale, SaleItem, Product, Client, SaleInstallment, CashboxLog, SalePayment
from app.enums import SaleStatus, PaymentMethodType


# =============================================================================
# ESTILOS PROFESIONALES PARA REPORTES (Unificados con exports.py)
# =============================================================================

# Colores consistentes con el sistema - Púrpura/Índigo corporativo
TITLE_FONT = Font(bold=True, size=16, color="4F46E5")
SUBTITLE_FONT = Font(bold=True, size=12, color="6366F1")
HEADER_FONT = Font(bold=True, size=10, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
SUBHEADER_FILL = PatternFill(start_color="C7D2FE", end_color="C7D2FE", fill_type="solid")
TOTAL_FILL = PatternFill(start_color="EEF2FF", end_color="EEF2FF", fill_type="solid")
POSITIVE_FILL = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
NEGATIVE_FILL = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
WARNING_FILL = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
CURRENCY_FORMAT = '"S/"#,##0.00'
PERCENT_FORMAT = '0.00%'
DATE_FORMAT = 'DD/MM/YYYY'
DATETIME_FORMAT = 'DD/MM/YYYY HH:MM:SS'

THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

THICK_BORDER_BOTTOM = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="medium"),
)


def _round_currency(value: float | Decimal) -> Decimal:
    """Redondea a 2 decimales para moneda."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_currency(value: float | Decimal) -> str:
    """Formatea valor como moneda."""
    return f"S/ {_round_currency(value):,.2f}"


def _add_company_header(ws: Worksheet, company_name: str, report_title: str, period: str, columns: int = 8) -> int:
    """
    Agrega encabezado de empresa profesional al reporte.
    
    Args:
        ws: Hoja de trabajo
        company_name: Nombre de la empresa
        report_title: Título del reporte
        period: Período del reporte
        columns: Número de columnas para el merge (default 8)
    
    Retorna la fila siguiente disponible.
    """
    end_col = get_column_letter(columns)
    
    # Fila 1: Logo / Nombre empresa con fondo
    ws.merge_cells(f"A1:{end_col}1")
    ws["A1"] = company_name.upper()
    ws["A1"].font = Font(bold=True, size=18, color="FFFFFF")
    ws["A1"].fill = HEADER_FILL
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30
    
    # Fila 2: Título del reporte
    ws.merge_cells(f"A2:{end_col}2")
    ws["A2"] = report_title
    ws["A2"].font = SUBTITLE_FONT
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 25
    
    # Fila 3: Período
    ws.merge_cells(f"A3:{end_col}3")
    ws["A3"] = f"📅 Período: {period}"
    ws["A3"].font = Font(size=11, color="374151")
    ws["A3"].alignment = Alignment(horizontal="center")
    
    # Fila 4: Fecha de generación
    ws.merge_cells(f"A4:{end_col}4")
    ws["A4"] = f"🕐 Generado: {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}"
    ws["A4"].font = Font(italic=True, size=9, color="6B7280")
    ws["A4"].alignment = Alignment(horizontal="center")
    
    # Línea separadora visual (fila 5 vacía con borde inferior)
    ws.merge_cells(f"A5:{end_col}5")
    ws["A5"].border = Border(bottom=Side(style="medium", color="4F46E5"))
    
    return 7  # Siguiente fila disponible (dejamos una fila de espacio)


def _style_header_row(ws: Worksheet, row: int, columns: list[str]) -> None:
    """Aplica estilo a fila de encabezados."""
    for col_idx, header in enumerate(columns, start=1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER


def _add_totals_row(ws: Worksheet, row: int, data: list[Any], label_col: int = 1) -> None:
    """Agrega fila de totales con estilo."""
    for col_idx, value in enumerate(data, start=1):
        cell = ws.cell(row=row, column=col_idx, value=value)
        cell.font = Font(bold=True)
        cell.fill = TOTAL_FILL
        cell.border = THICK_BORDER_BOTTOM


def _add_totals_row_with_formulas(
    ws: Worksheet, 
    row: int, 
    start_data_row: int,
    columns_config: list[dict],
) -> None:
    """
    Agrega fila de totales usando fórmulas de Excel para verificabilidad.
    
    Args:
        ws: Hoja de trabajo
        row: Fila donde agregar los totales
        start_data_row: Primera fila de datos
        columns_config: Lista de diccionarios con configuración por columna:
            - type: 'label' | 'sum' | 'count' | 'average' | 'formula' | 'text'
            - value: Valor para 'label', 'text' o fórmula personalizada
            - col_letter: Letra de columna para fórmulas
    """
    for col_idx, config in enumerate(columns_config, start=1):
        cell = ws.cell(row=row, column=col_idx)
        col_type = config.get("type", "text")
        
        if col_type == "label":
            cell.value = config.get("value", "TOTAL")
        elif col_type == "sum":
            col_letter = config.get("col_letter", get_column_letter(col_idx))
            cell.value = f"=SUM({col_letter}{start_data_row}:{col_letter}{row-1})"
        elif col_type == "count":
            col_letter = config.get("col_letter", get_column_letter(col_idx))
            cell.value = f"=COUNT({col_letter}{start_data_row}:{col_letter}{row-1})"
        elif col_type == "average":
            col_letter = config.get("col_letter", get_column_letter(col_idx))
            cell.value = f"=AVERAGE({col_letter}{start_data_row}:{col_letter}{row-1})"
        elif col_type == "formula":
            cell.value = config.get("value", "")
        elif col_type == "text":
            cell.value = config.get("value", "")
        
        cell.font = Font(bold=True)
        cell.fill = TOTAL_FILL
        cell.border = THICK_BORDER_BOTTOM
        
        # Aplicar formato numérico si se especifica
        if config.get("number_format"):
            cell.number_format = config["number_format"]


def _add_notes_section(ws: Worksheet, row: int, notes: list[str], columns: int = 8) -> int:
    """
    Agrega una sección de notas explicativas al final de la hoja.
    
    Args:
        ws: Hoja de trabajo
        row: Fila inicial
        notes: Lista de notas a agregar
        columns: Número de columnas para el merge
    
    Returns:
        Siguiente fila disponible
    """
    row += 2  # Espacio
    end_col = get_column_letter(columns)
    
    ws.merge_cells(f"A{row}:{end_col}{row}")
    ws[f"A{row}"] = "📋 NOTAS Y DEFINICIONES:"
    ws[f"A{row}"].font = Font(bold=True, size=10, color="374151")
    row += 1
    
    for note in notes:
        ws.merge_cells(f"A{row}:{end_col}{row}")
        ws[f"A{row}"] = f"• {note}"
        ws[f"A{row}"].font = Font(size=9, color="6B7280")
        ws[f"A{row}"].alignment = Alignment(wrap_text=True)
        row += 1
    
    return row


def _safe_decimal(value: Any) -> Decimal:
    """Convierte un valor a Decimal de forma segura, evitando corrupción de datos."""
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal("0")


def _safe_int(value: Any) -> int:
    """Convierte un valor a int de forma segura."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _safe_string(value: Any, default: str = "") -> str:
    """Convierte un valor a string de forma segura."""
    if value is None:
        return default
    try:
        return str(value).strip()
    except:
        return default


def _translate_payment_method(method: str) -> str:
    """
    Traduce códigos de método de pago a español legible.
    
    Args:
        method: Código o nombre del método de pago
    
    Returns:
        Nombre en español del método de pago
    """
    translations = {
        # Códigos comunes
        "cash": "Efectivo",
        "efectivo": "Efectivo",
        "card": "Tarjeta",
        "tarjeta": "Tarjeta",
        "credit_card": "Tarjeta de Crédito",
        "debit_card": "Tarjeta de Débito",
        "transfer": "Transferencia Bancaria",
        "transferencia": "Transferencia Bancaria",
        "bank_transfer": "Transferencia Bancaria",
        "yape": "Yape",
        "plin": "Plin",
        "wallet": "Billetera Digital",
        "credit": "Crédito/Fiado",
        "credito": "Crédito/Fiado",
        "check": "Cheque",
        "cheque": "Cheque",
        "mixed": "Pago Mixto",
        "mixto": "Pago Mixto",
        "other": "Otro",
        "otro": "Otro",
        "no especificado": "No Especificado",
        "": "No Especificado",
    }
    
    method_lower = method.lower().strip()
    return translations.get(method_lower, method.capitalize())


def _translate_sale_status(status: str) -> str:
    """
    Traduce estados de venta a español legible.
    
    Args:
        status: Código del estado
    
    Returns:
        Estado en español
    """
    translations = {
        "completed": "Completada",
        "pending": "Pendiente",
        "cancelled": "Anulada",
        "voided": "Anulada",
        "partial": "Parcial",
        "credit": "A Crédito",
        "paid": "Pagada",
    }
    
    return translations.get(status.lower().strip(), status.capitalize())


def _auto_adjust_columns(ws: Worksheet, min_width: int = 12, max_width: int = 50) -> None:
    """Ajusta automáticamente el ancho de columnas."""
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = min(max(max_length + 2, min_width), max_width)
        ws.column_dimensions[column_letter].width = adjusted_width


# =============================================================================
# REPORTE DE VENTAS CONSOLIDADO
# =============================================================================

def generate_sales_report(
    session,
    start_date: datetime,
    end_date: datetime,
    company_name: str = "TUWAYKIAPP",
    include_cancelled: bool = False,
) -> io.BytesIO:
    """
    Genera reporte de ventas consolidado con detalles contables.
    
    Incluye:
    - Resumen ejecutivo
    - Detalle de ventas por día
    - Desglose por categoría
    - Desglose por método de pago
    - Análisis de utilidad bruta
    - Listado detallado de transacciones
    """
    wb = Workbook()
    
    # Consultar ventas del período
    query = (
        select(Sale)
        .where(
            and_(
                Sale.timestamp >= start_date,
                Sale.timestamp <= end_date,
            )
        )
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.payments),
            selectinload(Sale.user),
            selectinload(Sale.client),
        )
        .order_by(Sale.timestamp.desc())
    )
    
    if not include_cancelled:
        query = query.where(Sale.status != SaleStatus.cancelled)
    
    sales = session.exec(query).all()
    
    period_str = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
    
    # =================
    # HOJA 1: RESUMEN EJECUTIVO
    # =================
    ws_summary = wb.active
    ws_summary.title = "Resumen Ejecutivo"
    
    row = _add_company_header(ws_summary, company_name, "REPORTE DE VENTAS CONSOLIDADO", period_str)
    
    # Calcular métricas
    total_ventas = Decimal("0")
    total_costo = Decimal("0")
    total_descuentos = Decimal("0")
    ventas_count = 0
    ventas_credito = 0
    ventas_contado = 0
    monto_credito = Decimal("0")
    monto_contado = Decimal("0")
    
    by_category: dict[str, dict] = {}
    by_payment: dict[str, dict] = {}
    by_day: dict[str, dict] = {}
    by_user: dict[str, dict] = {}
    
    for sale in sales:
        if sale.status == SaleStatus.cancelled:
            continue
            
        ventas_count += 1
        sale_total = Decimal(str(sale.total_amount or 0))
        total_ventas += sale_total
        
        # Clasificar por tipo
        is_credit = (
            bool(getattr(sale, "is_credit", False)) or
            (sale.payment_condition or "").lower() in {"credito", "credit"}
        )
        
        if is_credit:
            ventas_credito += 1
            monto_credito += sale_total
        else:
            ventas_contado += 1
            monto_contado += sale_total
        
        # Por día
        day_key = sale.timestamp.strftime("%Y-%m-%d") if sale.timestamp else "Sin fecha"
        if day_key not in by_day:
            by_day[day_key] = {"count": 0, "total": Decimal("0"), "cost": Decimal("0")}
        by_day[day_key]["count"] += 1
        by_day[day_key]["total"] += sale_total
        
        # Por usuario
        user_name = sale.user.username if sale.user else "Desconocido"
        if user_name not in by_user:
            by_user[user_name] = {"count": 0, "total": Decimal("0")}
        by_user[user_name]["count"] += 1
        by_user[user_name]["total"] += sale_total
        
        # Por categoría y calcular costo
        for item in (sale.items or []):
            item_total = Decimal(str(item.subtotal or 0))
            # Obtener costo del producto relacionado
            cost_price = Decimal(str(item.product.purchase_price or 0)) if item.product else Decimal("0")
            item_cost = cost_price * Decimal(str(item.quantity or 0))
            total_costo += item_cost
            
            category = item.product_category_snapshot or "Sin categoría"
            if category not in by_category:
                by_category[category] = {"count": 0, "total": Decimal("0"), "cost": Decimal("0"), "qty": 0}
            by_category[category]["count"] += 1
            by_category[category]["total"] += item_total
            by_category[category]["cost"] += item_cost
            by_category[category]["qty"] += int(item.quantity or 0)
        
        # Por método de pago
        for payment in (sale.payments or []):
            method = payment.method_type.value if payment.method_type else "No especificado"
            amount = Decimal(str(payment.amount or 0))
            if method not in by_payment:
                by_payment[method] = {"count": 0, "total": Decimal("0")}
            by_payment[method]["count"] += 1
            by_payment[method]["total"] += amount
    
    utilidad_bruta = total_ventas - total_costo
    margen_bruto = (utilidad_bruta / total_ventas * 100) if total_ventas > 0 else Decimal("0")
    ticket_promedio = (total_ventas / ventas_count) if ventas_count > 0 else Decimal("0")
    
    # Escribir resumen
    row += 1
    ws_summary.cell(row=row, column=1, value="INDICADORES PRINCIPALES").font = SUBTITLE_FONT
    row += 1
    
    indicators = [
        ("Total Ventas Brutas:", _format_currency(total_ventas)),
        ("(-) Costo de Ventas:", _format_currency(total_costo)),
        ("(=) Utilidad Bruta:", _format_currency(utilidad_bruta)),
        ("Margen Bruto:", f"{margen_bruto:.2f}%"),
        ("", ""),
        ("Número de Transacciones:", ventas_count),
        ("Ticket Promedio:", _format_currency(ticket_promedio)),
        ("", ""),
        ("Ventas al Contado:", f"{ventas_contado} ({_format_currency(monto_contado)})"),
        ("Ventas a Crédito:", f"{ventas_credito} ({_format_currency(monto_credito)})"),
    ]
    
    for label, value in indicators:
        ws_summary.cell(row=row, column=1, value=label).font = Font(bold=True)
        ws_summary.cell(row=row, column=2, value=value)
        row += 1
    
    # =================
    # HOJA 2: VENTAS POR DÍA (con fórmulas de Excel)
    # =================
    ws_daily = wb.create_sheet("Ventas por Día")
    row = _add_company_header(ws_daily, company_name, "VENTAS DIARIAS DETALLADAS", period_str, columns=6)
    
    headers = ["Fecha", "Nº Transacciones", "Venta Bruta (S/)", "Costo (S/)", "Utilidad (S/)", "Margen (%)"]
    _style_header_row(ws_daily, row, headers)
    data_start_row = row + 1
    row += 1
    
    for day_key in sorted(by_day.keys()):
        day_data = by_day[day_key]
        
        ws_daily.cell(row=row, column=1, value=day_key)
        ws_daily.cell(row=row, column=2, value=day_data["count"])
        ws_daily.cell(row=row, column=3, value=float(day_data["total"])).number_format = CURRENCY_FORMAT
        ws_daily.cell(row=row, column=4, value=float(day_data["cost"])).number_format = CURRENCY_FORMAT
        # Utilidad = Fórmula Excel: Venta - Costo
        ws_daily.cell(row=row, column=5, value=f"=C{row}-D{row}").number_format = CURRENCY_FORMAT
        # Margen % = Fórmula Excel: (Utilidad / Venta) * 100
        ws_daily.cell(row=row, column=6, value=f"=IF(C{row}>0,E{row}/C{row},0)").number_format = PERCENT_FORMAT
        
        for col in range(1, 7):
            ws_daily.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    # Fila de totales con fórmulas
    totals_row = row
    _add_totals_row_with_formulas(ws_daily, totals_row, data_start_row, [
        {"type": "label", "value": "TOTALES"},
        {"type": "sum", "col_letter": "B"},
        {"type": "sum", "col_letter": "C", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "D", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "E", "number_format": CURRENCY_FORMAT},
        {"type": "formula", "value": f"=IF(C{totals_row}>0,E{totals_row}/C{totals_row},0)", "number_format": PERCENT_FORMAT},
    ])
    
    # Agregar notas explicativas
    _add_notes_section(ws_daily, totals_row, [
        "Venta Bruta: Total facturado sin incluir descuentos aplicados.",
        "Costo: Precio de compra/adquisición de los productos vendidos.",
        "Utilidad = Venta Bruta - Costo (fórmula verificable en Excel).",
        "Margen % = Utilidad ÷ Venta Bruta × 100.",
    ], columns=6)
    
    _auto_adjust_columns(ws_daily)
    
    # =================
    # HOJA 3: VENTAS POR CATEGORÍA (con fórmulas de Excel)
    # =================
    ws_category = wb.create_sheet("Por Categoría")
    row = _add_company_header(ws_category, company_name, "ANÁLISIS DE VENTAS POR CATEGORÍA", period_str, columns=7)
    
    headers = ["Categoría", "Unidades Vendidas", "Venta Bruta (S/)", "Costo (S/)", "Utilidad (S/)", "Margen (%)", "Participación (%)"]
    _style_header_row(ws_category, row, headers)
    cat_data_start = row + 1
    row += 1
    
    sorted_categories = sorted(by_category.items(), key=lambda x: x[1]["total"], reverse=True)
    
    for cat_name, cat_data in sorted_categories:
        ws_category.cell(row=row, column=1, value=cat_name)
        ws_category.cell(row=row, column=2, value=cat_data["qty"])
        ws_category.cell(row=row, column=3, value=float(cat_data["total"])).number_format = CURRENCY_FORMAT
        ws_category.cell(row=row, column=4, value=float(cat_data["cost"])).number_format = CURRENCY_FORMAT
        # Utilidad = Fórmula: Venta - Costo
        ws_category.cell(row=row, column=5, value=f"=C{row}-D{row}").number_format = CURRENCY_FORMAT
        # Margen % = Fórmula: Utilidad / Venta
        ws_category.cell(row=row, column=6, value=f"=IF(C{row}>0,E{row}/C{row},0)").number_format = PERCENT_FORMAT
        # % del Total = se calculará con referencia al total
        ws_category.cell(row=row, column=7, value=float(cat_data["total"])).number_format = CURRENCY_FORMAT  # Temporal
        
        for col in range(1, 8):
            ws_category.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    cat_totals_row = row
    _add_totals_row_with_formulas(ws_category, cat_totals_row, cat_data_start, [
        {"type": "label", "value": "TOTALES"},
        {"type": "sum", "col_letter": "B"},
        {"type": "sum", "col_letter": "C", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "D", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "E", "number_format": CURRENCY_FORMAT},
        {"type": "formula", "value": f"=IF(C{cat_totals_row}>0,E{cat_totals_row}/C{cat_totals_row},0)", "number_format": PERCENT_FORMAT},
        {"type": "text", "value": "100.00%"},
    ])
    
    # Actualizar columna G con fórmulas de participación
    for r in range(cat_data_start, cat_totals_row):
        ws_category.cell(row=r, column=7, value=f"=IF($C${cat_totals_row}>0,C{r}/$C${cat_totals_row},0)").number_format = PERCENT_FORMAT
    
    _add_notes_section(ws_category, cat_totals_row, [
        "Unidades Vendidas: Cantidad total de productos vendidos de esta categoría.",
        "Utilidad = Venta Bruta - Costo.",
        "Margen = Utilidad ÷ Venta Bruta (indica rentabilidad por categoría).",
        "Participación = Venta de categoría ÷ Venta Total (peso relativo).",
    ], columns=7)
    
    _auto_adjust_columns(ws_category)
    
    # =================
    # HOJA 4: POR MÉTODO DE PAGO (con fórmulas)
    # =================
    ws_payment = wb.create_sheet("Por Método de Pago")
    row = _add_company_header(ws_payment, company_name, "RECAUDACIÓN POR MÉTODO DE PAGO", period_str, columns=4)
    
    headers = ["Método de Pago", "Nº Operaciones", "Monto Recaudado (S/)", "Participación (%)"]
    _style_header_row(ws_payment, row, headers)
    pay_data_start = row + 1
    row += 1
    
    sorted_payments = sorted(by_payment.items(), key=lambda x: x[1]["total"], reverse=True)
    
    for method, method_data in sorted_payments:
        # Traducir métodos de pago a español
        method_es = _translate_payment_method(method)
        ws_payment.cell(row=row, column=1, value=method_es)
        ws_payment.cell(row=row, column=2, value=method_data["count"])
        ws_payment.cell(row=row, column=3, value=float(method_data["total"])).number_format = CURRENCY_FORMAT
        ws_payment.cell(row=row, column=4, value=float(method_data["total"])).number_format = CURRENCY_FORMAT  # Temporal
        
        for col in range(1, 5):
            ws_payment.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    pay_totals_row = row
    _add_totals_row_with_formulas(ws_payment, pay_totals_row, pay_data_start, [
        {"type": "label", "value": "TOTAL RECAUDADO"},
        {"type": "sum", "col_letter": "B"},
        {"type": "sum", "col_letter": "C", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": "100.00%"},
    ])
    
    # Actualizar columna D con fórmulas de participación
    for r in range(pay_data_start, pay_totals_row):
        ws_payment.cell(row=r, column=4, value=f"=IF($C${pay_totals_row}>0,C{r}/$C${pay_totals_row},0)").number_format = PERCENT_FORMAT
    
    _add_notes_section(ws_payment, pay_totals_row, [
        "Nº Operaciones: Cantidad de pagos registrados con este método.",
        "Monto Recaudado: Suma total de pagos recibidos por método.",
        "Participación: Porcentaje del total recaudado que representa cada método.",
    ], columns=4)
    
    _auto_adjust_columns(ws_payment)
    
    # =================
    # HOJA 5: POR VENDEDOR (con fórmulas)
    # =================
    ws_user = wb.create_sheet("Por Vendedor")
    row = _add_company_header(ws_user, company_name, "RENDIMIENTO POR VENDEDOR", period_str, columns=5)
    
    headers = ["Vendedor", "Nº Transacciones", "Venta Total (S/)", "Ticket Promedio (S/)", "Participación (%)"]
    _style_header_row(ws_user, row, headers)
    user_data_start = row + 1
    row += 1
    
    sorted_users = sorted(by_user.items(), key=lambda x: x[1]["total"], reverse=True)
    
    for user_name, user_data in sorted_users:
        ws_user.cell(row=row, column=1, value=user_name)
        ws_user.cell(row=row, column=2, value=user_data["count"])
        ws_user.cell(row=row, column=3, value=float(user_data["total"])).number_format = CURRENCY_FORMAT
        # Ticket Promedio = Fórmula: Venta Total / Nº Transacciones
        ws_user.cell(row=row, column=4, value=f"=IF(B{row}>0,C{row}/B{row},0)").number_format = CURRENCY_FORMAT
        # Participación - se calculará con referencia al total
        ws_user.cell(row=row, column=5, value=float(user_data["total"])).number_format = CURRENCY_FORMAT  # Temporal
        
        for col in range(1, 6):
            ws_user.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    user_totals_row = row
    _add_totals_row_with_formulas(ws_user, user_totals_row, user_data_start, [
        {"type": "label", "value": "TOTAL EQUIPO"},
        {"type": "sum", "col_letter": "B"},
        {"type": "sum", "col_letter": "C", "number_format": CURRENCY_FORMAT},
        {"type": "formula", "value": f"=IF(B{user_totals_row}>0,C{user_totals_row}/B{user_totals_row},0)", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": "100.00%"},
    ])
    
    # Actualizar columna E con fórmulas de participación
    for r in range(user_data_start, user_totals_row):
        ws_user.cell(row=r, column=5, value=f"=IF($C${user_totals_row}>0,C{r}/$C${user_totals_row},0)").number_format = PERCENT_FORMAT
    
    _add_notes_section(ws_user, user_totals_row, [
        "Nº Transacciones: Cantidad de ventas realizadas por el vendedor.",
        "Ticket Promedio = Venta Total ÷ Nº Transacciones.",
        "Participación: Porcentaje de ventas del vendedor respecto al total del equipo.",
    ], columns=5)
    
    _auto_adjust_columns(ws_user)
    
    # =================
    # HOJA 6: DETALLE DE TRANSACCIONES (mejorado)
    # =================
    ws_detail = wb.create_sheet("Detalle Transacciones")
    row = _add_company_header(ws_detail, company_name, "LISTADO DETALLADO DE TRANSACCIONES", period_str, columns=10)
    
    headers = [
        "Nº Venta", "Fecha y Hora", "Cliente", "Vendedor", "Productos Vendidos",
        "Venta (S/)", "Costo (S/)", "Utilidad (S/)", "Forma de Pago", "Estado"
    ]
    _style_header_row(ws_detail, row, headers)
    detail_data_start = row + 1
    row += 1
    
    for sale in sales:
        # Productos
        products = []
        sale_cost = Decimal("0")
        for item in (sale.items or []):
            name = item.product_name_snapshot or "Producto"
            qty = item.quantity or 0
            products.append(f"{name} x{qty}")
            # Obtener costo del producto relacionado
            cost_price = _safe_decimal(item.product.purchase_price) if item.product else Decimal("0")
            sale_cost += cost_price * _safe_decimal(qty)
        
        products_str = "; ".join(products) if products else "Sin productos"
        
        # Método de pago
        payment_method = "No especificado"
        for payment in (sale.payments or []):
            if payment.method_type:
                payment_method = _translate_payment_method(payment.method_type.value)
                break
        
        sale_total = _safe_decimal(sale.total_amount)
        
        is_credit = (
            bool(getattr(sale, "is_credit", False)) or
            (sale.payment_condition or "").lower() in {"credito", "credit"}
        )
        if is_credit:
            payment_method = "Crédito/Fiado"
        
        # Estado traducido
        status_es = _translate_sale_status(sale.status.value) if sale.status else "Desconocido"
        
        ws_detail.cell(row=row, column=1, value=sale.id)
        ws_detail.cell(row=row, column=2, value=sale.timestamp.strftime("%d/%m/%Y %H:%M") if sale.timestamp else "Sin fecha")
        ws_detail.cell(row=row, column=3, value=sale.client.name if sale.client else "Cliente General")
        ws_detail.cell(row=row, column=4, value=sale.user.username if sale.user else "Sistema")
        ws_detail.cell(row=row, column=5, value=products_str[:80])  # Limitar longitud
        ws_detail.cell(row=row, column=6, value=float(sale_total)).number_format = CURRENCY_FORMAT
        ws_detail.cell(row=row, column=7, value=float(sale_cost)).number_format = CURRENCY_FORMAT
        # Utilidad = Fórmula: Venta - Costo
        ws_detail.cell(row=row, column=8, value=f"=F{row}-G{row}").number_format = CURRENCY_FORMAT
        ws_detail.cell(row=row, column=9, value=payment_method)
        ws_detail.cell(row=row, column=10, value=status_es)
        
        for col in range(1, 11):
            ws_detail.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    # Fila de totales con fórmulas
    detail_totals_row = row
    _add_totals_row_with_formulas(ws_detail, detail_totals_row, detail_data_start, [
        {"type": "label", "value": "TOTALES"},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "sum", "col_letter": "F", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "G", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "H", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
    ])
    
    _auto_adjust_columns(ws_detail)
    
    # =================
    # HOJA 7: PRODUCTOS MÁS VENDIDOS (TOP 20, con fórmulas)
    # =================
    ws_top_products = wb.create_sheet("Top Productos")
    row = _add_company_header(ws_top_products, company_name, "RANKING DE PRODUCTOS MÁS VENDIDOS", period_str, columns=8)
    
    # Calcular productos más vendidos
    by_product: dict[str, dict] = {}
    for sale in sales:
        if sale.status == SaleStatus.cancelled:
            continue
        for item in (sale.items or []):
            product_name = item.product_name_snapshot or "Producto sin nombre"
            product_id = item.product_id or 0
            key = f"{product_id}|{product_name}"
            qty = _safe_int(item.quantity)
            subtotal = _safe_decimal(item.subtotal)
            cost_price = _safe_decimal(item.product.purchase_price) if item.product else Decimal("0")
            item_cost = cost_price * Decimal(str(qty))
            
            if key not in by_product:
                by_product[key] = {
                    "name": product_name,
                    "category": item.product_category_snapshot or "Sin categoría",
                    "qty": 0,
                    "total": Decimal("0"),
                    "cost": Decimal("0"),
                    "transactions": 0,
                }
            by_product[key]["qty"] += qty
            by_product[key]["total"] += subtotal
            by_product[key]["cost"] += item_cost
            by_product[key]["transactions"] += 1
    
    headers = [
        "Producto", "Categoría", "Unidades Vendidas", "Nº Ventas",
        "Ingresos (S/)", "Costo (S/)", "Utilidad (S/)", "Margen (%)"
    ]
    _style_header_row(ws_top_products, row, headers)
    top_data_start = row + 1
    row += 1
    
    # Ordenar por total de venta (mayor primero) y limitar a top 20
    sorted_products = sorted(by_product.values(), key=lambda x: x["total"], reverse=True)[:20]
    
    for prod in sorted_products:
        ws_top_products.cell(row=row, column=1, value=prod["name"][:50])
        ws_top_products.cell(row=row, column=2, value=prod["category"])
        ws_top_products.cell(row=row, column=3, value=prod["qty"])
        ws_top_products.cell(row=row, column=4, value=prod["transactions"])
        ws_top_products.cell(row=row, column=5, value=float(prod["total"])).number_format = CURRENCY_FORMAT
        ws_top_products.cell(row=row, column=6, value=float(prod["cost"])).number_format = CURRENCY_FORMAT
        # Utilidad = Fórmula: Ingresos - Costo
        ws_top_products.cell(row=row, column=7, value=f"=E{row}-F{row}").number_format = CURRENCY_FORMAT
        # Margen = Fórmula: Utilidad / Ingresos
        ws_top_products.cell(row=row, column=8, value=f"=IF(E{row}>0,G{row}/E{row},0)").number_format = PERCENT_FORMAT
        
        for col in range(1, 9):
            ws_top_products.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    # Totales con fórmulas
    top_totals_row = row
    _add_totals_row_with_formulas(ws_top_products, top_totals_row, top_data_start, [
        {"type": "label", "value": "TOTALES TOP 20"},
        {"type": "text", "value": ""},
        {"type": "sum", "col_letter": "C"},
        {"type": "sum", "col_letter": "D"},
        {"type": "sum", "col_letter": "E", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "F", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "G", "number_format": CURRENCY_FORMAT},
        {"type": "formula", "value": f"=IF(E{top_totals_row}>0,G{top_totals_row}/E{top_totals_row},0)", "number_format": PERCENT_FORMAT},
    ])
    
    _add_notes_section(ws_top_products, top_totals_row, [
        "Este ranking muestra los 20 productos con mayores ingresos en el período.",
        "Unidades Vendidas: Cantidad total de unidades vendidas del producto.",
        "Nº Ventas: Cantidad de transacciones donde aparece el producto.",
        "Margen = Utilidad ÷ Ingresos (rentabilidad del producto).",
    ], columns=8)
    
    _auto_adjust_columns(ws_top_products)
    
    # =================
    # HOJA 8: ANÁLISIS HORARIO (con fórmulas)
    # =================
    ws_hourly = wb.create_sheet("Análisis Horario")
    row = _add_company_header(ws_hourly, company_name, "DISTRIBUCIÓN DE VENTAS POR HORA", period_str, columns=5)
    
    by_hour: dict[int, dict] = {}
    for sale in sales:
        if sale.status == SaleStatus.cancelled:
            continue
        if sale.timestamp:
            hour = sale.timestamp.hour
            if hour not in by_hour:
                by_hour[hour] = {"count": 0, "total": Decimal("0")}
            by_hour[hour]["count"] += 1
            by_hour[hour]["total"] += _safe_decimal(sale.total_amount)
    
    headers = ["Franja Horaria", "Nº Transacciones", "Venta Total (S/)", "Participación (%)", "Ticket Promedio (S/)"]
    _style_header_row(ws_hourly, row, headers)
    hourly_data_start = row + 1
    row += 1
    
    for hour in sorted(by_hour.keys()):
        hour_data = by_hour[hour]
        
        ws_hourly.cell(row=row, column=1, value=f"{hour:02d}:00 - {hour:02d}:59")
        ws_hourly.cell(row=row, column=2, value=hour_data["count"])
        ws_hourly.cell(row=row, column=3, value=float(hour_data["total"])).number_format = CURRENCY_FORMAT
        # Participación - se calculará con referencia al total
        ws_hourly.cell(row=row, column=4, value=float(hour_data["total"])).number_format = CURRENCY_FORMAT  # Temporal
        # Ticket Promedio = Fórmula: Venta / Transacciones
        ws_hourly.cell(row=row, column=5, value=f"=IF(B{row}>0,C{row}/B{row},0)").number_format = CURRENCY_FORMAT
        
        for col in range(1, 6):
            ws_hourly.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    hourly_totals_row = row
    _add_totals_row_with_formulas(ws_hourly, hourly_totals_row, hourly_data_start, [
        {"type": "label", "value": "TOTAL DÍA"},
        {"type": "sum", "col_letter": "B"},
        {"type": "sum", "col_letter": "C", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": "100.00%"},
        {"type": "formula", "value": f"=IF(B{hourly_totals_row}>0,C{hourly_totals_row}/B{hourly_totals_row},0)", "number_format": CURRENCY_FORMAT},
    ])
    
    # Actualizar columna D con fórmulas de participación
    for r in range(hourly_data_start, hourly_totals_row):
        ws_hourly.cell(row=r, column=4, value=f"=IF($C${hourly_totals_row}>0,C{r}/$C${hourly_totals_row},0)").number_format = PERCENT_FORMAT
    
    _add_notes_section(ws_hourly, hourly_totals_row, [
        "Este análisis muestra las horas de mayor actividad comercial.",
        "Utilice esta información para optimizar horarios de personal.",
        "Franja Horaria: Período de 1 hora del día.",
        "Ticket Promedio = Venta Total ÷ Nº Transacciones.",
    ], columns=5)
    
    _auto_adjust_columns(ws_hourly)
    
    # Guardar
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# =============================================================================
# REPORTE DE INVENTARIO VALORIZADO
# =============================================================================

def generate_inventory_report(
    session,
    company_name: str = "TUWAYKIAPP",
    include_zero_stock: bool = True,
) -> io.BytesIO:
    """
    Genera reporte de inventario valorizado profesional.
    
    Incluye:
    - Resumen de valorización
    - Detalle por categoría
    - Análisis ABC
    - Productos con stock crítico
    - Rotación estimada
    """
    wb = Workbook()
    
    # Consultar productos
    query = select(Product).order_by(Product.category, Product.description)
    if not include_zero_stock:
        query = query.where(Product.stock > 0)
    
    products = session.exec(query).all()
    
    today = datetime.now().strftime("%d/%m/%Y")
    
    # =================
    # HOJA 1: RESUMEN
    # =================
    ws_summary = wb.active
    ws_summary.title = "Resumen Valorización"
    
    row = _add_company_header(ws_summary, company_name, "INVENTARIO VALORIZADO", f"Al {today}")
    
    # Calcular métricas
    total_items = len(products)
    total_units = sum(p.stock or 0 for p in products)
    total_cost_value = sum((p.stock or 0) * (p.purchase_price or 0) for p in products)
    total_sale_value = sum((p.stock or 0) * (p.sale_price or 0) for p in products)
    potential_profit = total_sale_value - total_cost_value
    
    stock_zero = sum(1 for p in products if (p.stock or 0) == 0)
    stock_low = sum(1 for p in products if 0 < (p.stock or 0) <= 5)
    stock_medium = sum(1 for p in products if 5 < (p.stock or 0) <= 10)
    stock_ok = sum(1 for p in products if (p.stock or 0) > 10)
    
    by_category: dict[str, dict] = {}
    for p in products:
        cat = p.category or "Sin categoría"
        if cat not in by_category:
            by_category[cat] = {"items": 0, "units": 0, "cost": Decimal("0"), "sale": Decimal("0")}
        by_category[cat]["items"] += 1
        by_category[cat]["units"] += p.stock or 0
        by_category[cat]["cost"] += Decimal(str((p.stock or 0) * (p.purchase_price or 0)))
        by_category[cat]["sale"] += Decimal(str((p.stock or 0) * (p.sale_price or 0)))
    
    row += 1
    ws_summary.cell(row=row, column=1, value="RESUMEN DE VALORIZACIÓN").font = SUBTITLE_FONT
    row += 1
    
    summary_data = [
        ("Total de Productos (SKU):", total_items),
        ("Total de Unidades en Stock:", total_units),
        ("", ""),
        ("Valor al Costo:", _format_currency(total_cost_value)),
        ("Valor a Precio Venta:", _format_currency(total_sale_value)),
        ("Utilidad Potencial:", _format_currency(potential_profit)),
        ("", ""),
        ("ESTADO DEL STOCK:", ""),
        ("   Sin stock (0 unidades):", stock_zero),
        ("   Stock crítico (1-5 unidades):", stock_low),
        ("   Stock bajo (6-10 unidades):", stock_medium),
        ("   Stock normal (>10 unidades):", stock_ok),
    ]
    
    for label, value in summary_data:
        ws_summary.cell(row=row, column=1, value=label).font = Font(bold=True) if not label.startswith("   ") else Font()
        ws_summary.cell(row=row, column=2, value=value)
        row += 1
    
    _auto_adjust_columns(ws_summary)
    
    # =================
    # HOJA 2: POR CATEGORÍA (con fórmulas)
    # =================
    ws_category = wb.create_sheet("Por Categoría")
    row = _add_company_header(ws_category, company_name, "VALORIZACIÓN POR CATEGORÍA DE PRODUCTO", f"Al {today}", columns=7)
    
    headers = ["Categoría", "Nº Productos", "Unidades en Stock", "Valor al Costo (S/)", "Valor a Venta (S/)", "Utilidad Potencial (S/)", "Participación (%)"]
    _style_header_row(ws_category, row, headers)
    inv_cat_data_start = row + 1
    row += 1
    
    sorted_cats = sorted(by_category.items(), key=lambda x: x[1]["cost"], reverse=True)
    
    for cat_name, cat_data in sorted_cats:
        ws_category.cell(row=row, column=1, value=cat_name)
        ws_category.cell(row=row, column=2, value=cat_data["items"])
        ws_category.cell(row=row, column=3, value=cat_data["units"])
        ws_category.cell(row=row, column=4, value=float(cat_data["cost"])).number_format = CURRENCY_FORMAT
        ws_category.cell(row=row, column=5, value=float(cat_data["sale"])).number_format = CURRENCY_FORMAT
        # Utilidad Potencial = Fórmula: Valor Venta - Valor Costo
        ws_category.cell(row=row, column=6, value=f"=E{row}-D{row}").number_format = CURRENCY_FORMAT
        # Participación - temporal, se actualizará con fórmula
        ws_category.cell(row=row, column=7, value=float(cat_data["cost"])).number_format = CURRENCY_FORMAT
        
        for col in range(1, 8):
            ws_category.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    inv_cat_totals_row = row
    _add_totals_row_with_formulas(ws_category, inv_cat_totals_row, inv_cat_data_start, [
        {"type": "label", "value": "TOTAL INVENTARIO"},
        {"type": "sum", "col_letter": "B"},
        {"type": "sum", "col_letter": "C"},
        {"type": "sum", "col_letter": "D", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "E", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "F", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": "100.00%"},
    ])
    
    # Actualizar columna G con fórmulas de participación
    for r in range(inv_cat_data_start, inv_cat_totals_row):
        ws_category.cell(row=r, column=7, value=f"=IF($D${inv_cat_totals_row}>0,D{r}/$D${inv_cat_totals_row},0)").number_format = PERCENT_FORMAT
    
    _add_notes_section(ws_category, inv_cat_totals_row, [
        "Valor al Costo: Stock × Precio de Compra.",
        "Valor a Venta: Stock × Precio de Venta al Público.",
        "Utilidad Potencial = Valor a Venta - Valor al Costo (ganancia si se vende todo).",
        "Participación: Peso de la categoría sobre el valor total del inventario.",
    ], columns=7)
    
    _auto_adjust_columns(ws_category)
    
    # =================
    # HOJA 3: DETALLE COMPLETO (con fórmulas)
    # =================
    ws_detail = wb.create_sheet("Detalle Inventario")
    row = _add_company_header(ws_detail, company_name, "LISTADO DETALLADO DE PRODUCTOS EN INVENTARIO", f"Al {today}", columns=12)
    
    headers = [
        "Código/SKU", "Descripción del Producto", "Categoría", "Stock Actual", "Unidad de Medida",
        "Costo Unitario (S/)", "Precio Venta (S/)", "Margen Unitario (S/)", "Margen (%)",
        "Valor en Costo (S/)", "Valor en Venta (S/)", "Estado Stock"
    ]
    _style_header_row(ws_detail, row, headers)
    inv_detail_start = row + 1
    row += 1
    
    for product in products:
        stock = _safe_int(product.stock)
        cost = _safe_decimal(product.purchase_price)
        price = _safe_decimal(product.sale_price)
        
        # Estado del stock
        if stock == 0:
            status = "SIN STOCK"
        elif stock <= 5:
            status = "⚠️ CRÍTICO"
        elif stock <= 10:
            status = "⚡ BAJO"
        else:
            status = "✅ NORMAL"
        
        ws_detail.cell(row=row, column=1, value=_safe_string(product.barcode, "S/C"))
        ws_detail.cell(row=row, column=2, value=_safe_string(product.description, "Sin descripción"))
        ws_detail.cell(row=row, column=3, value=_safe_string(product.category, "Sin categoría"))
        ws_detail.cell(row=row, column=4, value=stock)
        ws_detail.cell(row=row, column=5, value=_safe_string(product.unit, "Unid."))
        ws_detail.cell(row=row, column=6, value=float(cost)).number_format = CURRENCY_FORMAT
        ws_detail.cell(row=row, column=7, value=float(price)).number_format = CURRENCY_FORMAT
        # Margen Unitario = Fórmula: Precio - Costo
        ws_detail.cell(row=row, column=8, value=f"=G{row}-F{row}").number_format = CURRENCY_FORMAT
        # Margen % = Fórmula: Margen / Costo (si costo > 0)
        ws_detail.cell(row=row, column=9, value=f"=IF(F{row}>0,H{row}/F{row},0)").number_format = PERCENT_FORMAT
        # Valor en Costo = Fórmula: Stock × Costo
        ws_detail.cell(row=row, column=10, value=f"=D{row}*F{row}").number_format = CURRENCY_FORMAT
        # Valor en Venta = Fórmula: Stock × Precio
        ws_detail.cell(row=row, column=11, value=f"=D{row}*G{row}").number_format = CURRENCY_FORMAT
        ws_detail.cell(row=row, column=12, value=status)
        
        # Color según estado
        status_cell = ws_detail.cell(row=row, column=12)
        if "SIN STOCK" in status:
            status_cell.fill = NEGATIVE_FILL
        elif "CRÍTICO" in status:
            status_cell.fill = WARNING_FILL
        elif "BAJO" in status:
            status_cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        else:
            status_cell.fill = POSITIVE_FILL
        
        for col in range(1, 13):
            ws_detail.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    # Fila de totales con fórmulas
    inv_detail_totals = row
    _add_totals_row_with_formulas(ws_detail, inv_detail_totals, inv_detail_start, [
        {"type": "label", "value": "TOTALES"},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "sum", "col_letter": "D"},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "sum", "col_letter": "J", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "K", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": ""},
    ])
    
    _add_notes_section(ws_detail, inv_detail_totals, [
        "Código/SKU: Identificador único del producto (código de barras o interno).",
        "Margen Unitario = Precio Venta - Costo Unitario.",
        "Margen % = Margen Unitario ÷ Costo Unitario (rentabilidad sobre costo).",
        "Valor en Costo = Stock × Costo Unitario (inversión en inventario).",
        "Valor en Venta = Stock × Precio Venta (potencial de venta).",
        "Estados: ❌ SIN STOCK (0 unid.), ⚠️ CRÍTICO (1-5), ⚡ BAJO (6-10), ✅ NORMAL (>10).",
    ], columns=12)
    
    _auto_adjust_columns(ws_detail)
    
    # =================
    # HOJA 4: STOCK CRÍTICO (productos a reponer)
    # =================
    ws_critical = wb.create_sheet("Productos a Reponer")
    row = _add_company_header(ws_critical, company_name, "PRODUCTOS CON STOCK CRÍTICO - REQUIEREN REPOSICIÓN", f"Al {today}", columns=6)
    
    headers = ["Código/SKU", "Descripción", "Categoría", "Stock Actual", "Precio Venta (S/)", "Valor Disponible (S/)"]
    _style_header_row(ws_critical, row, headers)
    critical_data_start = row + 1
    row += 1
    
    critical_products = [p for p in products if _safe_int(p.stock) <= 10]
    critical_products.sort(key=lambda p: _safe_int(p.stock))
    
    for product in critical_products:
        stock = _safe_int(product.stock)
        
        ws_critical.cell(row=row, column=1, value=_safe_string(product.barcode, "S/C"))
        ws_critical.cell(row=row, column=2, value=_safe_string(product.description, "Sin descripción"))
        ws_critical.cell(row=row, column=3, value=_safe_string(product.category, "Sin categoría"))
        ws_critical.cell(row=row, column=4, value=stock)
        ws_critical.cell(row=row, column=5, value=float(_safe_decimal(product.sale_price))).number_format = CURRENCY_FORMAT
        # Valor Disponible = Fórmula: Stock × Precio
        ws_critical.cell(row=row, column=6, value=f"=D{row}*E{row}").number_format = CURRENCY_FORMAT
        
        for col in range(1, 7):
            ws_critical.cell(row=row, column=col).border = THIN_BORDER
        
        # Color según nivel de urgencia
        if stock == 0:
            for col in range(1, 7):
                ws_critical.cell(row=row, column=col).fill = NEGATIVE_FILL
        elif stock <= 5:
            for col in range(1, 7):
                ws_critical.cell(row=row, column=col).fill = WARNING_FILL
        
        row += 1
    
    critical_totals_row = row
    _add_totals_row_with_formulas(ws_critical, critical_totals_row, critical_data_start, [
        {"type": "label", "value": "TOTALES"},
        {"type": "text", "value": f"{len(critical_products)} productos"},
        {"type": "text", "value": ""},
        {"type": "sum", "col_letter": "D"},
        {"type": "text", "value": ""},
        {"type": "sum", "col_letter": "F", "number_format": CURRENCY_FORMAT},
    ])
    
    _add_notes_section(ws_critical, critical_totals_row, [
        "Esta lista muestra productos que necesitan reposición urgente.",
        "🔴 Rojo: Sin stock (0 unidades) - Requiere pedido inmediato.",
        "🟡 Amarillo: Stock crítico (1-5 unidades) - Prioridad alta.",
        "⚪ Sin color: Stock bajo (6-10 unidades) - Planificar reposición.",
        "Valor Disponible: Dinero en inventario de estos productos.",
    ], columns=6)
    
    _auto_adjust_columns(ws_critical)
    
    # Guardar
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# =============================================================================
# REPORTE DE CUENTAS POR COBRAR (ANTIGÜEDAD DE DEUDA)
# =============================================================================

def generate_receivables_report(
    session,
    company_name: str = "TUWAYKIAPP",
) -> io.BytesIO:
    """
    Genera reporte de cuentas por cobrar con análisis de antigüedad.
    
    Incluye:
    - Resumen de cartera
    - Antigüedad de deuda (0-30, 31-60, 61-90, >90 días)
    - Detalle por cliente
    - Provisión sugerida para cobranza dudosa
    """
    wb = Workbook()
    
    # Consultar cuotas pendientes
    query = (
        select(SaleInstallment)
        .where(SaleInstallment.status != "paid")
        .order_by(SaleInstallment.due_date)
    )
    
    installments = session.exec(query).all()
    
    # Cargar ventas y clientes relacionados
    sale_ids = list(set(inst.sale_id for inst in installments if inst.sale_id))
    sales_map = {}
    clients_map = {}
    
    if sale_ids:
        sales_query = select(Sale).where(Sale.id.in_(sale_ids)).options(selectinload(Sale.client))
        sales_list = session.exec(sales_query).all()
        for sale in sales_list:
            sales_map[sale.id] = sale
            if sale.client:
                clients_map[sale.id] = sale.client
    
    today = datetime.now()
    today_str = today.strftime("%d/%m/%Y")
    
    # Clasificar por antigüedad
    aging_buckets = {
        "current": {"label": "Vigente (no vencido)", "days": "0", "amount": Decimal("0"), "count": 0},
        "0-30": {"label": "1-30 días", "days": "1-30", "amount": Decimal("0"), "count": 0},
        "31-60": {"label": "31-60 días", "days": "31-60", "amount": Decimal("0"), "count": 0},
        "61-90": {"label": "61-90 días", "days": "61-90", "amount": Decimal("0"), "count": 0},
        "90+": {"label": "Más de 90 días", "days": ">90", "amount": Decimal("0"), "count": 0},
    }
    
    # Provisiones sugeridas
    provision_rates = {
        "current": Decimal("0"),
        "0-30": Decimal("0.05"),  # 5%
        "31-60": Decimal("0.10"),  # 10%
        "61-90": Decimal("0.25"),  # 25%
        "90+": Decimal("0.50"),   # 50%
    }
    
    by_client: dict[str, dict] = {}
    installments_data = []
    
    for installment in installments:
        amount = Decimal(str(installment.amount or 0))
        paid = Decimal(str(installment.paid_amount or 0))
        pending = amount - paid
        
        if pending <= 0:
            continue
        
        sale = sales_map.get(installment.sale_id)
        client = clients_map.get(installment.sale_id)
        client_name = client.name if client else "Sin cliente"
        due_date = installment.due_date
        
        # Calcular antigüedad - normalizar a date
        if due_date:
            if hasattr(due_date, 'date'):
                due_date_normalized = due_date.date()
            else:
                due_date_normalized = due_date
            days_overdue = (today.date() - due_date_normalized).days
        else:
            days_overdue = 0
        
        if days_overdue <= 0:
            bucket = "current"
        elif days_overdue <= 30:
            bucket = "0-30"
        elif days_overdue <= 60:
            bucket = "31-60"
        elif days_overdue <= 90:
            bucket = "61-90"
        else:
            bucket = "90+"
        
        aging_buckets[bucket]["amount"] += pending
        aging_buckets[bucket]["count"] += 1
        
        # Por cliente
        if client_name not in by_client:
            by_client[client_name] = {
                "current": Decimal("0"),
                "0-30": Decimal("0"),
                "31-60": Decimal("0"),
                "61-90": Decimal("0"),
                "90+": Decimal("0"),
                "total": Decimal("0"),
            }
        by_client[client_name][bucket] += pending
        by_client[client_name]["total"] += pending
        
        installments_data.append({
            "client": client_name,
            "sale_id": sale.id if sale else 0,
            "installment_num": installment.number,
            "due_date": due_date.strftime("%d/%m/%Y") if due_date else "",
            "days_overdue": max(0, days_overdue),
            "amount": amount,
            "paid": paid,
            "pending": pending,
            "bucket": bucket,
        })
    
    total_receivables = sum(b["amount"] for b in aging_buckets.values())
    total_provision = sum(
        aging_buckets[k]["amount"] * provision_rates[k]
        for k in aging_buckets
    )
    
    # =================
    # HOJA 1: RESUMEN (mejorado)
    # =================
    ws_summary = wb.active
    ws_summary.title = "Resumen Cartera"
    
    row = _add_company_header(ws_summary, company_name, "ANÁLISIS DE CUENTAS POR COBRAR", f"Al {today_str}", columns=6)
    
    row += 1
    ws_summary.cell(row=row, column=1, value="RESUMEN DE CARTERA DE CRÉDITOS").font = SUBTITLE_FONT
    row += 1
    
    summary = [
        ("Total Cuentas por Cobrar:", _format_currency(total_receivables)),
        ("Número de Cuotas Pendientes:", sum(b["count"] for b in aging_buckets.values())),
        ("Clientes con Deuda Activa:", len(by_client)),
        ("", ""),
        ("Provisión Sugerida (Cobranza Dudosa):", _format_currency(total_provision)),
        ("Cartera Neta Estimada:", _format_currency(total_receivables - total_provision)),
    ]
    
    for label, value in summary:
        ws_summary.cell(row=row, column=1, value=label).font = Font(bold=True)
        ws_summary.cell(row=row, column=2, value=value)
        row += 1
    
    row += 2
    ws_summary.cell(row=row, column=1, value="ANTIGÜEDAD DE CARTERA (Análisis de Vencimiento)").font = SUBTITLE_FONT
    row += 1
    
    headers = ["Período de Vencimiento", "Nº Cuotas", "Monto Pendiente (S/)", "Participación (%)", "Tasa Provisión", "Provisión (S/)"]
    _style_header_row(ws_summary, row, headers)
    aging_data_start = row + 1
    row += 1
    
    for bucket_key in ["current", "0-30", "31-60", "61-90", "90+"]:
        bucket = aging_buckets[bucket_key]
        prov_rate = provision_rates[bucket_key]
        
        ws_summary.cell(row=row, column=1, value=bucket["label"])
        ws_summary.cell(row=row, column=2, value=bucket["count"])
        ws_summary.cell(row=row, column=3, value=float(bucket["amount"])).number_format = CURRENCY_FORMAT
        # Participación - temporal
        ws_summary.cell(row=row, column=4, value=float(bucket["amount"])).number_format = CURRENCY_FORMAT
        ws_summary.cell(row=row, column=5, value=float(prov_rate)).number_format = PERCENT_FORMAT
        # Provisión = Fórmula: Monto × Tasa
        ws_summary.cell(row=row, column=6, value=f"=C{row}*E{row}").number_format = CURRENCY_FORMAT
        
        for col in range(1, 7):
            ws_summary.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    aging_totals_row = row
    _add_totals_row_with_formulas(ws_summary, aging_totals_row, aging_data_start, [
        {"type": "label", "value": "TOTAL CARTERA"},
        {"type": "sum", "col_letter": "B"},
        {"type": "sum", "col_letter": "C", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": "100.00%"},
        {"type": "text", "value": ""},
        {"type": "sum", "col_letter": "F", "number_format": CURRENCY_FORMAT},
    ])
    
    # Actualizar participación con fórmulas
    for r in range(aging_data_start, aging_totals_row):
        ws_summary.cell(row=r, column=4, value=f"=IF($C${aging_totals_row}>0,C{r}/$C${aging_totals_row},0)").number_format = PERCENT_FORMAT
    
    _add_notes_section(ws_summary, aging_totals_row, [
        "Vigente: Cuotas aún no vencidas (fecha de pago futura).",
        "Provisión: Reserva estimada para deudas de difícil cobro.",
        "Tasa de Provisión: 0% vigente, 5% (1-30d), 10% (31-60d), 25% (61-90d), 50% (>90d).",
        "Cartera Neta = Total por Cobrar - Provisión.",
    ], columns=6)
    
    _auto_adjust_columns(ws_summary)
    
    # =================
    # HOJA 2: POR CLIENTE (con fórmulas)
    # =================
    ws_client = wb.create_sheet("Por Cliente")
    row = _add_company_header(ws_client, company_name, "DEUDA DETALLADA POR CLIENTE", f"Al {today_str}", columns=7)
    
    headers = ["Cliente", "Vigente (S/)", "1-30 días (S/)", "31-60 días (S/)", "61-90 días (S/)", ">90 días (S/)", "Total Deuda (S/)"]
    _style_header_row(ws_client, row, headers)
    client_data_start = row + 1
    row += 1
    
    sorted_clients = sorted(by_client.items(), key=lambda x: x[1]["total"], reverse=True)
    
    for client_name, client_data in sorted_clients:
        ws_client.cell(row=row, column=1, value=client_name)
        ws_client.cell(row=row, column=2, value=float(client_data["current"])).number_format = CURRENCY_FORMAT
        ws_client.cell(row=row, column=3, value=float(client_data["0-30"])).number_format = CURRENCY_FORMAT
        ws_client.cell(row=row, column=4, value=float(client_data["31-60"])).number_format = CURRENCY_FORMAT
        ws_client.cell(row=row, column=5, value=float(client_data["61-90"])).number_format = CURRENCY_FORMAT
        ws_client.cell(row=row, column=6, value=float(client_data["90+"])).number_format = CURRENCY_FORMAT
        # Total = Fórmula: Suma de columnas B a F
        ws_client.cell(row=row, column=7, value=f"=SUM(B{row}:F{row})").number_format = CURRENCY_FORMAT
        
        for col in range(1, 8):
            ws_client.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    client_totals_row = row
    _add_totals_row_with_formulas(ws_client, client_totals_row, client_data_start, [
        {"type": "label", "value": "TOTAL CLIENTES"},
        {"type": "sum", "col_letter": "B", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "C", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "D", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "E", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "F", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "G", "number_format": CURRENCY_FORMAT},
    ])
    
    _add_notes_section(ws_client, client_totals_row, [
        "Los clientes están ordenados por monto total de deuda (mayor a menor).",
        "Total Deuda = Suma de todas las cuotas pendientes del cliente.",
        "Priorizar cobranza de clientes con deuda vencida (columnas 31-60, 61-90, >90 días).",
    ], columns=7)
    
    _auto_adjust_columns(ws_client)
    
    # =================
    # HOJA 3: DETALLE (mejorado)
    # =================
    ws_detail = wb.create_sheet("Detalle Cuotas")
    row = _add_company_header(ws_detail, company_name, "LISTADO DETALLADO DE CUOTAS PENDIENTES", f"Al {today_str}", columns=9)
    
    headers = ["Cliente", "Nº Venta", "Nº Cuota", "Fecha Vencimiento", "Días Vencido", "Monto Cuota (S/)", "Abonado (S/)", "Pendiente (S/)", "Estado"]
    _style_header_row(ws_detail, row, headers)
    cuota_data_start = row + 1
    row += 1
    
    # Ordenar por días vencido (mayor primero)
    installments_data.sort(key=lambda x: x["days_overdue"], reverse=True)
    
    for inst in installments_data:
        ws_detail.cell(row=row, column=1, value=inst["client"])
        ws_detail.cell(row=row, column=2, value=inst["sale_id"])
        ws_detail.cell(row=row, column=3, value=inst["installment_num"])
        ws_detail.cell(row=row, column=4, value=inst["due_date"])
        ws_detail.cell(row=row, column=5, value=inst["days_overdue"])
        ws_detail.cell(row=row, column=6, value=float(inst["amount"])).number_format = CURRENCY_FORMAT
        ws_detail.cell(row=row, column=7, value=float(inst["paid"])).number_format = CURRENCY_FORMAT
        # Pendiente = Fórmula: Monto - Abonado
        ws_detail.cell(row=row, column=8, value=f"=F{row}-G{row}").number_format = CURRENCY_FORMAT
        ws_detail.cell(row=row, column=9, value=aging_buckets[inst["bucket"]]["label"])
        
        # Color según antigüedad
        if inst["bucket"] == "90+":
            fill = NEGATIVE_FILL
        elif inst["bucket"] == "61-90":
            fill = PatternFill(start_color="FDBA74", end_color="FDBA74", fill_type="solid")
        elif inst["bucket"] == "31-60":
            fill = WARNING_FILL
        elif inst["bucket"] == "0-30":
            fill = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")
        else:
            fill = POSITIVE_FILL
        
        for col in range(1, 10):
            cell = ws_detail.cell(row=row, column=col)
            cell.border = THIN_BORDER
            cell.fill = fill
        
        row += 1
    
    cuota_totals_row = row
    _add_totals_row_with_formulas(ws_detail, cuota_totals_row, cuota_data_start, [
        {"type": "label", "value": "TOTALES"},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "text", "value": ""},
        {"type": "sum", "col_letter": "F", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "G", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "H", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": ""},
    ])
    
    _add_notes_section(ws_detail, cuota_totals_row, [
        "Las cuotas están ordenadas por días de vencimiento (más antiguas primero).",
        "🔴 Rojo: Más de 90 días vencido - Riesgo alto de incobrabilidad.",
        "🟠 Naranja: 61-90 días - Requiere gestión de cobranza urgente.",
        "🟡 Amarillo: 31-60 días - Seguimiento prioritario.",
        "🟢 Verde: Vigente - Sin vencimiento.",
        "Pendiente = Monto de la Cuota - Monto Abonado.",
    ], columns=9)
    
    _auto_adjust_columns(ws_detail)
    
    # Guardar
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# =============================================================================
# REPORTE DE CAJA CONSOLIDADO
# =============================================================================

def generate_cashbox_report(
    session,
    start_date: datetime,
    end_date: datetime,
    company_name: str = "TUWAYKIAPP",
) -> io.BytesIO:
    """
    Genera reporte de caja consolidado.
    
    Incluye:
    - Resumen de movimientos
    - Detalle de aperturas y cierres
    - Ingresos por método de pago
    - Diferencias detectadas
    """
    wb = Workbook()
    
    period_str = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
    
    # Consultar logs de caja
    query = (
        select(CashboxLog)
        .where(
            and_(
                CashboxLog.timestamp >= start_date,
                CashboxLog.timestamp <= end_date,
            )
        )
        .order_by(CashboxLog.timestamp.desc())
    )
    
    logs = session.exec(query).all()
    
    # Consultar ventas del período
    sales_query = (
        select(Sale)
        .where(
            and_(
                Sale.timestamp >= start_date,
                Sale.timestamp <= end_date,
                Sale.status != SaleStatus.cancelled,
            )
        )
        .options(selectinload(Sale.payments))
    )
    
    sales = session.exec(sales_query).all()
    
    # Calcular métricas usando funciones seguras
    total_openings = sum(1 for log in logs if log.action == "apertura")
    total_closings = sum(1 for log in logs if log.action == "cierre")
    total_opening_amount = sum(_safe_decimal(log.amount) for log in logs if log.action == "apertura")
    total_closing_amount = sum(_safe_decimal(log.amount) for log in logs if log.action == "cierre")
    
    total_sales = sum(_safe_decimal(s.total_amount) for s in sales)
    
    by_payment: dict[str, Decimal] = {}
    for sale in sales:
        for payment in (sale.payments or []):
            method = payment.method_type.value if payment.method_type else "No especificado"
            amount = _safe_decimal(payment.amount)
            by_payment[method] = by_payment.get(method, Decimal("0")) + amount
    
    # =================
    # HOJA 1: RESUMEN (mejorado)
    # =================
    ws_summary = wb.active
    ws_summary.title = "Resumen Caja"
    
    row = _add_company_header(ws_summary, company_name, "REPORTE CONSOLIDADO DE CAJA", period_str, columns=4)
    
    row += 1
    ws_summary.cell(row=row, column=1, value="MOVIMIENTOS DE CAJA EN EL PERÍODO").font = SUBTITLE_FONT
    row += 1
    
    summary = [
        ("Número de Aperturas de Caja:", total_openings),
        ("Número de Cierres de Caja:", total_closings),
        ("", ""),
        ("Total Monto en Aperturas:", _format_currency(total_opening_amount)),
        ("Total Monto en Cierres:", _format_currency(total_closing_amount)),
        ("", ""),
        ("Total Ventas Registradas:", _format_currency(total_sales)),
        ("Número de Transacciones:", len(sales)),
    ]
    
    for label, value in summary:
        ws_summary.cell(row=row, column=1, value=label).font = Font(bold=True)
        ws_summary.cell(row=row, column=2, value=value)
        row += 1
    
    row += 2
    ws_summary.cell(row=row, column=1, value="RECAUDACIÓN POR MÉTODO DE PAGO").font = SUBTITLE_FONT
    row += 1
    
    headers = ["Método de Pago", "Monto Recaudado (S/)", "Participación (%)", "Observación"]
    _style_header_row(ws_summary, row, headers)
    caja_pay_start = row + 1
    row += 1
    
    sorted_payments = sorted(by_payment.items(), key=lambda x: x[1], reverse=True)
    total_payments = sum(by_payment.values())
    
    for method, amount in sorted_payments:
        method_es = _translate_payment_method(method)
        
        ws_summary.cell(row=row, column=1, value=method_es)
        ws_summary.cell(row=row, column=2, value=float(amount)).number_format = CURRENCY_FORMAT
        # Participación - temporal
        ws_summary.cell(row=row, column=3, value=float(amount)).number_format = CURRENCY_FORMAT
        # Observación según método
        obs = "Debe cuadrar con caja física" if method_es.lower() == "efectivo" else "Verificar en extracto bancario"
        ws_summary.cell(row=row, column=4, value=obs)
        
        for col in range(1, 5):
            ws_summary.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    caja_pay_totals = row
    _add_totals_row_with_formulas(ws_summary, caja_pay_totals, caja_pay_start, [
        {"type": "label", "value": "TOTAL RECAUDADO"},
        {"type": "sum", "col_letter": "B", "number_format": CURRENCY_FORMAT},
        {"type": "text", "value": "100.00%"},
        {"type": "text", "value": ""},
    ])
    
    # Actualizar participación con fórmulas
    for r in range(caja_pay_start, caja_pay_totals):
        ws_summary.cell(row=r, column=3, value=f"=IF($B${caja_pay_totals}>0,B{r}/$B${caja_pay_totals},0)").number_format = PERCENT_FORMAT
    
    _auto_adjust_columns(ws_summary)
    
    # =================
    # HOJA 2: DETALLE APERTURAS/CIERRES
    # =================
    ws_logs = wb.create_sheet("Aperturas y Cierres")
    row = _add_company_header(ws_logs, company_name, "DETALLE DE APERTURAS Y CIERRES", period_str)
    
    headers = ["Fecha/Hora", "Acción", "Monto", "Notas"]
    _style_header_row(ws_logs, row, headers)
    row += 1
    
    for log in logs:
        ws_logs.cell(row=row, column=1, value=log.timestamp.strftime("%d/%m/%Y %H:%M:%S") if log.timestamp else "")
        # Traducir acción a español
        action_es = "Apertura de Caja" if log.action == "apertura" else "Cierre de Caja" if log.action == "cierre" else (log.action or "").capitalize()
        ws_logs.cell(row=row, column=2, value=action_es)
        ws_logs.cell(row=row, column=3, value=float(_safe_decimal(log.amount))).number_format = CURRENCY_FORMAT
        ws_logs.cell(row=row, column=4, value=_safe_string(log.notes, "Sin observaciones"))
        
        for col in range(1, 5):
            ws_logs.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    _add_notes_section(ws_logs, row, [
        "Apertura de Caja: Monto inicial con el que se inicia el día.",
        "Cierre de Caja: Monto contado al finalizar el día.",
    ], columns=4)
    
    _auto_adjust_columns(ws_logs)
    
    # =================
    # HOJA 3: VENTAS POR DÍA (con fórmulas)
    # =================
    ws_daily = wb.create_sheet("Ventas Diarias")
    row = _add_company_header(ws_daily, company_name, "RESUMEN DE VENTAS DIARIAS", period_str, columns=5)
    
    # Agrupar ventas por día
    by_day: dict[str, dict] = {}
    for sale in sales:
        if sale.timestamp:
            day_key = sale.timestamp.strftime("%Y-%m-%d")
            if day_key not in by_day:
                by_day[day_key] = {"count": 0, "total": Decimal("0"), "cash": Decimal("0"), "other": Decimal("0")}
            by_day[day_key]["count"] += 1
            by_day[day_key]["total"] += _safe_decimal(sale.total_amount)
            
            for payment in (sale.payments or []):
                amount = _safe_decimal(payment.amount)
                method = (payment.method_type.value if payment.method_type else "").lower()
                if method in {"efectivo", "cash"}:
                    by_day[day_key]["cash"] += amount
                else:
                    by_day[day_key]["other"] += amount
    
    headers = ["Fecha", "Nº Transacciones", "Efectivo (S/)", "Otros Medios (S/)", "Total del Día (S/)"]
    _style_header_row(ws_daily, row, headers)
    caja_daily_start = row + 1
    row += 1
    
    for day_key in sorted(by_day.keys()):
        day_data = by_day[day_key]
        
        ws_daily.cell(row=row, column=1, value=day_key)
        ws_daily.cell(row=row, column=2, value=day_data["count"])
        ws_daily.cell(row=row, column=3, value=float(day_data["cash"])).number_format = CURRENCY_FORMAT
        ws_daily.cell(row=row, column=4, value=float(day_data["other"])).number_format = CURRENCY_FORMAT
        # Total = Fórmula: Efectivo + Otros
        ws_daily.cell(row=row, column=5, value=f"=C{row}+D{row}").number_format = CURRENCY_FORMAT
        
        for col in range(1, 6):
            ws_daily.cell(row=row, column=col).border = THIN_BORDER
        row += 1
    
    caja_daily_totals = row
    _add_totals_row_with_formulas(ws_daily, caja_daily_totals, caja_daily_start, [
        {"type": "label", "value": "TOTALES"},
        {"type": "sum", "col_letter": "B"},
        {"type": "sum", "col_letter": "C", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "D", "number_format": CURRENCY_FORMAT},
        {"type": "sum", "col_letter": "E", "number_format": CURRENCY_FORMAT},
    ])
    
    _add_notes_section(ws_daily, caja_daily_totals, [
        "Efectivo: Pagos recibidos en billetes y monedas.",
        "Otros Medios: Tarjetas, transferencias, Yape, Plin, etc.",
        "Total del Día = Efectivo + Otros Medios.",
    ], columns=5)
    
    _auto_adjust_columns(ws_daily)
    
    # =================
    # HOJA 4: CONCILIACIÓN DE CAJA (con fórmulas)
    # =================
    ws_conciliation = wb.create_sheet("Conciliación")
    row = _add_company_header(ws_conciliation, company_name, "CUADRE Y CONCILIACIÓN DE CAJA", period_str, columns=4)
    
    row += 1
    ws_conciliation.cell(row=row, column=1, value="ANÁLISIS DE FLUJO DE EFECTIVO").font = SUBTITLE_FONT
    row += 2
    
    # Calcular efectivo esperado
    cash_from_sales = sum(by_day[d]["cash"] for d in by_day)
    
    # Escribir datos con referencias para fórmulas
    data_start_row = row
    ws_conciliation.cell(row=row, column=1, value="(+) Monto Inicial (Aperturas):").font = Font(bold=True)
    ws_conciliation.cell(row=row, column=2, value=float(total_opening_amount)).number_format = CURRENCY_FORMAT
    ws_conciliation.cell(row=row, column=3, value="Suma de todas las aperturas de caja")
    row += 1
    
    ws_conciliation.cell(row=row, column=1, value="(+) Ingresos en Efectivo:").font = Font(bold=True)
    ws_conciliation.cell(row=row, column=2, value=float(cash_from_sales)).number_format = CURRENCY_FORMAT
    ws_conciliation.cell(row=row, column=3, value="Total de ventas cobradas en efectivo")
    row += 1
    
    ws_conciliation.cell(row=row, column=1, value="(=) Efectivo Esperado al Cierre:").font = Font(bold=True, color="4F46E5")
    ws_conciliation.cell(row=row, column=2, value=f"=B{data_start_row}+B{data_start_row+1}").number_format = CURRENCY_FORMAT
    ws_conciliation.cell(row=row, column=3, value="Monto que debería haber en caja")
    expected_row = row
    row += 2
    
    ws_conciliation.cell(row=row, column=1, value="(-) Monto Real (Cierres):").font = Font(bold=True)
    ws_conciliation.cell(row=row, column=2, value=float(total_closing_amount)).number_format = CURRENCY_FORMAT
    ws_conciliation.cell(row=row, column=3, value="Suma de todos los cierres de caja")
    actual_row = row
    row += 2
    
    # Diferencia con fórmula
    ws_conciliation.cell(row=row, column=1, value="DIFERENCIA (Real - Esperado):").font = Font(bold=True, size=11)
    diff_cell = ws_conciliation.cell(row=row, column=2, value=f"=B{actual_row}-B{expected_row}")
    diff_cell.number_format = CURRENCY_FORMAT
    diff_cell.font = Font(bold=True, size=11)
    
    # Resultado interpretativo con fórmula condicional
    row += 1
    ws_conciliation.cell(row=row, column=1, value="Interpretación:").font = Font(bold=True)
    # Nota: Excel no soporta emojis en fórmulas SI(), así que usamos texto
    expected_total = total_opening_amount + cash_from_sales
    actual_difference = Decimal(str(total_closing_amount)) - Decimal(str(expected_total))
    
    if actual_difference > 0:
        ws_conciliation.cell(row=row, column=2, value="SOBRANTE en caja").font = Font(bold=True, color="16A34A")
        ws_conciliation.cell(row=row, column=2).fill = POSITIVE_FILL
        ws_conciliation.cell(row=row, column=3, value="Hay más dinero del esperado. Verificar si hubo ingresos no registrados.")
    elif actual_difference < 0:
        ws_conciliation.cell(row=row, column=2, value="FALTANTE en caja").font = Font(bold=True, color="DC2626")
        ws_conciliation.cell(row=row, column=2).fill = NEGATIVE_FILL
        ws_conciliation.cell(row=row, column=3, value="Falta dinero. Revisar gastos no registrados o errores en cobro.")
    else:
        ws_conciliation.cell(row=row, column=2, value="CAJA CUADRADA").font = Font(bold=True, color="4F46E5")
        ws_conciliation.cell(row=row, column=2).fill = POSITIVE_FILL
        ws_conciliation.cell(row=row, column=3, value="El efectivo real coincide con el esperado. ¡Excelente!")
    
    _add_notes_section(ws_conciliation, row, [
        "Monto Inicial: Efectivo con el que se abrió caja cada día.",
        "Ingresos en Efectivo: Ventas cobradas en efectivo (no incluye tarjetas, transferencias, etc.).",
        "Efectivo Esperado = Monto Inicial + Ingresos en Efectivo.",
        "Diferencia = Monto Real de Cierre - Efectivo Esperado.",
        "Diferencia positiva (Sobrante): Puede indicar ingresos no registrados.",
        "Diferencia negativa (Faltante): Puede indicar gastos no registrados o errores.",
    ], columns=4)
    
    _auto_adjust_columns(ws_conciliation)
    
    # Guardar
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
