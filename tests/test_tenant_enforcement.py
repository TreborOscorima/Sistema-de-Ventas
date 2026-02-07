from __future__ import annotations

from typing import Optional

import pytest
from sqlmodel import Field, SQLModel, Session, create_engine, select

from app.utils.tenant import (
    register_tenant_listeners,
    set_tenant_context,
    tenant_context,
)


class TenantWidget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    company_id: int = Field(nullable=False, index=True)
    branch_id: int = Field(nullable=False, index=True)


@pytest.fixture()
def db_session():
    register_tenant_listeners()
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_auto_sets_tenant_ids(db_session: Session):
    set_tenant_context(1, 10)
    widget = TenantWidget(name="A")
    db_session.add(widget)
    db_session.commit()
    assert widget.company_id == 1
    assert widget.branch_id == 10


def test_missing_tenant_context_raises(db_session: Session):
    set_tenant_context(None, None)
    widget = TenantWidget(name="B")
    db_session.add(widget)
    with pytest.raises(RuntimeError):
        db_session.commit()


def test_select_is_filtered_by_tenant(db_session: Session):
    with tenant_context(1, 1):
        db_session.add(TenantWidget(name="A1"))
        db_session.commit()
    with tenant_context(2, 2):
        db_session.add(TenantWidget(name="B2"))
        db_session.commit()

    set_tenant_context(1, 1)
    rows = db_session.exec(select(TenantWidget)).all()
    assert len(rows) == 1
    assert rows[0].company_id == 1
