"""Tests del KPI low_stock_count del Dashboard.

Verifica que DashboardState._load_kpis sume correctamente productos raíz +
variantes con stock bajo, usando el umbral propio de cada uno con fallback
al min_stock_alert del producto padre cuando la variante no lo define.

Esto es la contraparte de test_inventory_variant_min_stock_alert.py: aquel
prueba el builder de fila de inventario; este prueba el conteo agregado
para el dashboard.
"""
from __future__ import annotations

import os

import reflex as rx

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-low-stock-kpi-32chars-pls")
os.environ.setdefault("TENANT_STRICT", "0")

from app.states.dashboard_state import DashboardState


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


class _ExecResult:
    def __init__(self, scalar=0):
        self._scalar = scalar

    def one(self):
        return self._scalar


class _SequentialKpiSession:
    """FakeSession para _load_kpis.

    El método ejecuta queries en este orden estricto:
      1. total_clients
      2. active_credits
      3. pending_debt
      4. product_low (productos raíz con stock bajo)
      5. variant_low (variantes con stock bajo)
    """

    def __init__(self, scalars):
        self._scalars = list(scalars)

    def exec(self, statement):
        if not self._scalars:
            return _ExecResult(scalar=0)
        return _ExecResult(scalar=self._scalars.pop(0))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _patch_kpi_session(monkeypatch, scalars):
    monkeypatch.setattr(rx, "session", lambda: _SequentialKpiSession(scalars))


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadKpisLowStockCount:
    """low_stock_count = product_low + variant_low (suma de ambos)."""

    def test_solo_productos_raiz_con_stock_bajo(self, monkeypatch):
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)
        # clients=10, credits=2, debt=500, product_low=4, variant_low=0
        _patch_kpi_session(monkeypatch, [10, 2, 500, 4, 0])

        state._load_kpis()

        assert state.low_stock_count == 4
        assert state.total_clients == 10

    def test_solo_variantes_con_stock_bajo(self, monkeypatch):
        """Por ejemplo: tienda de ropa donde solo las variantes XL escasean."""
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)
        _patch_kpi_session(monkeypatch, [5, 0, 0, 0, 7])

        state._load_kpis()

        assert state.low_stock_count == 7

    def test_suma_productos_y_variantes(self, monkeypatch):
        """Caso típico: ambos canales contribuyen al conteo."""
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)
        _patch_kpi_session(monkeypatch, [12, 3, 1500, 6, 9])

        state._load_kpis()

        assert state.low_stock_count == 15

    def test_sin_stock_bajo_devuelve_cero(self, monkeypatch):
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)
        _patch_kpi_session(monkeypatch, [20, 1, 100, 0, 0])

        state._load_kpis()

        assert state.low_stock_count == 0

    def test_sin_tenant_resetea_kpis(self, monkeypatch):
        """Sin company_id/branch_id no debe abrir sesión y los KPIs se ponen a cero."""
        state = DashboardState()
        # Pre-cargamos valores para detectar si se resetean
        state.low_stock_count = 99
        state.total_clients = 50
        monkeypatch.setattr(state, "_company_id", lambda: None)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)

        def _explode():
            raise AssertionError("No debería abrir sesión sin tenant")

        monkeypatch.setattr(rx, "session", _explode)

        state._load_kpis()

        assert state.low_stock_count == 0
        assert state.total_clients == 0

    def test_query_variant_low_usa_coalesce_de_min_stock_alert(self, monkeypatch):
        """El SQL generado para variantes debe usar COALESCE entre el umbral
        de la variante y el del producto padre. Capturamos el SQL renderizado
        para verificar la presencia del coalesce."""
        state = DashboardState()
        monkeypatch.setattr(state, "_company_id", lambda: 1)
        monkeypatch.setattr(state, "_branch_id", lambda: 1)

        captured: list[str] = []

        class _CaptureSession:
            def exec(self, statement):
                captured.append(str(statement))
                return _ExecResult(scalar=0)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        monkeypatch.setattr(rx, "session", lambda: _CaptureSession())

        state._load_kpis()

        # Las últimas dos queries son las de stock bajo (product + variant).
        # En la query de variantes esperamos ver un coalesce entre las dos
        # columnas min_stock_alert.
        variant_sql = captured[-1].lower()
        assert "coalesce" in variant_sql
        assert "min_stock_alert" in variant_sql
        # Debe joinearse con product para acceder al umbral del padre
        assert "join product" in variant_sql or "from product" in variant_sql
