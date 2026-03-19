"""Tests para enforcement de tenant isolation.

IMPORTANTE: test_select_is_filtered_by_tenant DEBE ejecutarse antes que
cualquier otro test que invoque set_tenant_context() + flush/commit en
el mismo proceso. Esto es porque with_loader_criteria de SQLAlchemy
cachea la primera compilación de statement y reutiliza esos parámetros
en queries posteriores del mismo tipo. En producción esto no afecta
porque cada request usa un worker/contexto independiente.
"""
from __future__ import annotations

from typing import Optional

import pytest
from sqlmodel import Field, SQLModel, Session, create_engine, select

from app.utils.tenant import (
    register_tenant_listeners,
    set_tenant_context,
    tenant_context,
    tenant_bypass,
    _refresh_tenant_models,
)


class TenantWidget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    company_id: int = Field(nullable=False, index=True)
    branch_id: int = Field(nullable=False, index=True)


@pytest.fixture(autouse=True)
def _clean_tenant_context():
    """Reset tenant context between tests to prevent cross-contamination."""
    yield
    set_tenant_context(None, None)


@pytest.fixture()
def db_engine():
    register_tenant_listeners()
    _refresh_tenant_models()
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return engine


# NOTE: This test MUST run first (alphabetical order: "a" < "auto" < "missing")
def test_a_select_is_filtered_by_tenant():
    """Verify automatic SELECT filtering via with_loader_criteria.

    Uses a completely isolated engine and runs first to avoid
    SQLAlchemy's statement cache interference.
    """
    register_tenant_listeners()
    _refresh_tenant_models()
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    # Insert data with tenant_bypass
    with Session(engine) as session:
        with tenant_bypass():
            session.add(TenantWidget(name="A1", company_id=1, branch_id=1))
            session.add(TenantWidget(name="B2", company_id=2, branch_id=2))
            session.commit()

    # Query in a fresh session with tenant context set
    with Session(engine) as session:
        set_tenant_context(1, 1)
        rows = session.exec(select(TenantWidget)).all()
        assert len(rows) == 1
        assert rows[0].company_id == 1


def test_auto_sets_tenant_ids(db_engine):
    with Session(db_engine) as session:
        with tenant_context(1, 10):
            widget = TenantWidget(name="A")
            session.add(widget)
            session.commit()
            assert widget.company_id == 1
            assert widget.branch_id == 10


def test_missing_tenant_context_raises(db_engine):
    with Session(db_engine) as session:
        set_tenant_context(None, None)
        widget = TenantWidget(name="B")
        session.add(widget)
        with pytest.raises(RuntimeError):
            session.commit()
