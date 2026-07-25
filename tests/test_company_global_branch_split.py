"""Tests para la separación Global (empresa) vs Sucursal en configuración (v4.3).

Cubre:
    - Branch.phone (teléfono por local) y Branch.is_main (marca de matriz).
    - Contrato de ConfigState: is_main_branch + globals_locked.
    - Migración t5u6v7w8 (cadena y estructura).
"""
from __future__ import annotations

import os

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-global-split")
os.environ.setdefault("TENANT_STRICT", "0")


# ═════════════════════════════════════════════════════════════
# BRANCH: nuevos campos phone + is_main
# ═════════════════════════════════════════════════════════════


class TestBranchNewFields:
    """Branch.phone (por local) y Branch.is_main (matriz)."""

    def test_phone_field_exists(self):
        from app.models.company import Branch
        assert "phone" in Branch.model_fields

    def test_is_main_field_exists(self):
        from app.models.company import Branch
        assert "is_main" in Branch.model_fields

    def test_phone_default_empty(self):
        from app.models.company import Branch
        b = Branch(company_id=1, name="Sucursal Centro")
        assert b.phone == ""

    def test_is_main_default_false(self):
        """Una sucursal nueva nunca es matriz por defecto."""
        from app.models.company import Branch
        b = Branch(company_id=1, name="Sucursal Centro")
        assert b.is_main is False

    def test_phone_assignable_per_branch(self):
        """Cada local puede tener su propio teléfono."""
        from app.models.company import Branch
        a = Branch(company_id=1, name="Local A", phone="+54 11 4444")
        b = Branch(company_id=1, name="Local B", phone="+54 351 5555")
        assert a.phone == "+54 11 4444"
        assert b.phone == "+54 351 5555"
        assert a.phone != b.phone

    def test_main_branch_flag(self):
        from app.models.company import Branch
        b = Branch(company_id=1, name="Casa Central", is_main=True)
        assert b.is_main is True


# ═════════════════════════════════════════════════════════════
# CONFIG STATE: contrato del split global/sucursal
# ═════════════════════════════════════════════════════════════


class TestConfigStateContract:
    """ConfigState expone el estado matriz y el bloqueo de globales."""

    def test_has_is_main_branch(self):
        from app.states.config_state import ConfigState
        assert hasattr(ConfigState, "is_main_branch")

    def test_has_globals_locked_var(self):
        """globals_locked es un computed var derivado de is_main_branch."""
        from app.states.config_state import ConfigState
        assert "globals_locked" in dir(ConfigState)


# ═════════════════════════════════════════════════════════════
# MIGRACIÓN t5u6v7w8
# ═════════════════════════════════════════════════════════════


class TestGlobalSplitMigration:
    """Verifica la migración de phone/is_main + unificación de globales."""

    def _load(self):
        import importlib.util
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "alembic", "versions",
            "t5u6v7w8_branch_phone_is_main_global_split.py",
        )
        spec = importlib.util.spec_from_file_location("migration_t5u6v7w8", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_revision_chain(self):
        mod = self._load()
        assert mod.revision == "t5u6v7w8"
        assert mod.down_revision == "s4t5u6v7"

    def test_has_upgrade_downgrade(self):
        mod = self._load()
        assert callable(mod.upgrade)
        assert callable(mod.downgrade)
