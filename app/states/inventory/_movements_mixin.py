"""Mixin de historial de movimientos de stock."""
from __future__ import annotations

import io
from datetime import datetime, date
from typing import Any

import reflex as rx
from sqlmodel import select
from sqlalchemy import func

from app.models import StockMovement, Product
from app.models.auth import User
from app.utils.exports import (
    create_excel_workbook,
    style_header_row,
    auto_adjust_column_widths,
    add_company_header,
    THIN_BORDER,
    POSITIVE_FILL,
    NEGATIVE_FILL,
    WARNING_FILL,
)


class MovementsMixin:
    """Historial paginado y exportable de movimientos de stock."""

    # ── State vars ────────────────────────────────────────────────
    movements_list: list[dict] = []
    movements_total_pages: int = 1
    movements_current_page: int = 1
    movements_items_per_page: int = 25
    movements_type_filter: str = ""
    movements_date_from: str = ""
    movements_date_to: str = ""
    movements_search: str = ""
    movements_section_open: bool = False
    movements_total_count: int = 0

    # ── Toggle sección ────────────────────────────────────────────

    @rx.event
    def toggle_movements_section(self):
        self.movements_section_open = not self.movements_section_open
        if self.movements_section_open and not self.movements_list:
            return self.load_movements()

    # ── Filtros ───────────────────────────────────────────────────

    @rx.event
    def set_movements_type_filter(self, value: str):
        self.movements_type_filter = value
        self.movements_current_page = 1
        return self.load_movements()

    @rx.event
    def set_movements_date_from(self, value: str):
        self.movements_date_from = value
        self.movements_current_page = 1
        return self.load_movements()

    @rx.event
    def set_movements_date_to(self, value: str):
        self.movements_date_to = value
        self.movements_current_page = 1
        return self.load_movements()

    @rx.event
    def set_movements_search(self, value: str):
        self.movements_search = value
        self.movements_current_page = 1
        return self.load_movements()

    @rx.event
    def set_movements_page(self, page: int):
        total = self.movements_total_pages
        if page < 1:
            page = 1
        if page > total:
            page = total
        self.movements_current_page = page
        return self.load_movements()

    @rx.event
    def clear_movements_filters(self):
        self.movements_type_filter = ""
        self.movements_date_from = ""
        self.movements_date_to = ""
        self.movements_search = ""
        self.movements_current_page = 1
        return self.load_movements()

    # ── Carga de datos ────────────────────────────────────────────

    @rx.event
    def load_movements(self):
        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return

        per_page = int(self.movements_items_per_page)
        page = int(self.movements_current_page)
        offset = (page - 1) * per_page

        type_filter = self.movements_type_filter.strip()
        search = self.movements_search.strip().lower()
        date_from = self.movements_date_from.strip()
        date_to = self.movements_date_to.strip()

        with rx.session() as session:
            session.info["tenant_bypass"] = True

            # Query base
            stmt = (
                select(StockMovement, Product, User)
                .outerjoin(Product, StockMovement.product_id == Product.id)
                .outerjoin(User, StockMovement.user_id == User.id)
                .where(StockMovement.company_id == company_id)
                .where(StockMovement.branch_id == branch_id)
            )

            if type_filter:
                stmt = stmt.where(StockMovement.type == type_filter)

            if date_from:
                try:
                    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                    stmt = stmt.where(StockMovement.timestamp >= dt_from)
                except ValueError:
                    pass

            if date_to:
                try:
                    dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59
                    )
                    stmt = stmt.where(StockMovement.timestamp <= dt_to)
                except ValueError:
                    pass

            if search:
                stmt = stmt.where(
                    Product.description.ilike(f"%{search}%")
                    | Product.barcode.ilike(f"%{search}%")
                    | StockMovement.description.ilike(f"%{search}%")
                )

            # Total count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = session.exec(count_stmt).one() or 0

            # Paginated results
            rows = session.exec(
                stmt.order_by(StockMovement.timestamp.desc())
                .offset(offset)
                .limit(per_page)
            ).all()

        self.movements_total_count = total
        self.movements_total_pages = max(1, (total + per_page - 1) // per_page)

        tz_offset = getattr(self, "tz_offset_hours", 0) or 0

        result: list[dict] = []
        for movement, product, user in rows:
            ts = movement.timestamp
            if ts and tz_offset:
                from datetime import timedelta
                ts = ts + timedelta(hours=tz_offset)
            ts_str = ts.strftime("%d/%m/%Y %H:%M") if ts else "-"

            qty = float(movement.quantity or 0)
            qty_str = f"+{abs(qty):g}" if qty >= 0 else f"-{abs(qty):g}"

            ts_parts = ts_str.split(" ")
            result.append({
                "id": movement.id,
                "timestamp": ts_str,
                "timestamp_date": ts_parts[0] if len(ts_parts) > 0 else "-",
                "timestamp_time": ts_parts[1] if len(ts_parts) > 1 else "",
                "type": movement.type or "-",
                "quantity": qty_str,
                "quantity_positive": qty >= 0,
                "description": movement.description or "-",
                "product_name": product.description if product else "-",
                "product_barcode": product.barcode if product else "-",
                "username": user.username if user else "-",
            })

        self.movements_list = result

    # ── Exportación ───────────────────────────────────────────────

    @rx.event
    def export_movements_to_excel(self):
        if not self.current_user["privileges"].get("export_data", False):
            return rx.toast("No tiene permisos para exportar datos.", duration=3000)

        company_id = self._company_id()
        branch_id = self._branch_id()
        if not company_id or not branch_id:
            return rx.toast("Empresa no definida.", duration=3000)

        type_filter = self.movements_type_filter.strip()
        search = self.movements_search.strip().lower()
        date_from = self.movements_date_from.strip()
        date_to = self.movements_date_to.strip()

        with rx.session() as session:
            session.info["tenant_bypass"] = True

            stmt = (
                select(StockMovement, Product, User)
                .outerjoin(Product, StockMovement.product_id == Product.id)
                .outerjoin(User, StockMovement.user_id == User.id)
                .where(StockMovement.company_id == company_id)
                .where(StockMovement.branch_id == branch_id)
            )

            if type_filter:
                stmt = stmt.where(StockMovement.type == type_filter)

            if date_from:
                try:
                    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                    stmt = stmt.where(StockMovement.timestamp >= dt_from)
                except ValueError:
                    pass

            if date_to:
                try:
                    dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59
                    )
                    stmt = stmt.where(StockMovement.timestamp <= dt_to)
                except ValueError:
                    pass

            if search:
                stmt = stmt.where(
                    Product.description.ilike(f"%{search}%")
                    | Product.barcode.ilike(f"%{search}%")
                    | StockMovement.description.ilike(f"%{search}%")
                )

            rows = session.exec(
                stmt.order_by(StockMovement.timestamp.desc()).limit(5000)
            ).all()

        company_name = getattr(self, "company_name", "") or "EMPRESA"
        today_str = self._display_now().strftime("%d/%m/%Y")
        tz_offset = getattr(self, "tz_offset_hours", 0) or 0

        wb, ws = create_excel_workbook("Movimientos de Stock")

        subtitle = "HISTORIAL DE MOVIMIENTOS DE STOCK"
        if type_filter:
            subtitle += f" — Tipo: {type_filter}"
        if date_from or date_to:
            rng = f"{date_from or '...'} al {date_to or '...'}"
            subtitle += f" — Período: {rng}"

        row = add_company_header(
            ws,
            company_name,
            subtitle,
            f"Generado el {today_str}",
            columns=7,
            generated_at=self._display_now(),
        )

        headers = [
            "Fecha y Hora",
            "Tipo de Movimiento",
            "Producto",
            "Código de Barra",
            "Cantidad",
            "Usuario",
            "Descripción / Motivo",
        ]

        row += 1
        style_header_row(ws, row, headers)
        row += 1

        for movement, product, user in rows:
            ts = movement.timestamp
            if ts and tz_offset:
                from datetime import timedelta
                ts = ts + timedelta(hours=tz_offset)
            ts_str = ts.strftime("%d/%m/%Y %H:%M") if ts else "-"

            qty = float(movement.quantity or 0)
            qty_str = f"+{abs(qty):g}" if qty >= 0 else f"-{abs(qty):g}"

            ws.cell(row=row, column=1, value=ts_str)
            ws.cell(row=row, column=2, value=movement.type or "-")
            ws.cell(row=row, column=3, value=product.description if product else "-")
            ws.cell(row=row, column=4, value=product.barcode if product else "-")

            qty_cell = ws.cell(row=row, column=5, value=qty_str)
            if qty >= 0:
                qty_cell.fill = POSITIVE_FILL
            else:
                qty_cell.fill = NEGATIVE_FILL

            ws.cell(row=row, column=6, value=user.username if user else "-")
            ws.cell(row=row, column=7, value=movement.description or "-")

            for col in range(1, 8):
                ws.cell(row=row, column=col).border = THIN_BORDER

            row += 1

        auto_adjust_column_widths(ws)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        fname = f"movimientos_stock_{today_str.replace('/', '-')}.xlsx"
        return rx.download(data=output.getvalue(), filename=fname)
