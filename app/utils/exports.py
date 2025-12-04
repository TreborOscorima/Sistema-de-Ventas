"""
Excel export utilities.

Functions to simplify Excel file creation and formatting.
"""
import openpyxl
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from typing import Any


# Default styles for Excel exports
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def create_excel_workbook(title: str) -> tuple[Workbook, Worksheet]:
    """
    Create a new Excel workbook with a named sheet.
    
    Args:
        title: The title for the active sheet
        
    Returns:
        Tuple of (workbook, active_worksheet)
    """
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = title[:31]  # Excel sheet names max 31 chars
    return workbook, sheet


def style_header_row(ws: Worksheet, row: int, columns: list[str]) -> None:
    """
    Add styled headers to a worksheet row.
    
    Args:
        ws: The worksheet to modify
        row: Row number (1-indexed)
        columns: List of column header texts
    """
    for col_idx, header in enumerate(columns, start=1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER


def add_data_rows(
    ws: Worksheet,
    data: list[list[Any]],
    start_row: int,
    apply_border: bool = True,
) -> int:
    """
    Add multiple rows of data to a worksheet.
    
    Args:
        ws: The worksheet to modify
        data: List of row data (each row is a list of values)
        start_row: Starting row number (1-indexed)
        apply_border: Whether to apply borders to cells
        
    Returns:
        The row number after the last data row
    """
    current_row = start_row
    for row_data in data:
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=value)
            if apply_border:
                cell.border = THIN_BORDER
        current_row += 1
    return current_row


def add_simple_headers(ws: Worksheet, headers: list[str]) -> None:
    """
    Add simple headers to the first row of a worksheet (no styling).
    
    Args:
        ws: The worksheet to modify
        headers: List of header texts
    """
    ws.append(headers)


def auto_adjust_column_widths(ws: Worksheet, min_width: int = 10, max_width: int = 50) -> None:
    """
    Auto-adjust column widths based on content.
    
    Args:
        ws: The worksheet to modify
        min_width: Minimum column width
        max_width: Maximum column width
    """
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        if adjusted_width < min_width:
            adjusted_width = min_width
        if adjusted_width > max_width:
            adjusted_width = max_width
        ws.column_dimensions[column_letter].width = adjusted_width
