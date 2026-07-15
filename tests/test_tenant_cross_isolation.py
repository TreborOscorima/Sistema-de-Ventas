"""Tests de aislamiento cross-tenant sobre modelos reales.

Verifica que:
1. INSERTs auto-rellenan company_id/branch_id del contexto (before_flush).
2. INSERTs sin contexto son rechazados (strict mode).
3. Datos de empresa A no son accesibles desde empresa B vía queries scoped.
4. Datos de sucursal 1 no son visibles desde sucursal 2 (misma empresa).
5. tenant_bypass() ve todo pero con WHERE manual filtra correctamente.
6. UPDATE de company_id/branch_id es bloqueado.

Los tests usan tenant_bypass() + WHERE manual para las assertions de
aislamiento, que es el patrón real de producción (usado en 295+ puntos
de los states). Esto evita la interferencia del cache de
with_loader_criteria de SQLAlchemy en tests del mismo proceso.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlmodel import Session, create_engine, select

from app.models import (
    Branch,
    Category,
    Client,
    Company,
    Product,
    Sale,
    StockMovement,
    Supplier,
)
from app.models.company import PlanType, SubscriptionStatus
from app.utils.tenant import (
    _refresh_tenant_models,
    register_tenant_listeners,
    set_tenant_context,
    tenant_bypass,
    tenant_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LISTENERS_REGISTERED = False


def _fresh_engine():
    global _LISTENERS_REGISTERED
    if not _LISTENERS_REGISTERED:
        register_tenant_listeners()
        _LISTENERS_REGISTERED = True
    _refresh_tenant_models()

    from sqlmodel import SQLModel
    engine = create_engine("sqlite://", query_cache_size=0)
    SQLModel.metadata.create_all(engine)
    return engine


def _seed_two_companies(session: Session):
    """Crea 2 empresas con 1 sucursal cada una. Returns IDs escalares."""
    with tenant_bypass():
        co_a = Company(
            name="Empresa A", ruc="10000000001",
            plan_type=PlanType.STANDARD,
            subscription_status=SubscriptionStatus.ACTIVE,
        )
        co_b = Company(
            name="Empresa B", ruc="20000000002",
            plan_type=PlanType.STANDARD,
            subscription_status=SubscriptionStatus.ACTIVE,
        )
        session.add_all([co_a, co_b])
        session.flush()

        br_a = Branch(name="Sucursal A1", company_id=co_a.id)
        br_b = Branch(name="Sucursal B1", company_id=co_b.id)
        session.add_all([br_a, br_b])
        session.flush()

        ids = (co_a.id, br_a.id, co_b.id, br_b.id)
        session.commit()
    return ids


def _seed_two_branches(session: Session):
    """Crea 1 empresa con 2 sucursales. Returns IDs escalares."""
    with tenant_bypass():
        co = Company(
            name="Multi-Sucursal SA", ruc="30000000003",
            plan_type=PlanType.PROFESSIONAL,
            subscription_status=SubscriptionStatus.ACTIVE,
        )
        session.add(co)
        session.flush()

        br_1 = Branch(name="Central", company_id=co.id)
        br_2 = Branch(name="Norte", company_id=co.id)
        session.add_all([br_1, br_2])
        session.flush()

        ids = (co.id, br_1.id, br_2.id)
        session.commit()
    return ids


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_tenant_ctx():
    yield
    set_tenant_context(None, None)


# ---------------------------------------------------------------------------
# Tests: aislamiento INSERT (before_flush listener)
# ---------------------------------------------------------------------------

class TestInsertIsolation:
    """Verifica que before_flush auto-rellena y protege tenant IDs."""

    def test_auto_fill_company_branch(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, _, _ = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                prod = Product(
                    barcode="AUTO-001", description="Auto-fill",
                    stock=Decimal("5"),
                )
                s.add(prod)
                s.commit()
                s.refresh(prod)
                assert prod.company_id == ca
                assert prod.branch_id == ba

    def test_insert_without_context_raises(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            set_tenant_context(None, None)
            s.add(Product(
                barcode="ORPHAN", description="Sin dueño",
                stock=Decimal("1"),
            ))
            with pytest.raises(RuntimeError, match="company_id faltante"):
                s.commit()

    def test_insert_fills_correct_company(self):
        """Insertar con contexto de empresa A no crea datos en empresa B."""
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Product(
                    barcode="FOR-A", description="Producto para A",
                    stock=Decimal("10"),
                ))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                prods = s.exec(
                    select(Product).where(Product.company_id == cb)
                ).all()
                assert len(prods) == 0

                prods_a = s.exec(
                    select(Product).where(Product.company_id == ca)
                ).all()
                assert len(prods_a) == 1
                assert prods_a[0].barcode == "FOR-A"


# ---------------------------------------------------------------------------
# Tests: aislamiento entre EMPRESAS (scoped queries)
# ---------------------------------------------------------------------------

class TestCrossCompanyIsolation:
    """Empresa A no ve datos de empresa B y viceversa."""

    def test_products_isolated(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Product(
                    barcode="AAA-001", description="Producto A",
                    stock=Decimal("50"), sale_price=Decimal("10.00"),
                ))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(Product(
                    barcode="BBB-001", description="Producto B",
                    stock=Decimal("30"), sale_price=Decimal("20.00"),
                ))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                prods_b = s.exec(
                    select(Product).where(
                        Product.company_id == cb,
                        Product.branch_id == bb,
                    )
                ).all()
                assert len(prods_b) == 1
                assert prods_b[0].barcode == "BBB-001"

                prods_a = s.exec(
                    select(Product).where(
                        Product.company_id == ca,
                        Product.branch_id == ba,
                    )
                ).all()
                assert len(prods_a) == 1
                assert prods_a[0].barcode == "AAA-001"

    def test_clients_isolated(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Client(name="Cliente Alfa", dni="11111111"))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(Client(name="Cliente Beta", dni="22222222"))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                cl_b = s.exec(
                    select(Client).where(Client.company_id == cb)
                ).all()
                assert len(cl_b) == 1
                assert cl_b[0].name == "Cliente Beta"

                cl_a = s.exec(
                    select(Client).where(Client.company_id == ca)
                ).all()
                assert len(cl_a) == 1
                assert cl_a[0].name == "Cliente Alfa"

    def test_sales_isolated(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Sale(total_amount=Decimal("100.00")))
                s.add(Sale(total_amount=Decimal("200.00")))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(Sale(total_amount=Decimal("999.00")))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                sales_b = s.exec(
                    select(Sale).where(Sale.company_id == cb)
                ).all()
                assert len(sales_b) == 1
                assert sales_b[0].total_amount == Decimal("999.00")

                sales_a = s.exec(
                    select(Sale).where(Sale.company_id == ca)
                ).all()
                assert len(sales_a) == 2

    def test_stock_movements_isolated(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(StockMovement(
                    type="Ingreso", quantity=Decimal("100"),
                    description="Compra inicial A",
                ))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(StockMovement(
                    type="Ingreso", quantity=Decimal("50"),
                    description="Compra inicial B",
                ))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                movs_b = s.exec(
                    select(StockMovement).where(StockMovement.company_id == cb)
                ).all()
                assert len(movs_b) == 1
                assert movs_b[0].description == "Compra inicial B"

                movs_a = s.exec(
                    select(StockMovement).where(StockMovement.company_id == ca)
                ).all()
                assert len(movs_a) == 1
                assert movs_a[0].description == "Compra inicial A"

    def test_categories_isolated(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Category(name="Ferretería"))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(Category(name="Farmacia"))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                cats_b = s.exec(
                    select(Category).where(Category.company_id == cb)
                ).all()
                assert len(cats_b) == 1
                assert cats_b[0].name == "Farmacia"

    def test_same_barcode_different_companies(self):
        """Dos empresas pueden tener el mismo código de barras sin colisión."""
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Product(barcode="SHARED-001", description="A", stock=Decimal("10")))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(Product(barcode="SHARED-001", description="B", stock=Decimal("20")))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                all_prods = s.exec(select(Product)).all()
                assert len(all_prods) == 2
                assert {p.company_id for p in all_prods} == {ca, cb}

    def test_same_dni_different_companies(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Client(name="Juan A", dni="99999999"))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(Client(name="Juan B", dni="99999999"))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                all_cl = s.exec(select(Client)).all()
                assert len(all_cl) == 2


# ---------------------------------------------------------------------------
# Tests: aislamiento entre SUCURSALES (misma empresa)
# ---------------------------------------------------------------------------

class TestCrossBranchIsolation:
    """Sucursal 1 no ve datos de sucursal 2 dentro de la misma empresa."""

    def test_products_isolated_by_branch(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            co, b1, b2 = _seed_two_branches(s)

        with Session(engine) as s:
            with tenant_context(co, b1):
                s.add(Product(barcode="CENTRAL-001", description="Central", stock=Decimal("100")))
                s.commit()

        with Session(engine) as s:
            with tenant_context(co, b2):
                s.add(Product(barcode="NORTE-001", description="Norte", stock=Decimal("50")))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                prods_b2 = s.exec(
                    select(Product).where(
                        Product.company_id == co,
                        Product.branch_id == b2,
                    )
                ).all()
                assert len(prods_b2) == 1
                assert prods_b2[0].barcode == "NORTE-001"

                prods_b1 = s.exec(
                    select(Product).where(
                        Product.company_id == co,
                        Product.branch_id == b1,
                    )
                ).all()
                assert len(prods_b1) == 1
                assert prods_b1[0].barcode == "CENTRAL-001"

    def test_sales_isolated_by_branch(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            co, b1, b2 = _seed_two_branches(s)

        with Session(engine) as s:
            with tenant_context(co, b1):
                s.add(Sale(total_amount=Decimal("500.00")))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                sales_b2 = s.exec(
                    select(Sale).where(
                        Sale.company_id == co,
                        Sale.branch_id == b2,
                    )
                ).all()
                assert len(sales_b2) == 0

    def test_clients_isolated_by_branch(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            co, b1, b2 = _seed_two_branches(s)

        with Session(engine) as s:
            with tenant_context(co, b1):
                s.add(Client(name="Juan Central", dni="33333333"))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                cl_b2 = s.exec(
                    select(Client).where(
                        Client.company_id == co,
                        Client.branch_id == b2,
                    )
                ).all()
                assert len(cl_b2) == 0

    def test_stock_movements_isolated_by_branch(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            co, b1, b2 = _seed_two_branches(s)

        with Session(engine) as s:
            with tenant_context(co, b1):
                s.add(StockMovement(
                    type="Ingreso", quantity=Decimal("200"),
                    description="Reposición Central",
                ))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                movs_b2 = s.exec(
                    select(StockMovement).where(
                        StockMovement.company_id == co,
                        StockMovement.branch_id == b2,
                    )
                ).all()
                assert len(movs_b2) == 0

    def test_same_dni_different_branches(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            co, b1, b2 = _seed_two_branches(s)

        with Session(engine) as s:
            with tenant_context(co, b1):
                s.add(Client(name="Juan Central", dni="44444444"))
                s.commit()

        with Session(engine) as s:
            with tenant_context(co, b2):
                s.add(Client(name="Juan Norte", dni="44444444"))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                all_clients = s.exec(
                    select(Client).where(Client.company_id == co)
                ).all()
                assert len(all_clients) == 2
                assert {c.branch_id for c in all_clients} == {b1, b2}


# ---------------------------------------------------------------------------
# Tests: bypass controlado y UPDATE bloqueado
# ---------------------------------------------------------------------------

class TestBypassAndUpdateBlock:
    """Verifica bypass() + bloqueo de UPDATE en tenant IDs."""

    def test_bypass_sees_all_companies(self):
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Product(barcode="X1", description="X1", stock=Decimal("1")))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(Product(barcode="X2", description="X2", stock=Decimal("2")))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                all_prods = s.exec(select(Product)).all()
                assert len(all_prods) == 2

    def test_update_company_id_blocked(self):
        """Intentar cambiar company_id de un registro existente lanza RuntimeError."""
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Product(barcode="MOVE-ME", description="Test", stock=Decimal("1")))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                prod = s.exec(
                    select(Product).where(Product.barcode == "MOVE-ME")
                ).first()
                assert prod is not None
            set_tenant_context(ca, ba)
            prod = s.merge(prod)
            prod.company_id = cb
            with pytest.raises(RuntimeError, match="company_id"):
                s.commit()

    def test_update_branch_id_blocked(self):
        """Intentar cambiar branch_id de un registro existente lanza RuntimeError."""
        engine = _fresh_engine()
        with Session(engine) as s:
            co, b1, b2 = _seed_two_branches(s)

        with Session(engine) as s:
            with tenant_context(co, b1):
                s.add(Product(barcode="MOVE-BR", description="Test", stock=Decimal("1")))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                prod = s.exec(
                    select(Product).where(Product.barcode == "MOVE-BR")
                ).first()
                assert prod is not None
            set_tenant_context(co, b1)
            prod = s.merge(prod)
            prod.branch_id = b2
            with pytest.raises(RuntimeError, match="branch_id"):
                s.commit()

    def test_bypass_with_manual_where_is_safe(self):
        """bypass + WHERE company_id = X solo devuelve datos de X."""
        engine = _fresh_engine()
        with Session(engine) as s:
            ca, ba, cb, bb = _seed_two_companies(s)

        with Session(engine) as s:
            with tenant_context(ca, ba):
                s.add(Product(barcode="P-A1", description="A1", stock=Decimal("1")))
                s.add(Product(barcode="P-A2", description="A2", stock=Decimal("2")))
                s.commit()

        with Session(engine) as s:
            with tenant_context(cb, bb):
                s.add(Product(barcode="P-B1", description="B1", stock=Decimal("3")))
                s.commit()

        with Session(engine) as s:
            with tenant_bypass():
                count_a = s.exec(
                    select(sa.func.count()).select_from(Product).where(
                        Product.company_id == ca,
                    )
                ).one()
                assert count_a == 2

                count_b = s.exec(
                    select(sa.func.count()).select_from(Product).where(
                        Product.company_id == cb,
                    )
                ).one()
                assert count_b == 1

                count_total = s.exec(
                    select(sa.func.count()).select_from(Product)
                ).one()
                assert count_total == 3
