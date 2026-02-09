from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import traceback
import sys

import bcrypt
import reflex as rx
from sqlmodel import select

# Permite ejecutar el script desde scripts/ sin instalar el paquete.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.enums import PaymentMethodType, ReservationStatus, SportType
from app.models import (
    Branch,
    CashboxLog,
    Company,
    FieldReservation,
    PaymentMethod,
    Product,
    Role,
    SaleItem,
    SalePayment,
    Unit,
    User,
    UserBranch,
)
from app.schemas.sale_schemas import PaymentCashDTO, PaymentInfoDTO, SaleItemDTO
from app.services.sale_service import SaleService
from app.states.auth_state import AuthState
from app.states.services_state import ServicesState
from app.utils.auth import decode_token
from app.utils.db import async_engine, get_async_session
from app.utils.tenant import set_tenant_context, tenant_bypass


MONEY_QUANT = Decimal("0.01")
STOCK_QUANT = Decimal("0.0001")


@dataclass
class SmokeContext:
    run_id: str
    company_a_id: int
    company_b_id: int
    branch_a_id: int
    branch_b_id: int
    user_a_id: int
    user_b_id: int
    user_a_email: str
    user_b_email: str
    user_a_username: str
    user_b_username: str
    user_a_password: str
    user_b_password: str
    product_id: int
    product_barcode: str
    product_sale_price: Decimal
    product_initial_stock: Decimal
    reservation_services_state_id: int
    reservation_sale_service_only_id: int
    reservation_combo_id: int


@dataclass
class FlowResult:
    name: str
    ok: bool
    details: str


def _money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _stock(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(STOCK_QUANT, rounding=ROUND_HALF_UP)


def _create_company_and_branch(
    session,
    run_id: str,
    suffix: str,
) -> tuple[Company, Branch]:
    company = Company(
        name=f"SMOKE-{suffix}-{run_id}",
        ruc=f"SMK{suffix}{run_id}",
        is_active=True,
    )
    session.add(company)
    session.flush()

    branch = Branch(
        company_id=company.id,
        name=f"Sucursal {suffix}",
        address="Smoke branch",
    )
    session.add(branch)
    session.flush()
    return company, branch


def _bootstrap_admin_user(
    session,
    auth_helper: AuthState,
    company_id: int,
    branch_id: int,
    username: str,
    email: str,
    raw_password: str,
) -> User:
    set_tenant_context(company_id, None)
    auth_helper._bootstrap_default_roles(session, company_id)
    role = auth_helper._get_role_by_name(session, "Superadmin", company_id=company_id)
    if role is None:
        raise RuntimeError("No se pudo bootstrapear rol Superadmin.")

    user = User(
        username=username,
        email=email,
        password_hash=bcrypt.hashpw(
            raw_password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8"),
        is_active=True,
        must_change_password=False,
        company_id=company_id,
        branch_id=branch_id,
        role_id=role.id,
    )
    session.add(user)
    session.flush()
    session.add(UserBranch(user_id=user.id, branch_id=branch_id))
    return user


def setup_smoke_data() -> SmokeContext:
    run_id = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    auth_helper = AuthState()
    user_a_password = f"Sm0ke-A-{run_id}!"
    user_b_password = f"Sm0ke-B-{run_id}!"

    with tenant_bypass():
        with rx.session() as session:
            company_a, branch_a = _create_company_and_branch(session, run_id, "A")
            company_b, branch_b = _create_company_and_branch(session, run_id, "B")

            user_a = _bootstrap_admin_user(
                session=session,
                auth_helper=auth_helper,
                company_id=company_a.id,
                branch_id=branch_a.id,
                username=f"smoke_admin_a_{run_id}",
                email=f"smoke_a_{run_id}@local.test",
                raw_password=user_a_password,
            )
            user_b = _bootstrap_admin_user(
                session=session,
                auth_helper=auth_helper,
                company_id=company_b.id,
                branch_id=branch_b.id,
                username=f"smoke_admin_b_{run_id}",
                email=f"smoke_b_{run_id}@local.test",
                raw_password=user_b_password,
            )

            unit = Unit(
                company_id=company_a.id,
                branch_id=branch_a.id,
                name="Unidad",
                allows_decimal=False,
            )
            session.add(unit)

            methods = [
                PaymentMethod(
                    company_id=company_a.id,
                    branch_id=branch_a.id,
                    name="Efectivo",
                    code="cash",
                    method_id=f"SMK-CASH-{run_id}",
                    kind=PaymentMethodType.CASH,
                    description="Smoke cash",
                    is_active=True,
                    enabled=True,
                    allows_change=True,
                ),
                PaymentMethod(
                    company_id=company_a.id,
                    branch_id=branch_a.id,
                    name="Tarjeta Debito",
                    code="debit_card",
                    method_id=f"SMK-DEBIT-{run_id}",
                    kind=PaymentMethodType.DEBIT,
                    description="Smoke debit",
                    is_active=True,
                    enabled=True,
                    allows_change=False,
                ),
                PaymentMethod(
                    company_id=company_a.id,
                    branch_id=branch_a.id,
                    name="Tarjeta Credito",
                    code="credit_card",
                    method_id=f"SMK-CREDIT-{run_id}",
                    kind=PaymentMethodType.CREDIT,
                    description="Smoke credit",
                    is_active=True,
                    enabled=True,
                    allows_change=False,
                ),
            ]
            for method in methods:
                session.add(method)

            product_initial_stock = _stock(100)
            product_sale_price = _money(15)
            product = Product(
                company_id=company_a.id,
                branch_id=branch_a.id,
                barcode=f"SMK-PROD-{run_id}",
                description=f"Producto Smoke {run_id}",
                category="Smoke",
                stock=product_initial_stock,
                unit="Unidad",
                purchase_price=_money(8),
                sale_price=product_sale_price,
            )
            session.add(product)
            session.flush()

            now = dt.datetime.now().replace(second=0, microsecond=0)
            reservation_services_state = FieldReservation(
                client_name=f"Cliente Smoke Servicios {run_id}",
                client_dni="10000001",
                client_phone="900000001",
                sport=SportType.FUTBOL,
                field_name="Cancha Smoke 1",
                start_datetime=now + dt.timedelta(hours=2),
                end_datetime=now + dt.timedelta(hours=3),
                total_amount=_money(120),
                paid_amount=_money(20),
                status=ReservationStatus.PENDING,
                user_id=user_a.id,
                company_id=company_a.id,
                branch_id=branch_a.id,
            )
            reservation_sale_service_only = FieldReservation(
                client_name=f"Cliente Smoke Venta Reserva {run_id}",
                client_dni="10000002",
                client_phone="900000002",
                sport=SportType.FUTBOL,
                field_name="Cancha Smoke 2",
                start_datetime=now + dt.timedelta(hours=4),
                end_datetime=now + dt.timedelta(hours=5),
                total_amount=_money(80),
                paid_amount=_money(0),
                status=ReservationStatus.PENDING,
                user_id=user_a.id,
                company_id=company_a.id,
                branch_id=branch_a.id,
            )
            reservation_combo = FieldReservation(
                client_name=f"Cliente Smoke Combo {run_id}",
                client_dni="10000003",
                client_phone="900000003",
                sport=SportType.FUTBOL,
                field_name="Cancha Smoke 3",
                start_datetime=now + dt.timedelta(hours=6),
                end_datetime=now + dt.timedelta(hours=7),
                total_amount=_money(60),
                paid_amount=_money(10),
                status=ReservationStatus.PENDING,
                user_id=user_a.id,
                company_id=company_a.id,
                branch_id=branch_a.id,
            )
            session.add(reservation_services_state)
            session.add(reservation_sale_service_only)
            session.add(reservation_combo)

            session.commit()

            return SmokeContext(
                run_id=run_id,
                company_a_id=int(company_a.id),
                company_b_id=int(company_b.id),
                branch_a_id=int(branch_a.id),
                branch_b_id=int(branch_b.id),
                user_a_id=int(user_a.id),
                user_b_id=int(user_b.id),
                user_a_email=user_a.email or "",
                user_b_email=user_b.email or "",
                user_a_username=user_a.username,
                user_b_username=user_b.username,
                user_a_password=user_a_password,
                user_b_password=user_b_password,
                product_id=int(product.id),
                product_barcode=product.barcode,
                product_sale_price=product_sale_price,
                product_initial_stock=product_initial_stock,
                reservation_services_state_id=int(reservation_services_state.id),
                reservation_sale_service_only_id=int(reservation_sale_service_only.id),
                reservation_combo_id=int(reservation_combo.id),
            )


def flow_login_multiempresa(ctx: SmokeContext) -> str:
    auth_a = AuthState()
    auth_a.needs_initial_admin = False
    auth_a.login({"email": ctx.user_a_email, "password": ctx.user_a_password})
    if auth_a.error_message:
        raise AssertionError(f"Login empresa A fallo: {auth_a.error_message}")
    payload_a = decode_token(auth_a.token)
    if not payload_a:
        raise AssertionError("Token empresa A invalido.")
    cid_a = int(payload_a.get("cid") or 0)
    if cid_a != ctx.company_a_id:
        raise AssertionError(
            f"cid empresa A incorrecto. esperado={ctx.company_a_id} obtenido={cid_a}"
        )
    user_a = auth_a.current_user
    if int(user_a.get("company_id") or 0) != ctx.company_a_id:
        raise AssertionError("current_user de empresa A no coincide.")

    auth_b = AuthState()
    auth_b.needs_initial_admin = False
    auth_b.login({"email": ctx.user_b_email, "password": ctx.user_b_password})
    if auth_b.error_message:
        raise AssertionError(f"Login empresa B fallo: {auth_b.error_message}")
    payload_b = decode_token(auth_b.token)
    if not payload_b:
        raise AssertionError("Token empresa B invalido.")
    cid_b = int(payload_b.get("cid") or 0)
    if cid_b != ctx.company_b_id:
        raise AssertionError(
            f"cid empresa B incorrecto. esperado={ctx.company_b_id} obtenido={cid_b}"
        )
    if cid_a == cid_b:
        raise AssertionError("Los tokens de A y B tienen el mismo cid.")

    return f"PASS cid_a={cid_a} cid_b={cid_b}"


def flow_role_creation_by_tenant(ctx: SmokeContext) -> str:
    auth = AuthState()
    auth.needs_initial_admin = False
    auth.login({"email": ctx.user_a_email, "password": ctx.user_a_password})
    if auth.error_message:
        raise AssertionError(f"No se pudo autenticar admin de A: {auth.error_message}")

    current_user = auth.current_user
    if not current_user.get("privileges", {}).get("manage_users"):
        raise AssertionError("Usuario de smoke sin privilegio manage_users.")

    role_name = f"SMOKE_ROLE_{ctx.run_id}"
    auth.new_user_data["privileges"] = dict(current_user["privileges"])
    auth.new_role_name = role_name
    auth.create_role_from_current_privileges()

    with tenant_bypass():
        with rx.session() as session:
            role_a = session.exec(
                select(Role)
                .where(Role.company_id == ctx.company_a_id)
                .where(Role.name == role_name)
            ).first()
            role_b = session.exec(
                select(Role)
                .where(Role.company_id == ctx.company_b_id)
                .where(Role.name == role_name)
            ).first()

    if role_a is None:
        raise AssertionError("No se creo el rol en tenant A.")
    if role_b is not None:
        raise AssertionError("El rol se filtro mal y aparecio en tenant B.")

    return f"PASS role={role_name} role_id={role_a.id}"


def flow_services_state_reservation_payment(ctx: SmokeContext) -> str:
    set_tenant_context(ctx.company_a_id, ctx.branch_a_id)
    with rx.session() as session:
        reservation_before = session.exec(
            select(FieldReservation)
            .where(FieldReservation.id == ctx.reservation_services_state_id)
            .where(FieldReservation.company_id == ctx.company_a_id)
            .where(FieldReservation.branch_id == ctx.branch_a_id)
        ).first()
        if reservation_before is None:
            raise AssertionError("Reserva para ServicesState no encontrada.")
        expected_balance = _money(
            reservation_before.total_amount - reservation_before.paid_amount
        )

    state = ServicesState()
    state.current_user = {
        "id": ctx.user_a_id,
        "company_id": ctx.company_a_id,
        "username": ctx.user_a_username,
        "privileges": {
            "manage_reservations": True,
            "view_servicios": True,
            "manage_users": True,
        },
    }
    state.selected_branch_id = str(ctx.branch_a_id)
    state.reservation_payment_id = str(ctx.reservation_services_state_id)
    state.payment_method = "Efectivo"
    state.payment_method_kind = "cash"
    state.payment_cash_amount = float(expected_balance)
    state.pay_reservation_with_payment_method()

    set_tenant_context(ctx.company_a_id, ctx.branch_a_id)
    with rx.session() as session:
        reservation_after = session.exec(
            select(FieldReservation)
            .where(FieldReservation.id == ctx.reservation_services_state_id)
            .where(FieldReservation.company_id == ctx.company_a_id)
            .where(FieldReservation.branch_id == ctx.branch_a_id)
        ).first()
        if reservation_after is None:
            raise AssertionError("Reserva ServicesState desaparecio.")
        payments = session.exec(
            select(SalePayment)
            .where(SalePayment.reference_code == f"Reserva {ctx.reservation_services_state_id}")
            .where(SalePayment.company_id == ctx.company_a_id)
            .where(SalePayment.branch_id == ctx.branch_a_id)
        ).all()
        sale_ids = [int(payment.sale_id) for payment in payments if payment.sale_id]
        logs = []
        if sale_ids:
            logs = session.exec(
                select(CashboxLog)
                .where(CashboxLog.sale_id.in_(sale_ids))
                .where(CashboxLog.company_id == ctx.company_a_id)
                .where(CashboxLog.branch_id == ctx.branch_a_id)
            ).all()

    if _money(reservation_after.paid_amount) != _money(reservation_after.total_amount):
        raise AssertionError("La reserva ServicesState no quedo pagada al 100%.")
    if reservation_after.status != ReservationStatus.PAID:
        raise AssertionError(
            f"Estado de reserva incorrecto: {reservation_after.status}"
        )
    paid_sum = _money(sum(Decimal(payment.amount) for payment in payments))
    if paid_sum != expected_balance:
        raise AssertionError(
            f"Pago registrado incorrecto. esperado={expected_balance} obtenido={paid_sum}"
        )
    if not logs:
        raise AssertionError("No se genero CashboxLog para pago ServicesState.")

    return (
        f"PASS reservation_id={ctx.reservation_services_state_id} "
        f"paid={paid_sum} sale_ids={sale_ids}"
    )


async def flow_sale_service_product_sale(ctx: SmokeContext) -> tuple[int, Decimal]:
    payment = PaymentInfoDTO(
        method="Efectivo",
        method_kind="cash",
        cash=PaymentCashDTO(amount=_money(ctx.product_sale_price * Decimal("2"))),
    )
    item = SaleItemDTO(
        description=f"Producto Smoke {ctx.run_id}",
        quantity=Decimal("2"),
        unit="Unidad",
        price=ctx.product_sale_price,
        barcode=ctx.product_barcode,
        product_id=ctx.product_id,
    )

    async with get_async_session() as session:
        result = await SaleService.process_sale(
            session=session,
            user_id=ctx.user_a_id,
            company_id=ctx.company_a_id,
            branch_id=ctx.branch_a_id,
            items=[item],
            payment_data=payment,
        )
        sale_id = int(result.sale.id)

    set_tenant_context(ctx.company_a_id, ctx.branch_a_id)
    async with get_async_session() as session:
        sale_items = (
            await session.exec(
                select(SaleItem)
                .where(SaleItem.sale_id == sale_id)
                .where(SaleItem.company_id == ctx.company_a_id)
                .where(SaleItem.branch_id == ctx.branch_a_id)
            )
        ).all()
        payments = (
            await session.exec(
                select(SalePayment)
                .where(SalePayment.sale_id == sale_id)
                .where(SalePayment.company_id == ctx.company_a_id)
                .where(SalePayment.branch_id == ctx.branch_a_id)
            )
        ).all()
        product = (
            await session.exec(
                select(Product)
                .where(Product.id == ctx.product_id)
                .where(Product.company_id == ctx.company_a_id)
                .where(Product.branch_id == ctx.branch_a_id)
            )
        ).first()

    if not any(item_row.product_id == ctx.product_id for item_row in sale_items):
        raise AssertionError("Venta de producto sin detalle de item de producto.")
    total_paid = _money(sum(Decimal(payment_row.amount) for payment_row in payments))
    expected_total = _money(ctx.product_sale_price * Decimal("2"))
    if total_paid != expected_total:
        raise AssertionError(
            f"Pago de venta producto incorrecto. esperado={expected_total} obtenido={total_paid}"
        )
    if product is None:
        raise AssertionError("Producto no encontrado luego de la venta.")

    return sale_id, _stock(product.stock)


async def flow_sale_service_reservation_only(ctx: SmokeContext) -> tuple[int, Decimal]:
    set_tenant_context(ctx.company_a_id, ctx.branch_a_id)
    async with get_async_session() as session:
        reservation_before = (
            await session.exec(
                select(FieldReservation)
                .where(FieldReservation.id == ctx.reservation_sale_service_only_id)
                .where(FieldReservation.company_id == ctx.company_a_id)
                .where(FieldReservation.branch_id == ctx.branch_a_id)
            )
        ).first()
    if reservation_before is None:
        raise AssertionError("Reserva para cobro por SaleService no encontrada.")
    balance = _money(reservation_before.total_amount - reservation_before.paid_amount)

    payment = PaymentInfoDTO(
        method="Efectivo",
        method_kind="cash",
        cash=PaymentCashDTO(amount=balance),
    )
    async with get_async_session() as session:
        result = await SaleService.process_sale(
            session=session,
            user_id=ctx.user_a_id,
            company_id=ctx.company_a_id,
            branch_id=ctx.branch_a_id,
            items=[],
            payment_data=payment,
            reservation_id=str(ctx.reservation_sale_service_only_id),
        )
        sale_id = int(result.sale.id)

    set_tenant_context(ctx.company_a_id, ctx.branch_a_id)
    async with get_async_session() as session:
        reservation_after = (
            await session.exec(
                select(FieldReservation)
                .where(FieldReservation.id == ctx.reservation_sale_service_only_id)
                .where(FieldReservation.company_id == ctx.company_a_id)
                .where(FieldReservation.branch_id == ctx.branch_a_id)
            )
        ).first()
        sale_items = (
            await session.exec(
                select(SaleItem)
                .where(SaleItem.sale_id == sale_id)
                .where(SaleItem.company_id == ctx.company_a_id)
                .where(SaleItem.branch_id == ctx.branch_a_id)
            )
        ).all()

    if reservation_after is None:
        raise AssertionError("Reserva post-cobro no encontrada.")
    if reservation_after.status != ReservationStatus.PAID:
        raise AssertionError("La reserva cobrada por SaleService no quedo en PAID.")
    if _money(reservation_after.paid_amount) != _money(reservation_after.total_amount):
        raise AssertionError("paid_amount de reserva cobrada no cuadra con total.")
    has_service_line = any(
        (sale_item.product_id is None)
        and ((sale_item.product_category_snapshot or "").lower() == "servicios")
        for sale_item in sale_items
    )
    if not has_service_line:
        raise AssertionError("Venta de reserva no genero linea de servicio.")

    return sale_id, balance


async def flow_sale_service_product_plus_reservation(
    ctx: SmokeContext,
) -> tuple[int, Decimal]:
    set_tenant_context(ctx.company_a_id, ctx.branch_a_id)
    async with get_async_session() as session:
        reservation_before = (
            await session.exec(
                select(FieldReservation)
                .where(FieldReservation.id == ctx.reservation_combo_id)
                .where(FieldReservation.company_id == ctx.company_a_id)
                .where(FieldReservation.branch_id == ctx.branch_a_id)
            )
        ).first()
    if reservation_before is None:
        raise AssertionError("Reserva combo no encontrada.")
    reservation_balance = _money(
        reservation_before.total_amount - reservation_before.paid_amount
    )
    expected_total = _money(reservation_balance + ctx.product_sale_price)

    payment = PaymentInfoDTO(
        method="Efectivo",
        method_kind="cash",
        cash=PaymentCashDTO(amount=expected_total),
    )
    item = SaleItemDTO(
        description=f"Producto Smoke {ctx.run_id}",
        quantity=Decimal("1"),
        unit="Unidad",
        price=ctx.product_sale_price,
        barcode=ctx.product_barcode,
        product_id=ctx.product_id,
    )
    async with get_async_session() as session:
        result = await SaleService.process_sale(
            session=session,
            user_id=ctx.user_a_id,
            company_id=ctx.company_a_id,
            branch_id=ctx.branch_a_id,
            items=[item],
            payment_data=payment,
            reservation_id=str(ctx.reservation_combo_id),
        )
        sale_id = int(result.sale.id)

    set_tenant_context(ctx.company_a_id, ctx.branch_a_id)
    async with get_async_session() as session:
        reservation_after = (
            await session.exec(
                select(FieldReservation)
                .where(FieldReservation.id == ctx.reservation_combo_id)
                .where(FieldReservation.company_id == ctx.company_a_id)
                .where(FieldReservation.branch_id == ctx.branch_a_id)
            )
        ).first()
        sale_items = (
            await session.exec(
                select(SaleItem)
                .where(SaleItem.sale_id == sale_id)
                .where(SaleItem.company_id == ctx.company_a_id)
                .where(SaleItem.branch_id == ctx.branch_a_id)
            )
        ).all()
        payments = (
            await session.exec(
                select(SalePayment)
                .where(SalePayment.sale_id == sale_id)
                .where(SalePayment.company_id == ctx.company_a_id)
                .where(SalePayment.branch_id == ctx.branch_a_id)
            )
        ).all()
        product = (
            await session.exec(
                select(Product)
                .where(Product.id == ctx.product_id)
                .where(Product.company_id == ctx.company_a_id)
                .where(Product.branch_id == ctx.branch_a_id)
            )
        ).first()

    if reservation_after is None:
        raise AssertionError("Reserva combo no encontrada post-venta.")
    if reservation_after.status != ReservationStatus.PAID:
        raise AssertionError("Reserva combo no quedo pagada.")
    has_product_line = any(item_row.product_id == ctx.product_id for item_row in sale_items)
    has_service_line = any(item_row.product_id is None for item_row in sale_items)
    if not has_product_line or not has_service_line:
        raise AssertionError("Venta combo no contiene lineas producto+servicio.")

    total_paid = _money(sum(Decimal(payment_row.amount) for payment_row in payments))
    if total_paid != expected_total:
        raise AssertionError(
            f"Pago total combo incorrecto. esperado={expected_total} obtenido={total_paid}"
        )
    if product is None:
        raise AssertionError("Producto no encontrado tras combo.")

    return sale_id, _stock(product.stock)


def _run_sync_flow(results: list[FlowResult], name: str, fn) -> None:
    try:
        details = fn()
        results.append(FlowResult(name=name, ok=True, details=details))
    except Exception as exc:
        traceback_str = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        results.append(FlowResult(name=name, ok=False, details=traceback_str))


async def _run_async_sale_flows(ctx: SmokeContext) -> list[FlowResult]:
    results: list[FlowResult] = []
    try:
        sale_id_product, stock_after_product = await flow_sale_service_product_sale(ctx)
        results.append(
            FlowResult(
                name="venta_producto",
                ok=True,
                details=f"PASS sale_id={sale_id_product} stock_after={stock_after_product}",
            )
        )
    except Exception as exc:
        traceback_str = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        results.append(FlowResult(name="venta_producto", ok=False, details=traceback_str))
        return results

    try:
        sale_id_reservation, paid_balance = await flow_sale_service_reservation_only(ctx)
        results.append(
            FlowResult(
                name="cobro_servicio_reserva",
                ok=True,
                details=(
                    f"PASS sale_id={sale_id_reservation} "
                    f"reservation_id={ctx.reservation_sale_service_only_id} paid={paid_balance}"
                ),
            )
        )
    except Exception as exc:
        traceback_str = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        results.append(
            FlowResult(name="cobro_servicio_reserva", ok=False, details=traceback_str)
        )

    try:
        sale_id_combo, stock_after_combo = await flow_sale_service_product_plus_reservation(ctx)
        expected_stock = _stock(ctx.product_initial_stock - Decimal("3"))
        if stock_after_combo != expected_stock:
            raise AssertionError(
                f"Stock final incorrecto. esperado={expected_stock} obtenido={stock_after_combo}"
            )
        results.append(
            FlowResult(
                name="venta_producto_mas_cobro_reserva",
                ok=True,
                details=(
                    f"PASS sale_id={sale_id_combo} reservation_id={ctx.reservation_combo_id} "
                    f"stock_final={stock_after_combo}"
                ),
            )
        )
    except Exception as exc:
        traceback_str = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        results.append(
            FlowResult(
                name="venta_producto_mas_cobro_reserva",
                ok=False,
                details=traceback_str,
            )
        )

    return results


async def _dispose_async_resources() -> None:
    await async_engine.dispose()


async def _run_async_flows_and_cleanup(ctx: SmokeContext) -> list[FlowResult]:
    try:
        return await _run_async_sale_flows(ctx)
    finally:
        await _dispose_async_resources()


def main() -> int:
    print("== Smoke funcional en vivo (multi-tenant) ==")
    print(f"Inicio: {dt.datetime.now().isoformat(timespec='seconds')}")

    try:
        ctx = setup_smoke_data()
    except Exception as exc:
        print("FALLO setup_smoke_data")
        print("".join(traceback.format_exception_only(type(exc), exc)).strip())
        return 2

    print(
        "Contexto smoke: "
        f"run_id={ctx.run_id} "
        f"company_a={ctx.company_a_id} company_b={ctx.company_b_id} "
        f"branch_a={ctx.branch_a_id} branch_b={ctx.branch_b_id}"
    )

    results: list[FlowResult] = []
    _run_sync_flow(results, "login_multiempresa", lambda: flow_login_multiempresa(ctx))
    _run_sync_flow(
        results,
        "creacion_roles_por_tenant",
        lambda: flow_role_creation_by_tenant(ctx),
    )
    _run_sync_flow(
        results,
        "pago_reserva_services_state",
        lambda: flow_services_state_reservation_payment(ctx),
    )

    async_results = asyncio.run(_run_async_flows_and_cleanup(ctx))
    results.extend(async_results)

    print("\n== Resultados ==")
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.details}")

    passed = sum(1 for result in results if result.ok)
    failed = len(results) - passed
    print(f"\nResumen: {passed} PASS, {failed} FAIL")
    print(f"Fin: {dt.datetime.now().isoformat(timespec='seconds')}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
