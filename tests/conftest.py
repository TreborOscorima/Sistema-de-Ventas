import os
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, call

import pytest

# Ensure auth helpers can be imported during test collection.
os.environ.setdefault("AUTH_SECRET_KEY", "test_secret_key_for_pytest_only_32_chars_min")

from app.models import Product, Sale, Unit
from app.schemas.sale_schemas import PaymentCashDTO, PaymentInfoDTO, SaleItemDTO


class ExecResult:
    def __init__(self, all_items=None, first_item=None) -> None:
        self._all_items = all_items if all_items is not None else []
        self._first_item = first_item

    def all(self):
        return self._all_items

    def first(self):
        return self._first_item


class _QueueingExecMock:
    """Reemplazo de AsyncMock para `session.exec` que agota `side_effect` con
    fallback a ExecResult() vacío, permitiendo que tests con secuencias fijas
    sigan funcionando cuando el código de producción agrega nuevas queries
    (ej. _apply_promotions, lookup de price_list del cliente en Sprint 1).
    """

    def __init__(self) -> None:
        self.call_count = 0
        self.call_args_list: list = []
        self._side_effect_queue: list | None = None
        self._return_value = ExecResult()

    @property
    def side_effect(self):
        return self._side_effect_queue

    @side_effect.setter
    def side_effect(self, value):
        self._side_effect_queue = list(value) if value else None

    @property
    def return_value(self):
        return self._return_value

    @return_value.setter
    def return_value(self, value):
        self._return_value = value

    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.call_args_list.append(call(*args, **kwargs))
        if self._side_effect_queue:
            return self._side_effect_queue.pop(0)
        return self._return_value


class FakeAsyncSession:
    def __init__(self) -> None:
        # `exec` es un mock custom que soporta `side_effect=[lista]` como AsyncMock
        # pero, al agotarse la lista, devuelve ExecResult() vacío en vez de lanzar
        # StopAsyncIteration. Así los tests no se rompen cuando el código agrega
        # queries nuevas (ej. promociones, listas de precios por cliente).
        self.exec = _QueueingExecMock()
        self.get = AsyncMock()
        self.added = []
        self.add = Mock(side_effect=self._add)
        self.flush = AsyncMock(side_effect=self._flush)
        self.refresh = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    def _add(self, obj) -> None:
        self.added.append(obj)

    async def _flush(self) -> None:
        for obj in self.added:
            if isinstance(obj, Sale) and getattr(obj, "id", None) is None:
                obj.id = 1


@pytest.fixture
def session_mock():
    return FakeAsyncSession()


@pytest.fixture
def exec_result():
    def _factory(all_items=None, first_item=None):
        return ExecResult(all_items=all_items, first_item=first_item)

    return _factory


@pytest.fixture
def unit_sample():
    return Unit(name="Unidad", allows_decimal=False)


@pytest.fixture
def product_sample():
    return Product(
        id=1,
        barcode="1234567890123",
        description="Producto Test",
        stock=Decimal("10.0000"),
        unit="Unidad",
        sale_price=Decimal("5.00"),
    )


@pytest.fixture
def sale_data_sample(product_sample):
    return {
        "user_id": 1,
        "items": [
            SaleItemDTO(
                description=product_sample.description,
                quantity=Decimal("1"),
                unit=product_sample.unit,
                price=Decimal("5.00"),
                barcode=product_sample.barcode,
            )
        ],
        "payment_data": PaymentInfoDTO(
            method="cash",
            method_kind="cash",
            cash=PaymentCashDTO(amount=Decimal("5.00")),
        ),
    }
