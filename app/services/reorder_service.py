"""Servicio de reposición automática de inventario.

Detecta productos con stock <= min_stock_alert y genera órdenes de compra
(PurchaseOrder) sugeridas agrupadas por proveedor preferido (default_supplier_id).

Flujo:
1. suggest_reorders_by_supplier(company_id, branch_id) → dict[supplier_id, list[dict]]
   Agrupa productos bajo umbral por proveedor preferido.
   Los productos sin default_supplier_id quedan bajo la clave None.
2. create_draft_purchase_order(...) → crea PurchaseOrder + PurchaseOrderItem en BD.
3. cancel_purchase_order(...) / mark_purchase_order_sent(...) / convert_to_purchase(...)
   gestionan el ciclo de vida.

La cantidad sugerida por defecto es: max(min_stock_alert * 2 - current_stock, min_stock_alert).
Intención: reponer hasta duplicar el umbral mínimo, garantizando buffer post-reposición.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from sqlmodel import Session, select

from app.models import (
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)
from app.utils.timezone import utc_now_naive

logger = logging.getLogger(__name__)


@dataclass
class ReorderSuggestion:
    """Producto candidato a reposición."""
    product_id: int
    barcode: str
    description: str
    current_stock: Decimal
    min_stock_alert: Decimal
    suggested_quantity: Decimal
    unit: str
    unit_cost: Decimal
    default_supplier_id: Optional[int]

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "barcode": self.barcode,
            "description": self.description,
            "current_stock": float(self.current_stock),
            "min_stock_alert": float(self.min_stock_alert),
            "suggested_quantity": float(self.suggested_quantity),
            "unit": self.unit,
            "unit_cost": float(self.unit_cost),
            "default_supplier_id": self.default_supplier_id,
        }


@dataclass
class SupplierReorderGroup:
    """Productos a reponer agrupados por un mismo proveedor."""
    supplier_id: Optional[int]
    supplier_name: str
    items: List[ReorderSuggestion] = field(default_factory=list)

    @property
    def total_estimated(self) -> Decimal:
        return sum(
            (it.suggested_quantity * it.unit_cost for it in self.items),
            Decimal("0.00"),
        )

    def to_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "item_count": len(self.items),
            "total_estimated": float(self.total_estimated),
            "items": [it.to_dict() for it in self.items],
        }


def _compute_suggested_quantity(
    current_stock: Decimal, min_stock_alert: Decimal
) -> Decimal:
    """Cantidad sugerida: llevar stock al doble del umbral mínimo.

    Si el producto ya tiene algo de stock, descuenta lo disponible.
    Garantiza mínimo `min_stock_alert` para evitar reposiciones triviales.
    """
    target = min_stock_alert * Decimal("2")
    needed = target - current_stock
    if needed < min_stock_alert:
        needed = min_stock_alert
    # Redondear a 4 decimales (consistente con Numeric(10,4))
    return needed.quantize(Decimal("0.0001"))


def suggest_reorders_by_supplier(
    session: Session,
    company_id: int,
    branch_id: int,
) -> List[SupplierReorderGroup]:
    """Analiza productos bajo umbral y los agrupa por proveedor preferido.

    Returns:
        Lista de grupos ordenados alfabéticamente por nombre de proveedor.
        El grupo "Sin proveedor" (supplier_id=None) va al final si existe.
    """
    # Productos activos bajo umbral
    stmt = select(Product).where(
        Product.company_id == company_id,
        Product.branch_id == branch_id,
        Product.is_active == True,  # noqa: E712
        Product.stock <= Product.min_stock_alert,
    )
    products = list(session.exec(stmt).all())

    if not products:
        return []

    # Cargar proveedores referenciados
    supplier_ids = {p.default_supplier_id for p in products if p.default_supplier_id}
    suppliers_map: Dict[int, Supplier] = {}
    if supplier_ids:
        # Filtrar por tenant — evita leak si default_supplier_id apunta a
        # un proveedor de otra empresa por inconsistencia histórica.
        sup_stmt = select(Supplier).where(
            Supplier.id.in_(supplier_ids),
            Supplier.company_id == company_id,
            Supplier.branch_id == branch_id,
        )
        for s in session.exec(sup_stmt).all():
            suppliers_map[s.id] = s

    # Agrupar
    groups: Dict[Optional[int], SupplierReorderGroup] = {}
    for p in products:
        sid = p.default_supplier_id
        if sid and sid in suppliers_map:
            sname = suppliers_map[sid].name
        elif sid:
            # FK huérfana (proveedor eliminado o cambio de tenant)
            sname = f"Proveedor #{sid}"
        else:
            sname = "Sin proveedor asignado"

        if sid not in groups:
            groups[sid] = SupplierReorderGroup(
                supplier_id=sid, supplier_name=sname
            )

        suggestion = ReorderSuggestion(
            product_id=p.id,
            barcode=p.barcode,
            description=p.description,
            current_stock=Decimal(p.stock or 0),
            min_stock_alert=Decimal(p.min_stock_alert or 0),
            suggested_quantity=_compute_suggested_quantity(
                Decimal(p.stock or 0), Decimal(p.min_stock_alert or 0)
            ),
            unit=p.unit or "Unidad",
            unit_cost=Decimal(p.purchase_price or 0),
            default_supplier_id=sid,
        )
        groups[sid].items.append(suggestion)

    # Orden: con proveedor (alfabético) → sin proveedor al final
    with_supplier = [g for g in groups.values() if g.supplier_id is not None]
    with_supplier.sort(key=lambda g: g.supplier_name.lower())
    without_supplier = [g for g in groups.values() if g.supplier_id is None]
    return with_supplier + without_supplier


def create_draft_purchase_order(
    session: Session,
    company_id: int,
    branch_id: int,
    supplier_id: int,
    items: List[ReorderSuggestion],
    user_id: Optional[int] = None,
    notes: Optional[str] = "",
    auto_generated: bool = True,
) -> PurchaseOrder:
    """Crea una PurchaseOrder en estado 'draft' con ítems sugeridos.

    Seguridad:
        - Los `ReorderSuggestion` del input pueden venir de un state/frontend
          no confiable. Se recargan los datos autoritativos desde BD y se
          valida que cada product_id pertenezca al tenant.
        - Del input se acepta únicamente `product_id` y `suggested_quantity`
          (la última saneada > 0).

    Raises:
        ValueError si items está vacío, supplier_id no existe en el tenant,
        o algún product_id no pertenece al tenant.
    """
    if not items:
        raise ValueError("No se puede crear una PO sin ítems")

    # Validar proveedor del tenant
    supplier = session.exec(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.company_id == company_id,
            Supplier.branch_id == branch_id,
        )
    ).first()
    if supplier is None:
        raise ValueError(f"Proveedor {supplier_id} no existe en este tenant")

    # Batch load autoritativo desde BD — nunca confiar en los campos del
    # ReorderSuggestion salvo product_id y suggested_quantity.
    requested_ids = [int(it.product_id) for it in items if it.product_id]
    if not requested_ids:
        raise ValueError("No se puede crear una PO sin ítems")

    products_rows = session.exec(
        select(Product).where(
            Product.id.in_(requested_ids),
            Product.company_id == company_id,
            Product.branch_id == branch_id,
        )
    ).all()
    products_map: Dict[int, Product] = {int(p.id): p for p in products_rows}

    missing = [pid for pid in requested_ids if pid not in products_map]
    if missing:
        raise ValueError(
            f"Producto(s) no pertenecen al tenant o no existen: {missing}"
        )

    total = Decimal("0.00")
    po_items: List[PurchaseOrderItem] = []
    for it in items:
        pid = int(it.product_id)
        product = products_map[pid]
        qty = Decimal(str(it.suggested_quantity or 0))
        if qty <= 0:
            raise ValueError(
                f"Cantidad inválida para producto {pid}: {qty}"
            )
        qty = qty.quantize(Decimal("0.0001"))
        unit_cost = Decimal(str(product.purchase_price or 0))
        current_stock = Decimal(str(product.stock or 0))
        min_stock_alert = Decimal(str(product.min_stock_alert or 0))
        subtotal = (qty * unit_cost).quantize(Decimal("0.01"))
        total += subtotal
        po_items.append(
            PurchaseOrderItem(
                product_id=pid,
                company_id=company_id,
                branch_id=branch_id,
                description_snapshot=product.description,
                barcode_snapshot=product.barcode,
                current_stock=current_stock,
                min_stock_alert=min_stock_alert,
                suggested_quantity=qty,
                unit=product.unit or "Unidad",
                unit_cost=unit_cost,
                subtotal=subtotal,
            )
        )

    po = PurchaseOrder(
        company_id=company_id,
        branch_id=branch_id,
        supplier_id=supplier_id,
        status=PurchaseOrderStatus.DRAFT,
        total_amount=total,
        notes=notes,
        auto_generated=auto_generated,
        user_id=user_id,
    )
    session.add(po)
    session.flush()  # obtener po.id

    for it in po_items:
        it.purchase_order_id = po.id
        session.add(it)

    session.flush()
    logger.info(
        "Draft PO creada: id=%s supplier=%s items=%d total=%s",
        po.id, supplier_id, len(po_items), total,
    )
    return po


def list_purchase_orders(
    session: Session,
    company_id: int,
    branch_id: int,
    status: Optional[str] = None,
) -> List[PurchaseOrder]:
    """Lista POs del tenant, opcionalmente filtrado por status."""
    stmt = select(PurchaseOrder).where(
        PurchaseOrder.company_id == company_id,
        PurchaseOrder.branch_id == branch_id,
    )
    if status is not None:
        stmt = stmt.where(PurchaseOrder.status == status)
    stmt = stmt.order_by(PurchaseOrder.created_at.desc())
    return list(session.exec(stmt).all())


def mark_purchase_order_sent(
    session: Session,
    purchase_order_id: int,
    company_id: int,
    branch_id: int,
) -> PurchaseOrder:
    """Transiciona draft → sent. Se asume que se notificó al proveedor."""
    # FOR UPDATE serializa transiciones concurrentes — evita doble envío.
    po = session.exec(
        select(PurchaseOrder)
        .where(
            PurchaseOrder.id == purchase_order_id,
            PurchaseOrder.company_id == company_id,
            PurchaseOrder.branch_id == branch_id,
        )
        .with_for_update()
    ).first()
    if po is None:
        raise ValueError("PO no encontrada en este tenant")
    if po.status != PurchaseOrderStatus.DRAFT:
        raise ValueError(
            f"Solo se puede enviar una PO en estado 'draft' (estado actual: {po.status})"
        )
    po.status = PurchaseOrderStatus.SENT
    po.updated_at = utc_now_naive()
    session.add(po)
    session.flush()
    return po


def cancel_purchase_order(
    session: Session,
    purchase_order_id: int,
    company_id: int,
    branch_id: int,
) -> PurchaseOrder:
    """Cancela una PO (solo si no fue recibida)."""
    po = session.exec(
        select(PurchaseOrder)
        .where(
            PurchaseOrder.id == purchase_order_id,
            PurchaseOrder.company_id == company_id,
            PurchaseOrder.branch_id == branch_id,
        )
        .with_for_update()
    ).first()
    if po is None:
        raise ValueError("PO no encontrada en este tenant")
    if po.status == PurchaseOrderStatus.RECEIVED:
        raise ValueError("No se puede cancelar una PO ya recibida")
    po.status = PurchaseOrderStatus.CANCELLED
    po.updated_at = utc_now_naive()
    session.add(po)
    session.flush()
    return po
