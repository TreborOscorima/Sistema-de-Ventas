from __future__ import annotations

import time

from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.orm import selectinload

from app.models import Branch, Company, Permission, Role, User as UserModel, UserBranch
from app.states.auth_state import AuthState
from app.utils.tenant import set_tenant_context


def _create_company(session: Session, name: str, ruc: str) -> Company:
    company = Company(name=name, ruc=ruc)
    session.add(company)
    session.flush()
    return company


def _create_branch(session: Session, company_id: int, name: str) -> Branch:
    branch = Branch(company_id=company_id, name=name, address="")
    session.add(branch)
    session.flush()
    return branch


def _create_role(session: Session, company_id: int, name: str) -> Role:
    role = Role(company_id=company_id, name=name, description="")
    session.add(role)
    session.flush()
    return role


def _create_user(
    session: Session,
    *,
    company_id: int,
    role_id: int,
    username: str,
    email: str,
    branch_id: int | None = None,
) -> UserModel:
    user = UserModel(
        username=username,
        email=email,
        password_hash="hash",
        company_id=company_id,
        branch_id=branch_id,
        role_id=role_id,
    )
    session.add(user)
    session.flush()
    return user


def test_role_lookup_is_scoped_by_company() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    state = AuthState()
    with Session(engine) as session:
        company_a = _create_company(session, "Empresa A", "RUC-A")
        company_b = _create_company(session, "Empresa B", "RUC-B")

        role_a = Role(company_id=company_a.id, name="Cajero", description="")
        role_b = Role(company_id=company_b.id, name="Cajero", description="")
        session.add(role_a)
        session.add(role_b)
        session.commit()

        set_tenant_context(company_a.id, None)
        found_a = state._get_role_by_name(session, "cajero", company_id=company_a.id)
        set_tenant_context(company_b.id, None)
        found_b = state._get_role_by_name(session, "CAJERO", company_id=company_b.id)

        assert found_a is not None
        assert found_b is not None
        assert found_a.id != found_b.id
        assert found_a.company_id == company_a.id
        assert found_b.company_id == company_b.id


def test_updating_role_permissions_does_not_leak_between_companies() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    state = AuthState()
    with Session(engine) as session:
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

        set_tenant_context(company_a.id, None)
        state._ensure_role(
            session,
            "Cajero",
            {"perm_a": True},
            company_id=company_a.id,
            overwrite=True,
        )
        session.commit()

        set_tenant_context(company_a.id, None)
        updated_a = session.exec(
            select(Role)
            .where(Role.id == role_a.id)
            .options(selectinload(Role.permissions))
        ).first()
        set_tenant_context(company_b.id, None)
        updated_b = session.exec(
            select(Role)
            .where(Role.id == role_b.id)
            .options(selectinload(Role.permissions))
        ).first()

        assert updated_a is not None
        assert updated_b is not None
        assert {perm.codename for perm in updated_a.permissions} == {"perm_a"}
        assert {perm.codename for perm in updated_b.permissions} == {"perm_b"}


def test_ensure_user_branch_access_backfills_from_user_branch_id() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    state = AuthState()
    with Session(engine) as session:
        company = _create_company(session, "Empresa Branch", "RUC-BR-1")
        branch = _create_branch(session, company.id, "Casa Matriz")
        role = _create_role(session, company.id, "Administrador")
        user = _create_user(
            session,
            company_id=company.id,
            role_id=role.id,
            username="admin_branch",
            email="admin_branch@test.local",
            branch_id=branch.id,
        )
        session.commit()

        set_tenant_context(company.id, None)
        branch_ids, changed = state._ensure_user_branch_access(session, user)
        session.commit()

        links = session.exec(
            select(UserBranch).where(UserBranch.user_id == user.id)
        ).all()

        assert changed is True
        assert branch_ids == [branch.id]
        assert len(links) == 1
        assert links[0].branch_id == branch.id


def test_ensure_user_branch_access_uses_single_company_branch_as_fallback() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    state = AuthState()
    with Session(engine) as session:
        company = _create_company(session, "Empresa Single", "RUC-SINGLE-1")
        branch = _create_branch(session, company.id, "Principal")
        role = _create_role(session, company.id, "Administrador")
        user = _create_user(
            session,
            company_id=company.id,
            role_id=role.id,
            username="single_branch_user",
            email="single_branch_user@test.local",
        )
        session.commit()

        set_tenant_context(company.id, None)
        branch_ids, changed = state._ensure_user_branch_access(session, user)
        session.commit()
        session.refresh(user)

        links = session.exec(
            select(UserBranch).where(UserBranch.user_id == user.id)
        ).all()

        assert changed is True
        assert branch_ids == [branch.id]
        assert user.branch_id == branch.id
        assert len(links) == 1
        assert links[0].branch_id == branch.id


def test_ensure_user_branch_access_backfills_all_company_branches_for_admin_legacy_user() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    state = AuthState()
    with Session(engine) as session:
        company = _create_company(session, "Empresa Legacy", "RUC-LEGACY-1")
        branch_a = _create_branch(session, company.id, "Casa Matriz")
        branch_b = _create_branch(session, company.id, "Sucursal Norte")
        role = _create_role(session, company.id, "Administrador")
        user = _create_user(
            session,
            company_id=company.id,
            role_id=role.id,
            username="legacy_admin",
            email="legacy_admin@test.local",
        )
        session.commit()
        session.refresh(user)

        set_tenant_context(company.id, None)
        branch_ids, changed = state._ensure_user_branch_access(session, user)
        session.commit()
        session.refresh(user)

        links = session.exec(
            select(UserBranch).where(UserBranch.user_id == user.id)
        ).all()

        assert changed is True
        assert branch_ids == [branch_a.id, branch_b.id]
        assert user.branch_id == branch_a.id
        assert sorted(link.branch_id for link in links) == [branch_a.id, branch_b.id]


def test_module_visibility_waits_for_runtime_context() -> None:
    def build_state(runtime_ctx_loaded: bool) -> AuthState:
        state = AuthState()
        state._USER_CACHE_TTL = 30.0
        state._cached_user = {
            "id": 1,
            "company_id": 1,
            "branch_id": 1,
            "username": "admin",
            "email": "admin@test.local",
            "role": "Administrador",
            "privileges": {
                "view_servicios": True,
                "view_clientes": True,
                "view_cuentas": True,
            },
            "must_change_password": False,
            "is_platform_owner": False,
        }
        state._cached_user_token = state.token
        state._cached_user_time = time.time()
        state.runtime_ctx_loaded = runtime_ctx_loaded
        state.company_has_reservations = False
        state.company_has_clients = False
        state.company_has_credits = False
        return state

    pending_state = build_state(False)

    assert pending_state.can_view_servicios is True
    assert pending_state.can_view_clientes is True
    assert pending_state.can_view_cuentas is True

    ready_state = build_state(True)

    assert ready_state.can_view_servicios is False
    assert ready_state.can_view_clientes is False
    assert ready_state.can_view_cuentas is False


def test_can_view_servicios_uses_services_module_flag() -> None:
    state = AuthState()
    state._USER_CACHE_TTL = 30.0
    state._cached_user = {
        "id": 1,
        "company_id": 1,
        "branch_id": 1,
        "username": "admin",
        "email": "admin@test.local",
        "role": "Administrador",
        "privileges": {
            "view_servicios": True,
        },
        "must_change_password": False,
        "is_platform_owner": False,
    }
    state._cached_user_token = state.token
    state._cached_user_time = time.time()
    state.runtime_ctx_loaded = True
    state.company_has_services = True
    state.company_has_reservations = False

    assert state.can_view_servicios is True
