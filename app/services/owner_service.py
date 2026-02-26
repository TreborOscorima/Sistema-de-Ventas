"""
Servicio de administración de suscripciones para owners de plataforma.

Centraliza toda la lógica de negocio para gestionar empresas (tenants)
desde el backoffice owner. Ninguna modificación directa a Company se
hace desde la UI; todo pasa por este servicio con validaciones,
transiciones de estado y auditoría atómica.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.auth import User
from app.models.company import Branch, Company, PlanType, SubscriptionStatus
from app.models.owner import OwnerAuditLog
from app.models.sales import CompanySettings
from app.utils.logger import get_logger

logger = get_logger("OwnerService")

# ───────────────────────────────────────────────────────
#  Transiciones de estado válidas
# ───────────────────────────────────────────────────────

VALID_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    SubscriptionStatus.ACTIVE: [
        SubscriptionStatus.WARNING,
        SubscriptionStatus.SUSPENDED,
    ],
    SubscriptionStatus.WARNING: [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.SUSPENDED,
    ],
    SubscriptionStatus.PAST_DUE: [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.SUSPENDED,
    ],
    SubscriptionStatus.SUSPENDED: [
        SubscriptionStatus.ACTIVE,
    ],
}

# Límites por plan
PLAN_DEFAULTS: Dict[str, Dict[str, Any]] = {
    PlanType.TRIAL: {
        "max_users": 3,
        "max_branches": 2,
        "has_reservations_module": True,
        "has_services_module": True,
        "has_clients_module": True,
        "has_credits_module": True,
        "has_electronic_billing": False,
    },
    PlanType.STANDARD: {
        "max_users": 5,
        "max_branches": 3,
        "has_reservations_module": False,
        "has_services_module": False,
        "has_clients_module": False,
        "has_credits_module": False,
        "has_electronic_billing": False,
    },
    PlanType.PROFESSIONAL: {
        "max_users": 15,
        "max_branches": 10,
        "has_reservations_module": True,
        "has_services_module": True,
        "has_clients_module": True,
        "has_credits_module": True,
        "has_electronic_billing": True,
    },
    PlanType.ENTERPRISE: {
        "max_users": 999,
        "max_branches": 999,
        "has_reservations_module": True,
        "has_services_module": True,
        "has_clients_module": True,
        "has_credits_module": True,
        "has_electronic_billing": True,
    },
}


def _company_snapshot(company: Company) -> Dict[str, Any]:
    """Genera snapshot serializable del estado relevante de la empresa."""
    return {
        "plan_type": company.plan_type,
        "subscription_status": company.subscription_status,
        "is_active": company.is_active,
        "trial_ends_at": company.trial_ends_at.isoformat() if company.trial_ends_at else None,
        "subscription_ends_at": (
            company.subscription_ends_at.isoformat() if company.subscription_ends_at else None
        ),
        "max_users": company.max_users,
        "max_branches": company.max_branches,
        "has_reservations_module": company.has_reservations_module,
        "has_services_module": company.has_services_module,
        "has_clients_module": company.has_clients_module,
        "has_credits_module": company.has_credits_module,
        "has_electronic_billing": company.has_electronic_billing,
    }


async def _write_audit(
    session: AsyncSession,
    *,
    actor_user_id: int,
    actor_email: str,
    target_company: Company,
    action: str,
    before: Dict[str, Any],
    after: Dict[str, Any],
    reason: str,
    ip_address: Optional[str] = None,
) -> OwnerAuditLog:
    """Registra una entrada de auditoría en la misma transacción."""
    log = OwnerAuditLog(
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        target_company_id=target_company.id,  # type: ignore[arg-type]
        target_company_name=target_company.name,
        action=action,
        before_snapshot=json.dumps(before, ensure_ascii=False, default=str),
        after_snapshot=json.dumps(after, ensure_ascii=False, default=str),
        reason=reason,
        ip_address=ip_address,
    )
    session.add(log)
    return log


class OwnerServiceError(Exception):
    """Error controlado del servicio de owners."""
    pass


def _effective_status(company: Company) -> str:
    """Calcula el estado efectivo considerando expiración de trial.

    Si la empresa tiene plan trial, subscription_status == 'active' pero
    su trial_ends_at ya pasó, retorna 'trial_expired' para reflejar
    que el periodo de prueba venció aunque la BD no se haya actualizado.
    """
    if (
        company.plan_type == PlanType.TRIAL
        and company.subscription_status == SubscriptionStatus.ACTIVE
        and company.trial_ends_at
        and company.trial_ends_at < datetime.now()
    ):
        return "trial_expired"
    return company.subscription_status


class OwnerService:
    """Servicio estático para operaciones de backoffice de owners."""

    # ─── Lecturas ───────────────────────────────────────

    @staticmethod
    async def list_companies(
        session: AsyncSession,
        *,
        search: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Lista empresas con búsqueda, paginación y conteos de uso."""
        def _row_values(row: Any) -> List[Any]:
            """Normaliza filas SQLAlchemy/SQLModel a lista de valores."""
            if isinstance(row, (tuple, list)):
                return list(row)
            mapping = getattr(row, "_mapping", None)
            if mapping is not None:
                return list(mapping.values())
            try:
                return list(row)
            except TypeError:
                return [row]

        def _single_company_scalar_fallback(rows: list, caster):
            """Compatibilidad con mocks legacy que devuelven escalares."""
            if len(company_ids) != 1 or not rows:
                return {}
            first_values = _row_values(rows[0])
            if not first_values:
                return {}
            if len(first_values) >= 2:
                return {}
            try:
                return {company_ids[0]: caster(first_values[0])}
            except (TypeError, ValueError):
                return {}

        page = max(int(page or 1), 1)
        per_page = min(max(int(per_page or 20), 1), 100)

        # Conteo total
        count_stmt = select(func.count()).select_from(Company)
        if search:
            like = f"%{search}%"
            count_stmt = count_stmt.where(
                (Company.name.ilike(like)) | (Company.ruc.ilike(like))  # type: ignore[union-attr]
            )
        total_result = await session.exec(count_stmt)  # type: ignore[arg-type]
        total = int(total_result.one() or 0)

        # Datos paginados
        stmt = select(Company).order_by(Company.id.desc())  # type: ignore[union-attr]
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                (Company.name.ilike(like)) | (Company.ruc.ilike(like))  # type: ignore[union-attr]
            )
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        result = await session.exec(stmt)  # type: ignore[arg-type]
        companies = result.all()

        if not companies:
            return [], total

        company_ids = [int(c.id) for c in companies if getattr(c, "id", None) is not None]

        # ── Batch queries para evitar N+1 (latencia en tablas grandes) ──
        user_counts_stmt = (
            select(User.company_id, func.count(User.id))
            .where(User.company_id.in_(company_ids))
            .where(User.is_active == True)  # noqa: E712
            .group_by(User.company_id)
        )
        user_counts_result = await session.exec(user_counts_stmt)  # type: ignore[arg-type]
        user_count_rows = user_counts_result.all()
        user_counts = {}
        for row in user_count_rows:
            values = _row_values(row)
            if len(values) >= 2:
                company_id, count = values[0], values[1]
                user_counts[int(company_id)] = int(count or 0)
        if not user_counts:
            user_counts = _single_company_scalar_fallback(user_count_rows, lambda v: int(v or 0))

        branch_counts_stmt = (
            select(Branch.company_id, func.count(Branch.id))
            .where(Branch.company_id.in_(company_ids))
            .group_by(Branch.company_id)
        )
        branch_counts_result = await session.exec(branch_counts_stmt)  # type: ignore[arg-type]
        branch_count_rows = branch_counts_result.all()
        branch_counts = {}
        for row in branch_count_rows:
            values = _row_values(row)
            if len(values) >= 2:
                company_id, count = values[0], values[1]
                branch_counts[int(company_id)] = int(count or 0)
        if not branch_counts:
            branch_counts = _single_company_scalar_fallback(branch_count_rows, lambda v: int(v or 0))

        first_user_subq = (
            select(
                User.company_id.label("company_id"),
                func.min(User.id).label("first_user_id"),
            )
            .where(User.company_id.in_(company_ids))
            .group_by(User.company_id)
            .subquery()
        )
        first_user_stmt = (
            select(first_user_subq.c.company_id, User.email)
            .join(User, User.id == first_user_subq.c.first_user_id)
        )
        first_user_result = await session.exec(first_user_stmt)  # type: ignore[arg-type]
        first_user_rows = first_user_result.all()
        admin_emails = {}
        for row in first_user_rows:
            values = _row_values(row)
            if len(values) >= 2:
                company_id, email = values[0], values[1]
                admin_emails[int(company_id)] = email or ""
        if not admin_emails:
            admin_emails = _single_company_scalar_fallback(
                first_user_rows,
                lambda v: (v or ""),
            )

        first_settings_subq = (
            select(
                CompanySettings.company_id.label("company_id"),
                func.min(CompanySettings.id).label("first_settings_id"),
            )
            .where(CompanySettings.company_id.in_(company_ids))
            .group_by(CompanySettings.company_id)
            .subquery()
        )
        first_settings_stmt = (
            select(first_settings_subq.c.company_id, CompanySettings.phone)
            .join(CompanySettings, CompanySettings.id == first_settings_subq.c.first_settings_id)
        )
        first_settings_result = await session.exec(first_settings_stmt)  # type: ignore[arg-type]
        first_settings_rows = first_settings_result.all()
        company_phones = {}
        for row in first_settings_rows:
            values = _row_values(row)
            if len(values) >= 2:
                company_id, phone = values[0], values[1]
                company_phones[int(company_id)] = phone or ""
        if not company_phones:
            company_phones = _single_company_scalar_fallback(
                first_settings_rows,
                lambda v: (v or ""),
            )

        items = []
        for c in companies:
            company_id = int(c.id)

            # Limpiar trial_ends_at residual si la empresa ya no es trial
            effective_trial_ends = c.trial_ends_at
            if c.plan_type != PlanType.TRIAL and c.trial_ends_at:
                effective_trial_ends = None

            items.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "ruc": c.ruc,
                    "admin_email": admin_emails.get(company_id) or "Sin correo",
                    "company_phone": company_phones.get(company_id) or "Sin teléfono",
                    "is_active": c.is_active,
                    "plan_type": c.plan_type,
                    "subscription_status": c.subscription_status,
                    "effective_status": _effective_status(c),
                    "trial_ends_at": effective_trial_ends.isoformat() if effective_trial_ends else None,
                    "subscription_ends_at": (
                        c.subscription_ends_at.isoformat() if c.subscription_ends_at else None
                    ),
                    "max_users": c.max_users,
                    "max_branches": c.max_branches,
                    "current_users": user_counts.get(company_id, 0),
                    "current_branches": branch_counts.get(company_id, 0),
                    "has_reservations_module": c.has_reservations_module,
                    "has_services_module": c.has_services_module,
                    "has_clients_module": c.has_clients_module,
                    "has_credits_module": c.has_credits_module,
                    "has_electronic_billing": c.has_electronic_billing,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
            )

        return items, total

    @staticmethod
    async def get_company_detail(
        session: AsyncSession,
        company_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Obtiene detalle completo de una empresa."""
        company = await session.get(Company, company_id)
        if not company:
            return None

        user_count_stmt = (
            select(func.count())
            .select_from(User)
            .where(User.company_id == company_id, User.is_active == True)  # noqa: E712
        )
        user_count_result = await session.exec(user_count_stmt)  # type: ignore[arg-type]
        user_count = user_count_result.one()

        branch_count_stmt = (
            select(func.count())
            .select_from(Branch)
            .where(Branch.company_id == company_id)
        )
        branch_count_result = await session.exec(branch_count_stmt)  # type: ignore[arg-type]
        branch_count = branch_count_result.one()

        first_user_stmt = (
            select(User.email)
            .where(User.company_id == company_id)
            .order_by(User.id.asc())
            .limit(1)
        )
        first_user_result = await session.exec(first_user_stmt)  # type: ignore[arg-type]
        admin_email = first_user_result.first()

        settings_stmt = (
            select(CompanySettings.phone)
            .where(CompanySettings.company_id == company_id)
            .limit(1)
        )
        settings_result = await session.exec(settings_stmt)  # type: ignore[arg-type]
        company_phone = settings_result.first()

        return {
            "id": company.id,
            "name": company.name,
            "ruc": company.ruc,
            "admin_email": admin_email or "Sin correo",
            "company_phone": company_phone or "Sin teléfono",
            "is_active": company.is_active,
            "plan_type": company.plan_type,
            "subscription_status": company.subscription_status,
            "effective_status": _effective_status(company),
            "trial_ends_at": (
                company.trial_ends_at.isoformat() if company.trial_ends_at else None
            ),
            "subscription_ends_at": (
                company.subscription_ends_at.isoformat()
                if company.subscription_ends_at
                else None
            ),
            "max_users": company.max_users,
            "max_branches": company.max_branches,
            "current_users": user_count,
            "current_branches": branch_count,
            "has_reservations_module": company.has_reservations_module,
            "has_services_module": company.has_services_module,
            "has_clients_module": company.has_clients_module,
            "has_credits_module": company.has_credits_module,
            "has_electronic_billing": company.has_electronic_billing,
            "created_at": company.created_at.isoformat() if company.created_at else None,
        }

    @staticmethod
    async def get_audit_logs(
        session: AsyncSession,
        *,
        company_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Lista logs de auditoría con filtro opcional por empresa."""
        count_stmt = select(func.count()).select_from(OwnerAuditLog)
        if company_id:
            count_stmt = count_stmt.where(
                OwnerAuditLog.target_company_id == company_id
            )
        total_result = await session.exec(count_stmt)  # type: ignore[arg-type]
        total = total_result.one()

        stmt = select(OwnerAuditLog).order_by(OwnerAuditLog.id.desc())  # type: ignore[union-attr]
        if company_id:
            stmt = stmt.where(OwnerAuditLog.target_company_id == company_id)
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        result = await session.exec(stmt)  # type: ignore[arg-type]
        logs = result.all()

        items = []
        for log in logs:
            items.append(
                {
                    "id": log.id,
                    "actor_email": log.actor_email,
                    "target_company_name": log.target_company_name,
                    "target_company_id": log.target_company_id,
                    "action": log.action,
                    "before_snapshot": log.before_snapshot,
                    "after_snapshot": log.after_snapshot,
                    "reason": log.reason,
                    "ip_address": log.ip_address or "",
                    "created_at": (
                        log.created_at.isoformat() if log.created_at else ""
                    ),
                }
            )
        return items, total

    # ─── Escrituras (atómicas con auditoría) ─────────────

    @staticmethod
    async def change_plan(
        session: AsyncSession,
        *,
        company_id: int,
        new_plan: str,
        actor_user_id: int,
        actor_email: str,
        reason: str,
        subscription_months: int = 12,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cambia el plan de una empresa con validación y auditoría."""
        if not reason or not reason.strip():
            raise OwnerServiceError("El motivo es obligatorio.")

        valid_plans = [p.value for p in PlanType]
        if new_plan not in valid_plans:
            raise OwnerServiceError(
                f"Plan inválido: {new_plan}. Válidos: {valid_plans}"
            )

        company = await session.get(Company, company_id)
        if not company:
            raise OwnerServiceError(f"Empresa {company_id} no encontrada.")

        if company.plan_type == new_plan:
            raise OwnerServiceError(
                f"La empresa ya tiene el plan '{new_plan}'."
            )

        before = _company_snapshot(company)

        # Aplicar defaults del nuevo plan
        defaults = PLAN_DEFAULTS.get(new_plan, {})
        company.plan_type = new_plan
        company.max_users = defaults.get("max_users", company.max_users)
        company.max_branches = defaults.get("max_branches", company.max_branches)
        company.has_reservations_module = defaults.get(
            "has_reservations_module", company.has_reservations_module
        )
        company.has_services_module = defaults.get(
            "has_services_module", company.has_services_module
        )
        company.has_clients_module = defaults.get(
            "has_clients_module", company.has_clients_module
        )
        company.has_credits_module = defaults.get(
            "has_credits_module", company.has_credits_module
        )
        company.has_electronic_billing = defaults.get(
            "has_electronic_billing", company.has_electronic_billing
        )

        # Si sale de trial, limpiar trial_ends_at
        if new_plan != PlanType.TRIAL and company.trial_ends_at:
            company.trial_ends_at = None

        # Activar suscripción al cambiar plan (excepto si es trial)
        if new_plan != PlanType.TRIAL:
            company.subscription_status = SubscriptionStatus.ACTIVE
            company.is_active = True
            # Establecer fecha de vencimiento de suscripción
            if subscription_months and subscription_months > 0:
                company.subscription_ends_at = datetime.now() + timedelta(
                    days=subscription_months * 30
                )
            else:
                company.subscription_ends_at = None
        else:
            # Si es trial, limpiar subscription_ends_at
            company.subscription_ends_at = None

        after = _company_snapshot(company)

        session.add(company)
        await _write_audit(
            session,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_company=company,
            action="change_plan",
            before=before,
            after=after,
            reason=reason.strip(),
            ip_address=ip_address,
        )
        await session.commit()

        logger.info(
            f"Owner {actor_email} cambió plan de empresa {company.name} "
            f"({before['plan_type']} → {new_plan})"
        )
        return after

    @staticmethod
    async def change_status(
        session: AsyncSession,
        *,
        company_id: int,
        new_status: str,
        actor_user_id: int,
        actor_email: str,
        reason: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cambia el estado de suscripción con validación de transición."""
        if not reason or not reason.strip():
            raise OwnerServiceError("El motivo es obligatorio.")

        valid_statuses = [s.value for s in SubscriptionStatus]
        if new_status not in valid_statuses:
            raise OwnerServiceError(
                f"Estado inválido: {new_status}. Válidos: {valid_statuses}"
            )

        company = await session.get(Company, company_id)
        if not company:
            raise OwnerServiceError(f"Empresa {company_id} no encontrada.")

        current = company.subscription_status
        if current == new_status:
            raise OwnerServiceError(
                f"La empresa ya tiene estado '{new_status}'."
            )

        # Validar transición
        allowed = VALID_STATUS_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise OwnerServiceError(
                f"Transición inválida: '{current}' → '{new_status}'. "
                f"Transiciones permitidas desde '{current}': {allowed}"
            )

        before = _company_snapshot(company)

        company.subscription_status = new_status

        # Si se suspende, desactivar la empresa
        if new_status == SubscriptionStatus.SUSPENDED:
            company.is_active = False

        # Si se activa, reactivar la empresa
        if new_status == SubscriptionStatus.ACTIVE:
            company.is_active = True

        after = _company_snapshot(company)

        # Determinar acción descriptiva
        action = "change_status"
        if new_status == SubscriptionStatus.SUSPENDED:
            action = "suspend"
        elif new_status == SubscriptionStatus.ACTIVE and current == SubscriptionStatus.SUSPENDED:
            action = "reactivate"
        elif new_status == SubscriptionStatus.ACTIVE:
            action = "activate"

        session.add(company)
        await _write_audit(
            session,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_company=company,
            action=action,
            before=before,
            after=after,
            reason=reason.strip(),
            ip_address=ip_address,
        )
        await session.commit()

        logger.info(
            f"Owner {actor_email} cambió status de empresa {company.name} "
            f"({current} → {new_status})"
        )
        return after

    @staticmethod
    async def extend_trial(
        session: AsyncSession,
        *,
        company_id: int,
        extra_days: int,
        actor_user_id: int,
        actor_email: str,
        reason: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extiende el período de prueba de una empresa."""
        if not reason or not reason.strip():
            raise OwnerServiceError("El motivo es obligatorio.")

        if extra_days < 1 or extra_days > 365:
            raise OwnerServiceError(
                "Los días deben estar entre 1 y 365."
            )

        company = await session.get(Company, company_id)
        if not company:
            raise OwnerServiceError(f"Empresa {company_id} no encontrada.")

        if company.plan_type != PlanType.TRIAL:
            raise OwnerServiceError(
                "Solo se puede extender el trial de empresas con plan 'trial'."
            )

        before = _company_snapshot(company)

        base = company.trial_ends_at or datetime.now()
        company.trial_ends_at = base + timedelta(days=extra_days)
        company.is_active = True
        company.subscription_status = SubscriptionStatus.ACTIVE

        after = _company_snapshot(company)

        session.add(company)
        await _write_audit(
            session,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_company=company,
            action="extend_trial",
            before=before,
            after=after,
            reason=reason.strip(),
            ip_address=ip_address,
        )
        await session.commit()

        logger.info(
            f"Owner {actor_email} extendió trial de {company.name} "
            f"en {extra_days} días"
        )
        return after

    @staticmethod
    async def adjust_limits(
        session: AsyncSession,
        *,
        company_id: int,
        max_users: Optional[int] = None,
        max_branches: Optional[int] = None,
        has_reservations_module: Optional[bool] = None,
        has_services_module: Optional[bool] = None,
        has_clients_module: Optional[bool] = None,
        has_credits_module: Optional[bool] = None,
        has_electronic_billing: Optional[bool] = None,
        actor_user_id: int,
        actor_email: str,
        reason: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ajusta los límites y módulos de una empresa."""
        if not reason or not reason.strip():
            raise OwnerServiceError("El motivo es obligatorio.")

        company = await session.get(Company, company_id)
        if not company:
            raise OwnerServiceError(f"Empresa {company_id} no encontrada.")

        before = _company_snapshot(company)

        if max_users is not None:
            if max_users < 1:
                raise OwnerServiceError("max_users debe ser >= 1.")
            company.max_users = max_users

        if max_branches is not None:
            if max_branches < 1:
                raise OwnerServiceError("max_branches debe ser >= 1.")
            company.max_branches = max_branches

        if has_reservations_module is not None:
            company.has_reservations_module = has_reservations_module

        if has_services_module is not None:
            company.has_services_module = has_services_module

        if has_clients_module is not None:
            company.has_clients_module = has_clients_module

        if has_credits_module is not None:
            company.has_credits_module = has_credits_module

        if has_electronic_billing is not None:
            company.has_electronic_billing = has_electronic_billing

        after = _company_snapshot(company)

        if before == after:
            raise OwnerServiceError("No se detectaron cambios en los límites.")

        session.add(company)
        await _write_audit(
            session,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            target_company=company,
            action="adjust_limits",
            before=before,
            after=after,
            reason=reason.strip(),
            ip_address=ip_address,
        )
        await session.commit()

        logger.info(
            f"Owner {actor_email} ajustó límites de {company.name}"
        )
        return after

    # ─── Sincronización masiva de trials expirados ─────

    @staticmethod
    async def sync_expired_trials(
        session: AsyncSession,
        *,
        actor_user_id: int,
        actor_email: str,
        ip_address: Optional[str] = None,
    ) -> int:
        """Suspende todas las empresas con trial expirado que sigan activas.

        Busca empresas donde plan_type='trial', subscription_status='active'
        y trial_ends_at < ahora, y las pasa a 'suspended' con auditoría.

        Returns:
            Número de empresas actualizadas.
        """
        now = datetime.now()
        stmt = select(Company).where(
            Company.plan_type == PlanType.TRIAL,
            Company.subscription_status == SubscriptionStatus.ACTIVE,
            Company.trial_ends_at != None,  # noqa: E711
            Company.trial_ends_at < now,  # type: ignore[operator]
        )
        result = await session.exec(stmt)  # type: ignore[arg-type]
        expired_companies = result.all()

        count = 0
        for company in expired_companies:
            before = _company_snapshot(company)
            company.subscription_status = SubscriptionStatus.SUSPENDED
            company.is_active = False
            after = _company_snapshot(company)

            session.add(company)
            await _write_audit(
                session,
                actor_user_id=actor_user_id,
                actor_email=actor_email,
                target_company=company,
                action="sync_expired_trial",
                before=before,
                after=after,
                reason=f"Trial expirado automáticamente (venció {company.trial_ends_at})",
                ip_address=ip_address,
            )
            count += 1

        if count > 0:
            await session.commit()
            logger.info(
                f"Owner {actor_email} sincronizó {count} trials expirados"
            )

        return count
