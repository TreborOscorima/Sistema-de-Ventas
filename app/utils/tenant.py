from __future__ import annotations

import contextvars
import os
from contextlib import contextmanager
from typing import Any, Iterable, Optional, Type

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria
from sqlmodel import SQLModel

TENANT_OPTION_COMPANY = "tenant_company_id"
TENANT_OPTION_BRANCH = "tenant_branch_id"
TENANT_OPTION_BYPASS = "tenant_bypass"

_STRICT_TENANT = os.getenv("TENANT_STRICT", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}

_tenant_company_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "tenant_company_id",
    default=None,
)
_tenant_branch_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "tenant_branch_id",
    default=None,
)
_tenant_bypass: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "tenant_bypass",
    default=False,
)

_TENANT_COMPANY_MODELS: list[Type[SQLModel]] = []
_TENANT_BRANCH_MODELS: list[Type[SQLModel]] = []
_TENANT_MODELS_READY = False
_TENANT_LISTENERS_INSTALLED = False


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return None
    return value_int if value_int > 0 else None


def set_tenant_context(company_id: Any, branch_id: Any) -> None:
    _tenant_company_id.set(_coerce_int(company_id))
    _tenant_branch_id.set(_coerce_int(branch_id))


def get_tenant_context() -> tuple[Optional[int], Optional[int]]:
    return _tenant_company_id.get(), _tenant_branch_id.get()


@contextmanager
def tenant_context(company_id: Any, branch_id: Any):
    token_company = _tenant_company_id.set(_coerce_int(company_id))
    token_branch = _tenant_branch_id.set(_coerce_int(branch_id))
    try:
        yield
    finally:
        _tenant_company_id.reset(token_company)
        _tenant_branch_id.reset(token_branch)


@contextmanager
def tenant_bypass():
    token = _tenant_bypass.set(True)
    try:
        yield
    finally:
        _tenant_bypass.reset(token)


def _collect_models() -> list[Type[SQLModel]]:
    seen: set[Type[SQLModel]] = set()
    stack: list[Type[Any]] = [SQLModel]
    while stack:
        base = stack.pop()
        for sub in base.__subclasses__():
            stack.append(sub)
            if getattr(sub, "__table__", None) is not None:
                seen.add(sub)
    return list(seen)


def _refresh_tenant_models() -> None:
    global _TENANT_COMPANY_MODELS, _TENANT_BRANCH_MODELS, _TENANT_MODELS_READY
    models = _collect_models()
    company_models: list[Type[SQLModel]] = []
    branch_models: list[Type[SQLModel]] = []
    for model in models:
        table = getattr(model, "__table__", None)
        if table is None:
            continue
        if "company_id" in table.c:
            company_models.append(model)
        if "branch_id" in table.c:
            branch_col = table.c.get("branch_id")
            if branch_col is not None and not getattr(branch_col, "nullable", True):
                branch_models.append(model)
    _TENANT_COMPANY_MODELS = company_models
    _TENANT_BRANCH_MODELS = branch_models
    _TENANT_MODELS_READY = True


def _ensure_models_ready() -> None:
    if not _TENANT_MODELS_READY:
        _refresh_tenant_models()


def _statement_froms(statement: Any) -> Iterable[Any]:
    getter = getattr(statement, "get_final_froms", None)
    if callable(getter):
        try:
            return getter() or []
        except Exception:
            return []
    return []


def _statement_requires_company(statement: Any) -> bool:
    for from_ in _statement_froms(statement):
        cols = getattr(from_, "c", None)
        if cols is not None and "company_id" in cols:
            return True
    return False


def _statement_requires_branch(statement: Any) -> bool:
    for from_ in _statement_froms(statement):
        cols = getattr(from_, "c", None)
        if cols is None or "branch_id" not in cols:
            continue
        branch_col = cols.get("branch_id")
        if branch_col is not None and not getattr(branch_col, "nullable", True):
            return True
    return False


def _resolve_tenant_ids(execution_options: dict[str, Any] | None) -> tuple[Optional[int], Optional[int]]:
    exec_opts = execution_options or {}
    company_id = _coerce_int(_tenant_company_id.get())
    branch_id = _coerce_int(_tenant_branch_id.get())
    if company_id is None:
        company_id = _coerce_int(exec_opts.get(TENANT_OPTION_COMPANY))
    if branch_id is None:
        branch_id = _coerce_int(exec_opts.get(TENANT_OPTION_BRANCH))
    return company_id, branch_id


def _apply_tenant_criteria(orm_execute_state) -> None:
    if orm_execute_state.execution_options.get(TENANT_OPTION_BYPASS):
        return
    if _tenant_bypass.get():
        return
    if not orm_execute_state.is_select:
        return

    statement = orm_execute_state.statement
    if not _statement_requires_company(statement):
        return

    company_id, branch_id = _resolve_tenant_ids(orm_execute_state.execution_options)
    if company_id is None:
        if _STRICT_TENANT:
            raise RuntimeError(
                "Tenant company_id faltante. Usa set_tenant_context() o tenant_bypass."
            )
        return

    if branch_id is None and _STRICT_TENANT and _statement_requires_branch(statement):
        raise RuntimeError(
            "Tenant branch_id faltante para una entidad con branch_id. "
            "Selecciona sucursal o usa tenant_bypass."
        )

    _ensure_models_ready()
    for model in _TENANT_COMPANY_MODELS:
        statement = statement.options(
            with_loader_criteria(
                model,
                lambda cls: cls.company_id == company_id,
                include_aliases=True,
            )
        )

    if branch_id is not None:
        for model in _TENANT_BRANCH_MODELS:
            statement = statement.options(
                with_loader_criteria(
                    model,
                    lambda cls: cls.branch_id == branch_id,
                    include_aliases=True,
                )
            )

    orm_execute_state.statement = statement


def _before_flush(session, flush_context, instances) -> None:
    if session.info.get(TENANT_OPTION_BYPASS):
        return
    if _tenant_bypass.get():
        return

    _ensure_models_ready()
    company_ctx, branch_ctx = get_tenant_context()

    for obj in session.new:
        table = getattr(obj, "__table__", None)
        if table is None:
            continue

        if "company_id" in table.c:
            current_company = getattr(obj, "company_id", None)
            if _coerce_int(current_company) is None:
                if company_ctx is None:
                    raise RuntimeError(
                        "company_id faltante al crear entidad. "
                        "Establece tenant_context o asigna company_id explícitamente."
                    )
                setattr(obj, "company_id", company_ctx)

        if "branch_id" in table.c:
            current_branch = getattr(obj, "branch_id", None)
            branch_required = not getattr(table.c.get("branch_id"), "nullable", True)
            if _coerce_int(current_branch) is None:
                if branch_required:
                    if branch_ctx is None:
                        raise RuntimeError(
                            "branch_id faltante al crear entidad. "
                            "Selecciona sucursal o asigna branch_id explícitamente."
                        )
                    setattr(obj, "branch_id", branch_ctx)
                elif branch_ctx is not None:
                    setattr(obj, "branch_id", branch_ctx)


def register_tenant_listeners() -> None:
    global _TENANT_LISTENERS_INSTALLED
    if _TENANT_LISTENERS_INSTALLED:
        return
    event.listen(Session, "do_orm_execute", _apply_tenant_criteria)
    event.listen(Session, "before_flush", _before_flush)
    _TENANT_LISTENERS_INSTALLED = True

