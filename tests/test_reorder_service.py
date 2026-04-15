"""Tests del servicio de reposición automática (PO sugeridas por stock bajo).

Cubre:
  - Detección de productos bajo umbral agrupados por proveedor preferido
  - Productos sin default_supplier_id → grupo "Sin proveedor"
  - Cantidad sugerida: lleva stock al doble del umbral mínimo
  - Creación de PurchaseOrder en estado draft con ítems snapshot
  - Transiciones de estado: draft → sent, draft → cancelled
  - Validación de supplier cross-tenant
"""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

import pytest
from sqlmodel import Field, SQLModel, Session, create_engine

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-reorder-service-32-chars-min!")
os.environ.setdefault("TENANT_STRICT", "0")

from app.models import (
    Branch,
    Company,
    Product,
    PurchaseOrder,
    PurchaseOrderStatus,
    Supplier,
)
from app.services.reorder_service import (
    _compute_suggested_quantity,
    cancel_purchase_order,
    create_draft_purchase_order,
    list_purchase_orders,
    mark_purchase_order_sent,
    suggest_reorders_by_supplier,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def db_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def tenant(db_engine):
    """Crea un tenant básico (company + branch) para tests."""
    with Session(db_engine) as session:
        company = Company(name="TestCo", ruc="20123456789")
        session.add(company)
        session.flush()
        branch = Branch(name="Main", company_id=company.id)
        session.add(branch)
        session.flush()
        session.commit()
        return {"company_id": company.id, "branch_id": branch.id}


@pytest.fixture()
def supplier(db_engine, tenant):
    with Session(db_engine) as session:
        s = Supplier(
            name="Proveedor ACME",
            tax_id="20987654321",
            company_id=tenant["company_id"],
            branch_id=tenant["branch_id"],
        )
        session.add(s)
        session.commit()
        session.refresh(s)
        return {"id": s.id, "name": s.name}


def _make_product(
    session: Session,
    tenant: dict,
    *,
    barcode: str,
    description: str,
    stock: str,
    min_alert: str = "5.0000",
    unit_cost: str = "10.00",
    supplier_id: Optional[int] = None,
    is_active: bool = True,
) -> Product:
    p = Product(
        barcode=barcode,
        description=description,
        company_id=tenant["company_id"],
        branch_id=tenant["branch_id"],
        stock=Decimal(stock),
        min_stock_alert=Decimal(min_alert),
        purchase_price=Decimal(unit_cost),
        sale_price=Decimal("20.00"),
        is_active=is_active,
        default_supplier_id=supplier_id,
    )
    session.add(p)
    session.flush()
    return p


# ─────────────────────────────────────────────────────────────────────────────
# _compute_suggested_quantity
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeSuggestedQuantity:
    def test_reposicion_lleva_a_doble_del_umbral(self):
        # stock=2, min=10 → target=20, needed=18
        qty = _compute_suggested_quantity(Decimal("2"), Decimal("10"))
        assert qty == Decimal("18.0000")

    def test_minimo_reposicion_es_min_stock_alert(self):
        # stock=10, min=10 → target=20, needed=10 (exactamente el umbral)
        qty = _compute_suggested_quantity(Decimal("10"), Decimal("10"))
        assert qty == Decimal("10.0000")

    def test_fraccional_preserva_precision(self):
        qty = _compute_suggested_quantity(Decimal("2.5"), Decimal("7.5"))
        # target=15, needed=12.5
        assert qty == Decimal("12.5000")

    def test_stock_cero_repone_el_doble(self):
        qty = _compute_suggested_quantity(Decimal("0"), Decimal("5"))
        # target=10, needed=10
        assert qty == Decimal("10.0000")


# ─────────────────────────────────────────────────────────────────────────────
# suggest_reorders_by_supplier
# ─────────────────────────────────────────────────────────────────────────────


class TestSuggestReorders:
    def test_db_vacia_retorna_lista_vacia(self, db_engine, tenant):
        with Session(db_engine) as session:
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )
        assert groups == []

    def test_producto_con_stock_sobre_umbral_no_aparece(self, db_engine, tenant):
        with Session(db_engine) as session:
            _make_product(
                session, tenant,
                barcode="OK001", description="Producto OK",
                stock="100", min_alert="5",
            )
            session.commit()
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )
        assert groups == []

    def test_producto_bajo_umbral_aparece_sin_proveedor(self, db_engine, tenant):
        with Session(db_engine) as session:
            _make_product(
                session, tenant,
                barcode="LOW001", description="Stock bajo",
                stock="2", min_alert="10",
            )
            session.commit()
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )

        assert len(groups) == 1
        g = groups[0]
        assert g.supplier_id is None
        assert g.supplier_name == "Sin proveedor asignado"
        assert len(g.items) == 1
        item = g.items[0]
        assert item.barcode == "LOW001"
        assert item.current_stock == Decimal("2.0000")
        assert item.min_stock_alert == Decimal("10.0000")
        assert item.suggested_quantity == Decimal("18.0000")  # 20 - 2

    def test_agrupa_por_proveedor_preferido(
        self, db_engine, tenant, supplier
    ):
        with Session(db_engine) as session:
            # 2 con proveedor ACME, 1 sin proveedor
            _make_product(
                session, tenant,
                barcode="A1", description="Con proveedor A",
                stock="1", min_alert="5",
                supplier_id=supplier["id"],
            )
            _make_product(
                session, tenant,
                barcode="A2", description="Con proveedor B",
                stock="3", min_alert="10",
                supplier_id=supplier["id"],
            )
            _make_product(
                session, tenant,
                barcode="SP1", description="Sin proveedor",
                stock="0", min_alert="5",
            )
            session.commit()
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )

        assert len(groups) == 2
        # Primer grupo: con proveedor (alfabético); último: sin proveedor
        assert groups[0].supplier_id == supplier["id"]
        assert groups[0].supplier_name == "Proveedor ACME"
        assert len(groups[0].items) == 2
        assert groups[1].supplier_id is None
        assert len(groups[1].items) == 1

    def test_total_estimado_por_grupo(self, db_engine, tenant, supplier):
        with Session(db_engine) as session:
            # stock=0 min=5 unit_cost=10 → qty=10, subtotal=100
            _make_product(
                session, tenant,
                barcode="P1", description="P1",
                stock="0", min_alert="5", unit_cost="10.00",
                supplier_id=supplier["id"],
            )
            # stock=2 min=10 unit_cost=2.50 → qty=18, subtotal=45
            _make_product(
                session, tenant,
                barcode="P2", description="P2",
                stock="2", min_alert="10", unit_cost="2.50",
                supplier_id=supplier["id"],
            )
            session.commit()
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )

        assert len(groups) == 1
        # 10 * 10.00 + 18 * 2.50 = 100 + 45 = 145
        assert groups[0].total_estimated == Decimal("145.0000")

    def test_producto_inactivo_no_se_considera(self, db_engine, tenant, supplier):
        with Session(db_engine) as session:
            _make_product(
                session, tenant,
                barcode="INA", description="Inactivo",
                stock="0", min_alert="100",
                supplier_id=supplier["id"],
                is_active=False,
            )
            session.commit()
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )
        assert groups == []


# ─────────────────────────────────────────────────────────────────────────────
# create_draft_purchase_order
# ─────────────────────────────────────────────────────────────────────────────


class TestCreateDraftPO:
    def test_crea_po_con_items_en_estado_draft(
        self, db_engine, tenant, supplier
    ):
        with Session(db_engine) as session:
            _make_product(
                session, tenant,
                barcode="C1", description="Comp 1",
                stock="2", min_alert="10", unit_cost="5.00",
                supplier_id=supplier["id"],
            )
            session.commit()
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )
            assert len(groups) == 1
            g = groups[0]
            po = create_draft_purchase_order(
                session,
                tenant["company_id"],
                tenant["branch_id"],
                g.supplier_id,
                g.items,
                user_id=None,
                notes="Test auto reorder",
            )
            session.commit()
            session.refresh(po)

            assert po.status == PurchaseOrderStatus.DRAFT
            assert po.supplier_id == supplier["id"]
            assert po.auto_generated is True
            assert po.notes == "Test auto reorder"
            # 18 unidades * 5.00 = 90.00
            assert po.total_amount == Decimal("90.00")
            assert len(po.items) == 1
            item = po.items[0]
            assert item.barcode_snapshot == "C1"
            assert item.suggested_quantity == Decimal("18.0000")
            assert item.subtotal == Decimal("90.00")

    def test_rechaza_items_vacios(self, db_engine, tenant, supplier):
        with Session(db_engine) as session:
            with pytest.raises(ValueError, match="sin ítems"):
                create_draft_purchase_order(
                    session,
                    tenant["company_id"],
                    tenant["branch_id"],
                    supplier["id"],
                    [],
                )

    def test_rechaza_proveedor_cross_tenant(self, db_engine, tenant):
        with Session(db_engine) as session:
            # Proveedor de otro tenant
            other = Supplier(
                name="Otro", tax_id="99999999999",
                company_id=999, branch_id=999,
            )
            session.add(other)
            session.commit()
            session.refresh(other)
            _make_product(
                session, tenant,
                barcode="X1", description="X1",
                stock="0", min_alert="5",
            )
            session.commit()
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )
            items = groups[0].items
            with pytest.raises(ValueError, match="no existe en este tenant"):
                create_draft_purchase_order(
                    session,
                    tenant["company_id"],
                    tenant["branch_id"],
                    other.id,
                    items,
                )


# ─────────────────────────────────────────────────────────────────────────────
# Transiciones de estado
# ─────────────────────────────────────────────────────────────────────────────


class TestStateTransitions:
    def _create_po(self, db_engine, tenant, supplier):
        with Session(db_engine) as session:
            _make_product(
                session, tenant,
                barcode="T1", description="T1",
                stock="0", min_alert="5", unit_cost="10.00",
                supplier_id=supplier["id"],
            )
            session.commit()
            groups = suggest_reorders_by_supplier(
                session, tenant["company_id"], tenant["branch_id"]
            )
            po = create_draft_purchase_order(
                session,
                tenant["company_id"],
                tenant["branch_id"],
                groups[0].supplier_id,
                groups[0].items,
            )
            session.commit()
            return po.id

    def test_mark_sent_transiciona_draft_a_sent(
        self, db_engine, tenant, supplier
    ):
        po_id = self._create_po(db_engine, tenant, supplier)
        with Session(db_engine) as session:
            po = mark_purchase_order_sent(
                session, po_id, tenant["company_id"], tenant["branch_id"]
            )
            session.commit()
            assert po.status == PurchaseOrderStatus.SENT

    def test_no_se_puede_enviar_una_po_ya_enviada(
        self, db_engine, tenant, supplier
    ):
        po_id = self._create_po(db_engine, tenant, supplier)
        with Session(db_engine) as session:
            mark_purchase_order_sent(
                session, po_id, tenant["company_id"], tenant["branch_id"]
            )
            session.commit()
            with pytest.raises(ValueError, match="olo se puede enviar"):
                mark_purchase_order_sent(
                    session, po_id, tenant["company_id"], tenant["branch_id"]
                )

    def test_cancel_transiciona_a_cancelled(
        self, db_engine, tenant, supplier
    ):
        po_id = self._create_po(db_engine, tenant, supplier)
        with Session(db_engine) as session:
            po = cancel_purchase_order(
                session, po_id, tenant["company_id"], tenant["branch_id"]
            )
            session.commit()
            assert po.status == PurchaseOrderStatus.CANCELLED

    def test_list_filtra_por_status(self, db_engine, tenant, supplier):
        po_id = self._create_po(db_engine, tenant, supplier)
        with Session(db_engine) as session:
            drafts = list_purchase_orders(
                session, tenant["company_id"], tenant["branch_id"],
                status=PurchaseOrderStatus.DRAFT,
            )
            sents = list_purchase_orders(
                session, tenant["company_id"], tenant["branch_id"],
                status=PurchaseOrderStatus.SENT,
            )
        assert len(drafts) == 1
        assert drafts[0].id == po_id
        assert len(sents) == 0

    def test_cross_tenant_no_ve_po(self, db_engine, tenant, supplier):
        po_id = self._create_po(db_engine, tenant, supplier)
        with Session(db_engine) as session:
            with pytest.raises(ValueError, match="no encontrada"):
                cancel_purchase_order(session, po_id, 999, 999)
