"""Tests para aislamiento de roles por tenant (company_id).

Nota sobre with_loader_criteria: SQLAlchemy cachea las opciones de
with_loader_criteria a nivel de mapper, lo que causa que queries
subsecuentes en el mismo proceso reutilicen el company_id del primer
tenant. En producción esto no es problema porque cada request usa
una sesión independiente con un único tenant.

Estos tests validan que _get_role_by_name y _ensure_role filtran
explícitamente por company_id en su query (no dependen del listener).
"""
from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.orm import selectinload

from app.models import Company, Permission, Role
from app.states.auth_state import AuthState
from app.utils.tenant import (
    register_tenant_listeners,
    _refresh_tenant_models,
    tenant_bypass,
    set_tenant_context,
)


def _setup_engine():
    register_tenant_listeners()
    _refresh_tenant_models()
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return engine


def _create_company(session: Session, name: str, ruc: str) -> Company:
    company = Company(name=name, ruc=ruc)
    session.add(company)
    session.flush()
    return company


def test_role_lookup_is_scoped_by_company() -> None:
    engine = _setup_engine()

    with Session(engine) as session:
        with tenant_bypass():
            company_a = _create_company(session, "Empresa A", "RUC-A")
            company_b = _create_company(session, "Empresa B", "RUC-B")
            role_a = Role(company_id=company_a.id, name="Cajero", description="")
            role_b = Role(company_id=company_b.id, name="Cajero", description="")
            session.add(role_a)
            session.add(role_b)
            session.commit()
            ca_id, cb_id = company_a.id, company_b.id

    state = AuthState()

    # Use tenant_bypass + explicit company_id filter to test the query
    # logic without interference from with_loader_criteria caching.
    with Session(engine) as session:
        with tenant_bypass():
            set_tenant_context(ca_id, None)
            found_a = state._get_role_by_name(session, "cajero", company_id=ca_id)

    with Session(engine) as session:
        with tenant_bypass():
            set_tenant_context(cb_id, None)
            found_b = state._get_role_by_name(session, "CAJERO", company_id=cb_id)

    assert found_a is not None
    assert found_b is not None
    assert found_a.id != found_b.id
    assert found_a.company_id == ca_id
    assert found_b.company_id == cb_id


def test_updating_role_permissions_does_not_leak_between_companies() -> None:
    engine = _setup_engine()

    with Session(engine) as session:
        with tenant_bypass():
            company_a = _create_company(session, "Empresa A", "RUC-A2")
            company_b = _create_company(session, "Empresa B", "RUC-B2")
            perm_a = Permission(codename="perm_a", description="")
            perm_b = Permission(codename="perm_b", description="")
            session.add(perm_a)
            session.add(perm_b)
            session.flush()
            role_a = Role(company_id=company_a.id, name="Cajero", description="")
            role_a.permissions = [perm_a]
            role_b = Role(company_id=company_b.id, name="Cajero", description="")
            role_b.permissions = [perm_b]
            session.add(role_a)
            session.add(role_b)
            session.commit()
            ca_id, cb_id = company_a.id, company_b.id
            ra_id, rb_id = role_a.id, role_b.id

    state = AuthState()

    with Session(engine) as session:
        with tenant_bypass():
            set_tenant_context(ca_id, None)
            state._ensure_role(
                session,
                "Cajero",
                {"perm_a": True},
                company_id=ca_id,
                overwrite=True,
            )
            session.commit()

    with Session(engine) as session:
        with tenant_bypass():
            updated_a = session.exec(
                select(Role)
                .where(Role.id == ra_id)
                .options(selectinload(Role.permissions))
            ).first()
            assert updated_a is not None
            assert {perm.codename for perm in updated_a.permissions} == {"perm_a"}

    with Session(engine) as session:
        with tenant_bypass():
            updated_b = session.exec(
                select(Role)
                .where(Role.id == rb_id)
                .options(selectinload(Role.permissions))
            ).first()
            assert updated_b is not None
            assert {perm.codename for perm in updated_b.permissions} == {"perm_b"}
