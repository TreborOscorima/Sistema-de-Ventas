"""Servicio de Ventas - Lógica de negocio principal.

Este módulo contiene la lógica central para procesar ventas,
incluyendo:

- Validación de stock y productos
- Cálculo de totales y redondeo monetario
- Procesamiento de pagos (efectivo, tarjeta, billetera, mixto)
- Ventas a crédito con plan de cuotas
- Integración con reservas de canchas
- Registro en caja (CashboxLog) y movimientos de stock

Clases principales:
    SaleService: Servicio estático con el método principal `process_sale`
    SaleProcessResult: Dataclass con el resultado de una venta procesada
    StockError: Excepción específica para errores de inventario

Ejemplo de uso::

    from app.services.sale_service import SaleService, StockError
    
    async with get_async_session() as session:
        try:
            result = await SaleService.process_sale(
                session=session,
                user_id=1,
                items=[...],
                payment_data=payment_info,
            )
            await session.commit()
        except StockError as e:
            await session.rollback()
            # Manejar error de stock
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from sqlmodel import select
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession  # ✅ IMPORTANTE

from app.enums import PaymentMethodType, ReservationStatus, SaleStatus
from app.models import (
    CashboxLog,
    Client,
    FieldReservation,
    PaymentMethod,
    Product,
    Sale,
    SaleInstallment,
    SaleItem,
    SalePayment,
    Unit,
)
from app.schemas.sale_schemas import PaymentInfoDTO, SaleItemDTO
from app.utils.calculations import calculate_subtotal, calculate_total
from app.utils.logger import get_logger

# NOTA: Ya no importamos get_async_session aquí porque la sesión viene desde fuera

QTY_DECIMAL_QUANT = Decimal("0.0001")
QTY_DISPLAY_QUANT = Decimal("0.01")
QTY_INTEGER_QUANT = Decimal("1")

logger = get_logger("SaleService")


class StockError(ValueError):
    """Excepción para errores relacionados con inventario.
    
    Se lanza cuando:
    - El producto no existe en inventario
    - El stock es insuficiente para la cantidad solicitada
    - Hay ambigüedad en la descripción del producto
    
    Attributes:
        args: Mensaje descriptivo del error
    """
    pass


@dataclass
class SaleProcessResult:
    """Resultado de una venta procesada exitosamente.
    
    Contiene toda la información necesaria para generar el recibo
    y actualizar la UI después de procesar una venta.
    
    Attributes:
        sale: Objeto Sale persistido en base de datos
        receipt_items: Lista de items formateados para el recibo
            Cada item contiene: description, quantity, unit, price, subtotal
        sale_total: Total de la venta en Decimal (precisión completa)
        sale_total_display: Total redondeado para mostrar (float)
        timestamp: Fecha/hora de la transacción
        payment_summary: Resumen del pago para mostrar en recibo
            Ej: "Efectivo S/ 50.00" o "Mixto: Efectivo + Yape"
        reservation_context: Datos de reserva si aplica, None si es venta directa
        reservation_balance: Saldo pendiente de reserva cobrado
        reservation_balance_display: Saldo de reserva formateado (float)
    """
    sale: Sale
    receipt_items: List[Dict[str, Any]]
    sale_total: Decimal
    sale_total_display: float
    timestamp: datetime.datetime
    payment_summary: str
    reservation_context: Dict[str, Any] | None
    reservation_balance: Decimal
    reservation_balance_display: float


def _to_decimal(value: Any) -> Decimal:
    """Convierte cualquier valor numérico a Decimal.
    
    Args:
        value: Valor a convertir (int, float, str, None)
        
    Returns:
        Decimal del valor, o Decimal(0) si es None/vacío
    """
    return Decimal(str(value or 0))


def _round_money(value: Any) -> Decimal:
    """Redondea un valor monetario a 2 decimales.
    
    Usa ROUND_HALF_UP para consistencia contable.
    
    Args:
        value: Monto a redondear
        
    Returns:
        Decimal redondeado a centavos (0.01)
    """
    return calculate_total([{"subtotal": value}], key="subtotal")


def _round_quantity(value: Any, allows_decimal: bool, display: bool = False) -> Decimal:
    if allows_decimal:
        quant = QTY_DISPLAY_QUANT if display else QTY_DECIMAL_QUANT
    else:
        quant = QTY_INTEGER_QUANT
    return _to_decimal(value).quantize(quant, rounding=ROUND_HALF_UP)


def _quantity_for_receipt(value: Any, allows_decimal: bool) -> float | int:
    rounded = _round_quantity(value, allows_decimal, display=True)
    if allows_decimal:
        return float(rounded)
    return int(rounded)


def _money_to_float(value: Decimal) -> float:
    return float(_round_money(value))


def _money_display(value: Decimal) -> str:
    return f"S/ {float(_round_money(value)):.2f}"


def _reservation_status_value(status: Any) -> str:
    if isinstance(status, ReservationStatus):
        return status.value
    return str(status or "").strip().lower()


def _method_type_from_kind(kind: str) -> PaymentMethodType:
    normalized = (kind or "").strip().lower()
    if normalized == "cash":
        return PaymentMethodType.cash
    if normalized == "debit":
        return PaymentMethodType.debit
    if normalized == "credit":
        return PaymentMethodType.credit
    if normalized == "yape":
        return PaymentMethodType.yape
    if normalized == "plin":
        return PaymentMethodType.plin
    if normalized == "transfer":
        return PaymentMethodType.transfer
    if normalized == "mixed":
        return PaymentMethodType.mixed
    if normalized == "card":
        return PaymentMethodType.credit
    if normalized == "wallet":
        return PaymentMethodType.yape
    return PaymentMethodType.other


def _card_method_type(card_type: str) -> PaymentMethodType:
    value = (card_type or "").strip().lower()
    if "deb" in value:
        return PaymentMethodType.debit
    return PaymentMethodType.credit


def _wallet_method_type(provider: str) -> PaymentMethodType:
    value = (provider or "").strip().lower()
    if "plin" in value:
        return PaymentMethodType.plin
    return PaymentMethodType.yape


def _allocate_mixed_payments(
    sale_total: Decimal,
    cash_amount: Decimal,
    card_amount: Decimal,
    wallet_amount: Decimal,
    card_type: PaymentMethodType,
    wallet_type: PaymentMethodType,
) -> list[tuple[PaymentMethodType, Decimal]]:
    remaining = _round_money(sale_total)
    allocations: list[tuple[PaymentMethodType, Decimal]] = []

    def apply(amount: Decimal, method_type: PaymentMethodType) -> None:
        nonlocal remaining
        amount = _round_money(amount)
        if amount <= 0 or remaining <= 0:
            return
        applied = min(amount, remaining)
        allocations.append((method_type, _round_money(applied)))
        remaining = _round_money(remaining - applied)

    apply(card_amount, card_type)
    apply(wallet_amount, wallet_type)
    apply(cash_amount, PaymentMethodType.cash)

    if remaining > 0:
        if allocations:
            method_type, amount = allocations[0]
            allocations[0] = (method_type, _round_money(amount + remaining))
        else:
            allocations.append((PaymentMethodType.other, _round_money(sale_total)))

    return allocations


def _build_sale_payments(
    payment_data: PaymentInfoDTO,
    sale_total: Decimal,
) -> list[tuple[PaymentMethodType, Decimal]]:
    kind = (payment_data.method_kind or "other").strip().lower()
    if kind == "mixed":
        non_cash_kind = (payment_data.mixed.non_cash_kind or "").strip().lower()
        card_type = _card_method_type(payment_data.card.type)
        wallet_type = _wallet_method_type(
            payment_data.wallet.provider or payment_data.wallet.choice
        )
        if non_cash_kind in {"debit", "credit", "transfer"}:
            card_type = _method_type_from_kind(non_cash_kind)
        elif non_cash_kind in {"yape", "plin"}:
            wallet_type = _method_type_from_kind(non_cash_kind)
        return _allocate_mixed_payments(
            sale_total,
            _to_decimal(payment_data.mixed.cash),
            _to_decimal(payment_data.mixed.card),
            _to_decimal(payment_data.mixed.wallet),
            card_type,
            wallet_type,
        )
    if kind == "card":
        method_type = _card_method_type(payment_data.card.type)
    elif kind == "wallet":
        method_type = _wallet_method_type(
            payment_data.wallet.provider or payment_data.wallet.choice
        )
    else:
        method_type = _method_type_from_kind(kind)
    if method_type == PaymentMethodType.cash:
        amount = min(_to_decimal(payment_data.cash.amount), sale_total)
    else:
        amount = sale_total
    return [(method_type, _round_money(amount))]


def _payment_method_code(method_type: PaymentMethodType) -> str | None:
    if method_type == PaymentMethodType.cash:
        return "cash"
    if method_type == PaymentMethodType.yape:
        return "yape"
    if method_type == PaymentMethodType.plin:
        return "plin"
    if method_type == PaymentMethodType.transfer:
        return "transfer"
    if method_type == PaymentMethodType.debit:
        return "debit_card"
    if method_type == PaymentMethodType.credit:
        return "credit_card"
    return None


def _split_installments(total: Decimal, count: int) -> list[Decimal]:
    """Divide un monto total en cuotas iguales.
    
    Distribuye cualquier diferencia por redondeo en las primeras cuotas
    para garantizar que la suma exacta sea igual al total.
    
    Args:
        total: Monto total a dividir
        count: Número de cuotas
        
    Returns:
        Lista de montos por cuota (Decimal)
        
    Example:
        >>> _split_installments(Decimal("100.00"), 3)
        [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    """
    total = _round_money(total)
    if count <= 0:
        return []
    quant = Decimal("0.01")
    base = (total / count).quantize(quant, rounding=ROUND_HALF_UP)
    amounts = [base for _ in range(count)]
    distributed = (base * count).quantize(quant, rounding=ROUND_HALF_UP)
    remainder = (total - distributed).quantize(quant, rounding=ROUND_HALF_UP)
    if remainder != 0:
        step = quant if remainder > 0 else -quant
        steps = int(abs(remainder / quant))
        for i in range(steps):
            amounts[i] = (amounts[i] + step).quantize(
                quant, rounding=ROUND_HALF_UP
            )
    return amounts


class SaleService:
    """Servicio para procesamiento de ventas.
    
    Proporciona métodos estáticos para procesar ventas completas,
    incluyendo validación, descuento de stock, registro de pagos
    y generación de datos para recibos.
    
    Todos los métodos son asíncronos y requieren una sesión de BD.
    """
    
    @staticmethod
    async def process_sale(
        session: AsyncSession,
        user_id: int | None,
        items: list[SaleItemDTO],
        payment_data: PaymentInfoDTO,
        reservation_id: str | None = None,
    ) -> SaleProcessResult:
        """Procesa una venta completa de forma atómica.
        
        Este es el método principal del servicio. Realiza todas las
        validaciones y operaciones necesarias para completar una venta:
        
        1. Valida método de pago seleccionado
        2. Verifica reserva asociada (si aplica)
        3. Valida existencia y stock de productos
        4. Bloquea productos para evitar race conditions
        5. Calcula totales con precisión decimal
        6. Crea registro de venta (Sale)
        7. Crea items de venta (SaleItem)
        8. Registra pagos (SalePayment)
        9. Descuenta stock y registra movimientos
        10. Crea registro en caja (CashboxLog)
        11. Para créditos: crea plan de cuotas (SaleInstallment)
        
        Args:
            session: Sesión async de SQLAlchemy (debe manejarse externamente)
            user_id: ID del usuario que realiza la venta (puede ser None)
            items: Lista de productos a vender (SaleItemDTO)
            payment_data: Información de pago (PaymentInfoDTO)
            reservation_id: ID de reserva asociada (opcional)
            
        Returns:
            SaleProcessResult con todos los datos de la venta procesada
            
        Raises:
            ValueError: Para errores de validación (pago, cliente, montos)
            StockError: Para errores de inventario (stock insuficiente, producto no encontrado)
            
        Note:
            El commit/rollback debe manejarse externamente.
            En caso de error, se recomienda hacer rollback de la sesión.
            
        Example::
        
            result = await SaleService.process_sale(
                session=session,
                user_id=current_user.id,
                items=[SaleItemDTO(description="Producto", quantity=2, price=10.0, unit="Unidad")],
                payment_data=PaymentInfoDTO(method="Efectivo", method_kind="cash"),
            )
            await session.commit()
            print(f"Venta #{result.sale.id} - Total: {result.sale_total_display}")
        """
        payment_method = (payment_data.method or "").strip()
        if not payment_method:
            raise ValueError("Seleccione un metodo de pago.")

        all_methods = (await session.exec(select(PaymentMethod))).all()
        methods_map = {
            (method.code or "").strip().lower(): method.id
            for method in all_methods
            if method.code
        }

        def resolve_payment_method_id(code: str | None) -> int | None:
            if not code:
                return None
            return methods_map.get(code.strip().lower())

        # --- AQUI EMPIEZA LA LÓGICA DE NEGOCIO ---
        # Ya no usamos 'async with get_async_session()' porque 'session' ya llegó como argumento.

        reservation = None
        reservation_balance = Decimal("0.00")
        if reservation_id:
            reservation = (
                await session.exec(
                    select(FieldReservation).where(
                        FieldReservation.id == reservation_id
                    )
                )
            ).first()
            if reservation:
                status_value = _reservation_status_value(reservation.status)
                if status_value in {
                    ReservationStatus.cancelled.value,
                    ReservationStatus.refunded.value,
                    "cancelado",
                    "eliminado",
                }:
                    raise ValueError(
                        "No se puede cobrar una reserva cancelada o eliminada."
                    )
            if reservation:
                raw_balance = reservation.total_amount - reservation.paid_amount
                if raw_balance < 0:
                    raw_balance = Decimal("0.00")
                reservation_balance = _round_money(raw_balance)

        if not items and reservation_balance <= Decimal("0.00"):
            if reservation:
                raise ValueError("La reserva ya esta pagada.")
            raise ValueError("No hay productos en la venta.")

        units = (await session.exec(select(Unit))).all()
        decimal_units = {
            u.name.strip().lower(): u.allows_decimal for u in units
        }

        product_snapshot: list[Dict[str, Any]] = []
        decimal_snapshot: list[Dict[str, Any]] = []
        for item in items:
            description = (item.description or "").strip()
            if not description:
                raise ValueError("Producto sin descripcion.")
            unit = (item.unit or "").strip()
            allows_decimal = decimal_units.get(unit.lower(), False)
            quantity_receipt = _quantity_for_receipt(
                item.quantity, allows_decimal
            )
            quantity_db = _round_quantity(item.quantity, allows_decimal)
            price = _round_money(item.price)
            if quantity_db <= 0 or price <= 0:
                raise ValueError(
                    f"Cantidad o precio invalido para {description}."
                )
            subtotal = calculate_subtotal(quantity_db, price)
            product_snapshot.append(
                {
                    "description": description,
                    "quantity": quantity_receipt,
                    "unit": unit,
                    "price": _money_to_float(price),
                    "subtotal": _money_to_float(subtotal),
                }
            )
            decimal_snapshot.append(
                {
                    "description": description,
                    "quantity": quantity_db,
                    "unit": unit,
                    "price": price,
                    "subtotal": subtotal,
                    "barcode": item.barcode or "",
                }
            )

        descriptions: list[str] = []
        barcodes: list[str] = []
        for item in decimal_snapshot:
            description = (item.get("description") or "").strip()
            if description:
                descriptions.append(description)
            barcode = (item.get("barcode") or "").strip()
            if barcode:
                barcodes.append(barcode)

        unique_descriptions = list(dict.fromkeys(descriptions))
        unique_barcodes = list(dict.fromkeys(barcodes))
        products_by_description: dict[str, Product] = {}
        products_by_barcode: dict[str, Product] = {}
        ambiguous_descriptions: set[str] = set()
        filters = []
        if unique_barcodes:
            filters.append(Product.barcode.in_(unique_barcodes))
        if unique_descriptions:
            filters.append(Product.description.in_(unique_descriptions))
        if filters:
            if len(filters) == 1:
                query = select(Product).where(filters[0])
            else:
                query = select(Product).where(or_(*filters))
            products = (await session.exec(query.with_for_update())).all()
            for product in products:
                description = (product.description or "").strip()
                if not description:
                    continue
                if description in products_by_description:
                    ambiguous_descriptions.add(description)
                    continue
                products_by_description[description] = product
            for description in ambiguous_descriptions:
                products_by_description.pop(description, None)
            products_by_barcode = {
                product.barcode: product
                for product in products
                if product.barcode
            }

        locked_products: list[tuple[Dict[str, Any], Product]] = []
        for item in decimal_snapshot:
            barcode = (item.get("barcode") or "").strip()
            product = None
            if barcode:
                product = products_by_barcode.get(barcode)
            if not product:
                description = item.get("description", "")
                if description in ambiguous_descriptions:
                    raise StockError(
                        f"Producto '{description}' tiene multiples coincidencias en inventario. "
                        "Use codigo de barras."
                    )
                product = products_by_description.get(description)
            if not product:
                if barcode:
                    raise StockError(
                        f"Producto con codigo {barcode} no encontrado en inventario."
                    )
                raise StockError(
                    f"Producto {item['description']} no encontrado en inventario."
                )
            if product.stock < item["quantity"]:
                raise StockError(
                    f"Stock insuficiente para {item['description']}."
                )
            locked_products.append((item, product))

        items_total = calculate_total(decimal_snapshot)
        sale_total = _round_money(items_total + reservation_balance)
        if sale_total <= Decimal("0.00"):
            raise ValueError("No hay importe para cobrar.")

        is_credit = bool(payment_data.is_credit)
        initial_payment = _round_money(payment_data.initial_payment)
        if initial_payment < 0:
            raise ValueError("Monto inicial invalido.")
        initial_payment_input = initial_payment

        kind = (payment_data.method_kind or "other").strip().lower()
        total_paid_now = Decimal("0.00")
        if kind == "cash":
            cash_amount = _to_decimal(payment_data.cash.amount)
            total_paid_now = _round_money(cash_amount)
            if not is_credit:
                if cash_amount <= 0 or cash_amount < sale_total:
                    message = (
                        payment_data.cash.message
                        or "Ingrese un monto valido en efectivo."
                    )
                    raise ValueError(message)
            elif cash_amount < 0:
                message = (
                    payment_data.cash.message
                    or "Ingrese un monto valido en efectivo."
                )
                raise ValueError(message)
        elif kind == "mixed":
            total_paid_now = _round_money(
                _to_decimal(payment_data.mixed.cash)
                + _to_decimal(payment_data.mixed.card)
                + _to_decimal(payment_data.mixed.wallet)
            )
            if not is_credit:
                if total_paid_now <= 0 or total_paid_now < sale_total:
                    message = (
                        payment_data.mixed.message
                        or "Complete los montos del pago mixto."
                    )
                    raise ValueError(message)
            elif total_paid_now < 0:
                message = (
                    payment_data.mixed.message
                    or "Complete los montos del pago mixto."
                )
                raise ValueError(message)
        else:
            if is_credit:
                total_paid_now = _round_money(initial_payment)
            else:
                total_paid_now = sale_total

        if (
            is_credit
            and initial_payment_input > Decimal("0.00")
            and total_paid_now <= Decimal("0.00")
        ):
            total_paid_now = initial_payment_input

        if is_credit and kind in {"cash", "mixed"} and initial_payment_input <= Decimal(
            "0.00"
        ):
            initial_payment = total_paid_now

        sale_payment_label = payment_method
        if is_credit:
            sale_payment_label = (
                "Crédito c/ Inicial"
                if initial_payment > Decimal("0.00")
                else "Crédito"
            )

        client = None
        installments_plan: list[tuple[datetime.datetime, Decimal]] = []
        financed_amount = Decimal("0.00")
        if is_credit:
            if payment_data.client_id is None:
                raise ValueError("Cliente requerido para venta a credito.")
            client = await session.get(Client, payment_data.client_id)
            if not client:
                raise ValueError("Cliente no encontrado.")
            credit_base = _round_money(sale_total - initial_payment)
            if credit_base < Decimal("0.00"):
                credit_base = Decimal("0.00")
            if _round_money(client.current_debt) + credit_base > _round_money(
                client.credit_limit
            ):
                raise ValueError("Limite de credito excedido.")

        try:
            timestamp = datetime.datetime.now()
            sale_total_display = _money_to_float(sale_total)
    
            new_sale = Sale(
                timestamp=timestamp,
                total_amount=sale_total,
                status=SaleStatus.completed,
                user_id=user_id,
            )
            if hasattr(Sale, "payment_method"):
                new_sale.payment_method = sale_payment_label
            if is_credit:
                new_sale.payment_condition = "credito"
                new_sale.client_id = client.id
            session.add(new_sale)
            await session.flush()
            await session.refresh(new_sale)
    
            paid_now_total = sale_total
            if is_credit:
                paid_now_total = total_paid_now
    
            payment_allocations = _build_sale_payments(payment_data, paid_now_total)
            valid_allocations = [
                (method_type, amount)
                for method_type, amount in payment_allocations
                if amount > 0
            ]
            for method_type, amount in valid_allocations:
                method_code = _payment_method_code(method_type)
                method_id = resolve_payment_method_id(method_code)
                session.add(
                    SalePayment(
                        sale_id=new_sale.id,
                        amount=amount,
                        method_type=method_type,
                        reference_code=None,
                        payment_method_id=method_id,
                        created_at=timestamp,
                    )
                )
    
            cashbox_amount = paid_now_total
            if is_credit and initial_payment_input > Decimal("0.00"):
                cashbox_amount = initial_payment_input
    
            if cashbox_amount > 0:
                cashbox_method_id = None
                main_payment_code = None
                if kind == "cash":
                    main_payment_code = "cash"
                elif kind == "card":
                    card_type = _card_method_type(payment_data.card.type)
                    main_payment_code = _payment_method_code(card_type)
                elif kind == "wallet":
                    wallet_type = _wallet_method_type(
                        payment_data.wallet.provider or payment_data.wallet.choice
                    )
                    main_payment_code = _payment_method_code(wallet_type)
                elif kind == "mixed":
                    if valid_allocations:
                        primary_method_type, _ = max(
                            valid_allocations, key=lambda item: item[1]
                        )
                        main_payment_code = _payment_method_code(primary_method_type)
                else:
                    main_payment_code = _payment_method_code(
                        _method_type_from_kind(kind)
                    )
                cashbox_method_id = resolve_payment_method_id(main_payment_code)
                action_label = "Venta"
                summary_items: list[str] = []
                if reservation is not None:
                    field_name = (reservation.field_name or "").strip()
                    if field_name:
                        summary_items.append(f"Alquiler {field_name}")
                    else:
                        summary_items.append("Alquiler")
                for item in decimal_snapshot:
                    description = (item.get("description") or "").strip()
                    if not description:
                        continue
                    qty_value = _to_decimal(item.get("quantity", 0))
                    if qty_value == qty_value.to_integral_value():
                        qty_display = str(int(qty_value))
                    else:
                        qty_display = format(qty_value.normalize(), "f").rstrip("0").rstrip(".")
                    summary_items.append(f"{description} (x{qty_display})")
                summary_text = ", ".join(summary_items)
                notes = f"#{new_sale.id}: {summary_text}"
                if is_credit:
                    action_label = "Inicial Credito"
                    client_name = ""
                    if client:
                        client_name = (client.name or "").strip() or f"ID {client.id}"
                    notes = f"Inicial #{new_sale.id} ({summary_text})"
                    if client_name:
                        notes = f"{notes} - Cliente {client_name}"
                if len(notes) > 250:
                    notes = notes[:250]
                session.add(
                    CashboxLog(
                        action=action_label,
                        amount=cashbox_amount,
                        payment_method=payment_method,
                        payment_method_id=cashbox_method_id,
                        notes=notes,
                        timestamp=timestamp,
                        user_id=user_id,
                        sale_id=new_sale.id,
                    )
                )
    
            if is_credit:
                financed_amount = _round_money(sale_total - total_paid_now)
                if financed_amount < Decimal("0.00"):
                    financed_amount = Decimal("0.00")
                if financed_amount > 0:
                    installments_count = int(payment_data.installments or 1)
                    if installments_count < 1:
                        raise ValueError("Cantidad de cuotas invalida.")
                    interval_days = int(payment_data.interval_days or 0)
                    if interval_days <= 0:
                        interval_days = 30
                    for number, amount in enumerate(
                        _split_installments(financed_amount, installments_count),
                        start=1,
                    ):
                        due_date = timestamp + datetime.timedelta(
                            days=interval_days * number
                        )
                        installments_plan.append((due_date, amount))
                        session.add(
                            SaleInstallment(
                                sale_id=new_sale.id,
                                number=number,
                                amount=amount,
                                due_date=due_date,
                                status="pending",
                                paid_amount=Decimal("0.00"),
                                payment_date=None,
                            )
                        )
                    client.current_debt = _round_money(
                        client.current_debt + financed_amount
                    )
                    session.add(client)
    
            for item, product in locked_products:
                allows_decimal = decimal_units.get(
                    (product.unit or "").strip().lower(), False
                )
                scale = 4 if allows_decimal else 0
                product.stock = func.round(
                    Product.stock - item["quantity"], scale
                )
                session.add(product)
    
                sale_item = SaleItem(
                    sale_id=new_sale.id,
                    product_id=product.id,
                    quantity=item["quantity"],
                    unit_price=item["price"],
                    subtotal=item["subtotal"],
                    product_name_snapshot=product.description,
                    product_barcode_snapshot=product.barcode,
                    product_category_snapshot=product.category or "General",
                )
                session.add(sale_item)
    
            reservation_context = None
            reservation_balance_display = _money_to_float(reservation_balance)
            if reservation and reservation_balance > Decimal("0.00"):
                applied_amount = reservation_balance
                paid_before = reservation.paid_amount
                reservation.paid_amount = _round_money(
                    reservation.paid_amount + applied_amount
                )
                if reservation.paid_amount >= reservation.total_amount:
                    reservation.status = ReservationStatus.paid
                session.add(reservation)
    
                res_item = SaleItem(
                    sale_id=new_sale.id,
                    product_id=None,
                    quantity=Decimal("1.0000"),
                    unit_price=applied_amount,
                    subtotal=applied_amount,
                    product_name_snapshot=(
                        f"Alquiler {reservation.field_name} "
                        f"({reservation.start_datetime} - {reservation.end_datetime})"
                    ),
                    product_barcode_snapshot=str(reservation.id),
                    product_category_snapshot="Servicios",
                )
                session.add(res_item)
    
                balance_after = reservation.total_amount - reservation.paid_amount
                if balance_after < 0:
                    balance_after = Decimal("0.00")
                reservation_context = {
                    "total": _money_to_float(reservation.total_amount),
                    "paid_before": _money_to_float(paid_before),
                    "paid_now": _money_to_float(applied_amount),
                    "paid_after": _money_to_float(reservation.paid_amount),
                    "balance_after": _money_to_float(balance_after),
                    "header": (
                        f"Alquiler {reservation.field_name} "
                        f"({reservation.start_datetime} - {reservation.end_datetime})"
                    ),
                    "products_total": _money_to_float(items_total),
                    "charged_total": sale_total_display,
                }
    
            receipt_items = list(product_snapshot)
            if reservation and reservation_balance > Decimal("0.00"):
                receipt_items.insert(
                    0,
                    {
                        "description": f"Alquiler {reservation.field_name}",
                        "quantity": 1,
                        "unit": "Servicio",
                        "price": reservation_balance_display,
                        "subtotal": reservation_balance_display,
                    },
                )
    
            payment_summary = payment_data.summary or payment_method
            if is_credit:
                credit_lines = [
                    "CONDICION: CREDITO",
                    f"Pago Inicial: {_money_display(_round_money(initial_payment))}",
                    f"Saldo a Financiar: {_money_display(_round_money(financed_amount))}",
                    "Plan de Pagos:",
                ]
                if installments_plan:
                    for due_date, amount in installments_plan:
                        credit_lines.append(
                            f"- {due_date.strftime('%Y-%m-%d')}: {_money_display(amount)}"
                        )
                credit_lines.append("_____________________")
                credit_block = "\n".join(credit_lines)
                if payment_summary:
                    payment_summary = f"{payment_summary}\n{credit_block}"
                else:
                    payment_summary = credit_block
    
            await session.commit()
            return SaleProcessResult(
                sale=new_sale,
                receipt_items=receipt_items,
                sale_total=sale_total,
                sale_total_display=sale_total_display,
                timestamp=timestamp,
                payment_summary=payment_summary,
                reservation_context=reservation_context,
                reservation_balance=reservation_balance,
                reservation_balance_display=reservation_balance_display,
            )
        except Exception as e:
            await session.rollback()
            logger.error("Transacción fallida. Rollback ejecutado.", exc_info=True)
            raise e
