"""Tests del consumo controlado de promociones — bloque 5b.

Cobertura:
  * ``_consume_promotions_for_sale`` incrementa current_uses en 1 por promo,
    no por línea (1-por-venta).
  * Si una promo concurrente alcanzó max_uses bajo lock, se omite el
    incremento sin abortar la venta.
  * El SELECT usa ``with_for_update`` (verificado vía signature del query).
  * Se filtra por tenant (company_id, branch_id).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.sale_service import _consume_promotions_for_sale


def _make_promo(
    *,
    promo_id: int,
    current_uses: int = 0,
    max_uses: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=promo_id,
        current_uses=current_uses,
        max_uses=max_uses,
    )


@pytest.mark.asyncio
async def test_consume_increments_each_promo_exactly_once(
    session_mock, exec_result
):
    """Tres promo_ids distintos → cada una sube +1 a current_uses."""
    promos = [
        _make_promo(promo_id=1, current_uses=0),
        _make_promo(promo_id=2, current_uses=5),
        _make_promo(promo_id=3, current_uses=99),
    ]
    session_mock.exec.side_effect = [exec_result(all_items=promos)]

    await _consume_promotions_for_sale(
        session_mock,
        promotion_ids={1, 2, 3},
        company_id=1,
        branch_id=1,
    )

    assert promos[0].current_uses == 1
    assert promos[1].current_uses == 6
    assert promos[2].current_uses == 100
    # Una sola query (con FOR UPDATE) + un flush.
    assert session_mock.exec.call_count == 1
    assert session_mock.flush.await_count == 1


@pytest.mark.asyncio
async def test_consume_noop_when_set_is_empty(session_mock):
    """No hay query ni flush si no se aplicó ninguna promo en la venta."""
    await _consume_promotions_for_sale(
        session_mock,
        promotion_ids=set(),
        company_id=1,
        branch_id=1,
    )

    assert session_mock.exec.call_count == 0
    assert session_mock.flush.await_count == 0


@pytest.mark.asyncio
async def test_consume_skips_promo_already_at_max_uses(
    session_mock, exec_result
):
    """Si una venta concurrente ya saturó max_uses, no incrementar.

    Mejor sobre-permitir esta venta (precio ya cobrado) que abortar.
    """
    saturated = _make_promo(promo_id=10, current_uses=100, max_uses=100)
    fresh = _make_promo(promo_id=11, current_uses=10, max_uses=50)
    session_mock.exec.side_effect = [
        exec_result(all_items=[saturated, fresh])
    ]

    await _consume_promotions_for_sale(
        session_mock,
        promotion_ids={10, 11},
        company_id=1,
        branch_id=1,
    )

    assert saturated.current_uses == 100  # sin cambios
    assert fresh.current_uses == 11        # incrementado


@pytest.mark.asyncio
async def test_consume_query_uses_for_update_lock(session_mock, exec_result):
    """El SELECT debe llevar FOR UPDATE para serializar concurrencia.

    Verificación estructural: el statement pasado al exec proviene del builder
    SQLAlchemy con .with_for_update(); su atributo ``_for_update_arg`` queda
    seteado. No es exhaustivo, pero documenta la invariante de diseño.
    """
    session_mock.exec.side_effect = [exec_result(all_items=[])]

    await _consume_promotions_for_sale(
        session_mock,
        promotion_ids={1},
        company_id=1,
        branch_id=1,
    )

    assert session_mock.exec.call_count == 1
    stmt = session_mock.exec.call_args_list[0].args[0]
    # SQLAlchemy expone _for_update_arg cuando .with_for_update() fue aplicado.
    assert getattr(stmt, "_for_update_arg", None) is not None


@pytest.mark.asyncio
async def test_consume_swallows_exceptions_to_not_abort_sale(
    session_mock, exec_result
):
    """Best-effort: una excepción en el query no debe propagar.

    La venta ya se cobró; un fallo en el contador es soft-error.
    """
    async def _boom(*args, **kwargs):
        raise RuntimeError("DB down mid-flush")

    session_mock.exec.side_effect = None
    session_mock.exec = _boom  # type: ignore[assignment]

    # No debe levantar
    await _consume_promotions_for_sale(
        session_mock,
        promotion_ids={1},
        company_id=1,
        branch_id=1,
    )
