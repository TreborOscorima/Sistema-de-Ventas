from __future__ import annotations

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
