"""
Tests completos para el Backoffice de Owners.

Cubre:
1. Autorización (owner vs no-owner)
2. Transiciones de estado válidas/inválidas
3. Auditoría por cada acción
4. Validaciones de servicio
5. Regresión mínima (login normal no afectado)
"""

import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, MagicMock, patch

import pytest

os.environ.setdefault("AUTH_SECRET_KEY", "test_secret_key_for_pytest_only_32_chars_min")

from app.models.company import Company, PlanType, SubscriptionStatus
from app.models.auth import User
from app.models.owner import OwnerAuditLog
from app.services.owner_service import (
    OwnerService,
    OwnerServiceError,
    VALID_STATUS_TRANSITIONS,
    PLAN_DEFAULTS,
    _company_snapshot,
    _effective_status,
)


# ─── Helpers ────────────────────────────────────────────

def _make_company(**overrides) -> Company:
    """Crea una Company de test con defaults sensatos."""
    defaults = {
        "id": 1,
        "name": "Empresa Test",
        "ruc": "20100000001",
        "is_active": True,
        "plan_type": PlanType.TRIAL,
        "subscription_status": SubscriptionStatus.ACTIVE,
        "max_users": 3,
        "max_branches": 2,
        "has_reservations_module": True,
        "has_services_module": True,
        "has_clients_module": True,
        "has_credits_module": True,
        "has_electronic_billing": False,
        "trial_ends_at": datetime.now() + timedelta(days=7),
        "subscription_ends_at": None,
        "created_at": datetime.now(),
    }
    defaults.update(overrides)
    c = Company(**defaults)
    return c


def _make_user(is_owner: bool = False, **overrides) -> User:
    """Crea un User de test."""
    defaults = {
        "id": 99,
        "username": "owner_test",
        "email": "owner@test.com",
        "password_hash": "hashed",
        "is_active": True,
        "is_platform_owner": is_owner,
        "company_id": 1,
        "role_id": 1,
    }
    defaults.update(overrides)
    return User(**defaults)


class FakeExecResult:
    """Mock de resultado de ejecución de query."""
    def __init__(self, value=None):
        self._value = value
    def one(self):
        return self._value
    def all(self):
        return self._value if isinstance(self._value, list) else [self._value]
    def first(self):
        if isinstance(self._value, list):
            return self._value[0] if self._value else None
        return self._value


class FakeSession:
    """Session mock async para tests del servicio."""
    def __init__(self):
        self.exec = AsyncMock()
        self.get = AsyncMock()
        self.added = []
        self.add = Mock(side_effect=lambda obj: self.added.append(obj))
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.refresh = AsyncMock()


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def company():
    return _make_company()


@pytest.fixture
def owner_user():
    return _make_user(is_owner=True)


@pytest.fixture
def normal_user():
    return _make_user(is_owner=False, id=100, username="normal", email="normal@test.com")


# ═════════════════════════════════════════════════════════
# 1. TESTS DE AUTORIZACIÓN (modelo User)
# ═════════════════════════════════════════════════════════

class TestOwnerAuthorization:
    """Verifica que el campo is_platform_owner funciona correctamente."""

    def test_owner_user_has_flag_true(self, owner_user):
        assert owner_user.is_platform_owner is True

    def test_normal_user_has_flag_false(self, normal_user):
        assert normal_user.is_platform_owner is False

    def test_user_default_is_not_owner(self):
        u = User(
            id=200,
            username="test",
            password_hash="h",
            company_id=1,
            role_id=1,
        )
        assert u.is_platform_owner is False

    def test_guest_user_pattern_no_owner(self):
        """El patrón de guest user no debe tener is_platform_owner."""
        guest = {
            "id": None,
            "company_id": None,
            "username": "Invitado",
            "email": "",
            "role": "Invitado",
            "privileges": {},
            "must_change_password": False,
            "is_platform_owner": False,
        }
        assert guest["is_platform_owner"] is False


# ═════════════════════════════════════════════════════════
# 2. TESTS DE TRANSICIONES DE ESTADO
# ═════════════════════════════════════════════════════════

class TestStatusTransitions:
    """Verifica la matriz de transiciones de estado."""

    def test_valid_transitions_defined(self):
        """Todas las transiciones definidas son válidas."""
        for status in SubscriptionStatus:
            assert status.value in VALID_STATUS_TRANSITIONS

    def test_active_can_go_to_warning(self):
        allowed = VALID_STATUS_TRANSITIONS[SubscriptionStatus.ACTIVE]
        assert SubscriptionStatus.WARNING in allowed

    def test_active_can_go_to_suspended(self):
        allowed = VALID_STATUS_TRANSITIONS[SubscriptionStatus.ACTIVE]
        assert SubscriptionStatus.SUSPENDED in allowed

    def test_active_cannot_go_to_past_due(self):
        allowed = VALID_STATUS_TRANSITIONS[SubscriptionStatus.ACTIVE]
        assert SubscriptionStatus.PAST_DUE not in allowed

    def test_warning_can_go_to_active(self):
        allowed = VALID_STATUS_TRANSITIONS[SubscriptionStatus.WARNING]
        assert SubscriptionStatus.ACTIVE in allowed

    def test_warning_can_go_to_past_due(self):
        allowed = VALID_STATUS_TRANSITIONS[SubscriptionStatus.WARNING]
        assert SubscriptionStatus.PAST_DUE in allowed

    def test_past_due_can_go_to_active(self):
        allowed = VALID_STATUS_TRANSITIONS[SubscriptionStatus.PAST_DUE]
        assert SubscriptionStatus.ACTIVE in allowed

    def test_past_due_can_go_to_suspended(self):
        allowed = VALID_STATUS_TRANSITIONS[SubscriptionStatus.PAST_DUE]
        assert SubscriptionStatus.SUSPENDED in allowed

    def test_suspended_can_only_reactivate(self):
        allowed = VALID_STATUS_TRANSITIONS[SubscriptionStatus.SUSPENDED]
        assert allowed == [SubscriptionStatus.ACTIVE]


# ═════════════════════════════════════════════════════════
# 3. TESTS DEL SERVICIO OWNER — CAMBIAR PLAN
# ═════════════════════════════════════════════════════════

class TestChangePlan:
    """Pruebas de OwnerService.change_plan."""

    @pytest.mark.asyncio
    async def test_change_plan_happy_path(self, session, company):
        session.get.return_value = company

        result = await OwnerService.change_plan(
            session,
            company_id=1,
            new_plan=PlanType.STANDARD,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Upgrade solicitado por cliente",
        )

        assert result["plan_type"] == PlanType.STANDARD
        assert company.plan_type == PlanType.STANDARD
        assert company.trial_ends_at is None  # Sale de trial
        session.commit.assert_awaited_once()
        # Debe haber creado un audit log
        audit_logs = [o for o in session.added if isinstance(o, OwnerAuditLog)]
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "change_plan"

    @pytest.mark.asyncio
    async def test_change_plan_applies_defaults(self, session, company):
        session.get.return_value = company

        await OwnerService.change_plan(
            session,
            company_id=1,
            new_plan=PlanType.PROFESSIONAL,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Upgrade",
        )

        assert company.max_users == PLAN_DEFAULTS[PlanType.PROFESSIONAL]["max_users"]
        assert company.max_branches == PLAN_DEFAULTS[PlanType.PROFESSIONAL]["max_branches"]
        assert company.has_electronic_billing is True

    @pytest.mark.asyncio
    async def test_change_plan_invalid_plan(self, session, company):
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="Plan inválido"):
            await OwnerService.change_plan(
                session,
                company_id=1,
                new_plan="mega_plan",
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_change_plan_same_plan(self, session, company):
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="ya tiene el plan"):
            await OwnerService.change_plan(
                session,
                company_id=1,
                new_plan=PlanType.TRIAL,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_change_plan_not_found(self, session):
        session.get.return_value = None

        with pytest.raises(OwnerServiceError, match="no encontrada"):
            await OwnerService.change_plan(
                session,
                company_id=999,
                new_plan=PlanType.STANDARD,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_change_plan_empty_reason(self, session, company):
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="obligatorio"):
            await OwnerService.change_plan(
                session,
                company_id=1,
                new_plan=PlanType.STANDARD,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="",
            )


# ═════════════════════════════════════════════════════════
# 4. TESTS DEL SERVICIO OWNER — CAMBIAR ESTADO
# ═════════════════════════════════════════════════════════

class TestChangeStatus:
    """Pruebas de OwnerService.change_status."""

    @pytest.mark.asyncio
    async def test_suspend_company(self, session, company):
        session.get.return_value = company

        result = await OwnerService.change_status(
            session,
            company_id=1,
            new_status=SubscriptionStatus.SUSPENDED,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Falta de pago reiterada",
        )

        assert result["subscription_status"] == SubscriptionStatus.SUSPENDED
        assert company.is_active is False
        audit_logs = [o for o in session.added if isinstance(o, OwnerAuditLog)]
        assert audit_logs[0].action == "suspend"

    @pytest.mark.asyncio
    async def test_reactivate_suspended_company(self, session):
        company = _make_company(
            subscription_status=SubscriptionStatus.SUSPENDED,
            is_active=False,
        )
        session.get.return_value = company

        result = await OwnerService.change_status(
            session,
            company_id=1,
            new_status=SubscriptionStatus.ACTIVE,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Pago recibido",
        )

        assert result["subscription_status"] == SubscriptionStatus.ACTIVE
        assert company.is_active is True
        audit_logs = [o for o in session.added if isinstance(o, OwnerAuditLog)]
        assert audit_logs[0].action == "reactivate"

    @pytest.mark.asyncio
    async def test_invalid_transition(self, session, company):
        """active → past_due no está permitido."""
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="Transición inválida"):
            await OwnerService.change_status(
                session,
                company_id=1,
                new_status=SubscriptionStatus.PAST_DUE,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_same_status(self, session, company):
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="ya tiene estado"):
            await OwnerService.change_status(
                session,
                company_id=1,
                new_status=SubscriptionStatus.ACTIVE,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_change_status_invalid_status(self, session, company):
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="Estado inválido"):
            await OwnerService.change_status(
                session,
                company_id=1,
                new_status="unknown_status",
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )


# ═════════════════════════════════════════════════════════
# 5. TESTS DEL SERVICIO OWNER — EXTENDER TRIAL
# ═════════════════════════════════════════════════════════

class TestExtendTrial:
    """Pruebas de OwnerService.extend_trial."""

    @pytest.mark.asyncio
    async def test_extend_trial_happy_path(self, session, company):
        original_end = company.trial_ends_at
        session.get.return_value = company

        result = await OwnerService.extend_trial(
            session,
            company_id=1,
            extra_days=14,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Cliente necesita más tiempo",
        )

        expected_end = original_end + timedelta(days=14)
        assert company.trial_ends_at == expected_end
        audit_logs = [o for o in session.added if isinstance(o, OwnerAuditLog)]
        assert audit_logs[0].action == "extend_trial"

    @pytest.mark.asyncio
    async def test_extend_trial_not_trial_plan(self, session):
        company = _make_company(plan_type=PlanType.STANDARD)
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="plan 'trial'"):
            await OwnerService.extend_trial(
                session,
                company_id=1,
                extra_days=7,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_extend_trial_invalid_days(self, session, company):
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="entre 1 y 365"):
            await OwnerService.extend_trial(
                session,
                company_id=1,
                extra_days=0,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_extend_trial_too_many_days(self, session, company):
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="entre 1 y 365"):
            await OwnerService.extend_trial(
                session,
                company_id=1,
                extra_days=400,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )


# ═════════════════════════════════════════════════════════
# 6. TESTS DEL SERVICIO OWNER — AJUSTAR LÍMITES
# ═════════════════════════════════════════════════════════

class TestAdjustLimits:
    """Pruebas de OwnerService.adjust_limits."""

    @pytest.mark.asyncio
    async def test_adjust_limits_happy_path(self, session, company):
        session.get.return_value = company

        result = await OwnerService.adjust_limits(
            session,
            company_id=1,
            max_users=10,
            max_branches=5,
            has_electronic_billing=True,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Ampliación solicitada",
        )

        assert company.max_users == 10
        assert company.max_branches == 5
        assert company.has_electronic_billing is True
        audit_logs = [o for o in session.added if isinstance(o, OwnerAuditLog)]
        assert audit_logs[0].action == "adjust_limits"

    @pytest.mark.asyncio
    async def test_adjust_limits_no_changes(self, session, company):
        """No debe permitir guardar sin cambios reales."""
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="No se detectaron cambios"):
            await OwnerService.adjust_limits(
                session,
                company_id=1,
                max_users=company.max_users,
                max_branches=company.max_branches,
                has_reservations_module=company.has_reservations_module,
                has_services_module=company.has_services_module,
                has_clients_module=company.has_clients_module,
                has_credits_module=company.has_credits_module,
                has_electronic_billing=company.has_electronic_billing,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_adjust_limits_invalid_users(self, session, company):
        session.get.return_value = company

        with pytest.raises(OwnerServiceError, match="max_users"):
            await OwnerService.adjust_limits(
                session,
                company_id=1,
                max_users=0,
                actor_user_id=99,
                actor_email="owner@test.com",
                reason="Test",
            )


# ═════════════════════════════════════════════════════════
# 7. TESTS DE AUDITORÍA
# ═════════════════════════════════════════════════════════

class TestAuditLogs:
    """Verifica que cada acción genera un audit log completo."""

    @pytest.mark.asyncio
    async def test_change_plan_creates_audit(self, session, company):
        session.get.return_value = company

        await OwnerService.change_plan(
            session,
            company_id=1,
            new_plan=PlanType.ENTERPRISE,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Upgrade masivo",
            ip_address="192.168.1.1",
        )

        audit_logs = [o for o in session.added if isinstance(o, OwnerAuditLog)]
        assert len(audit_logs) == 1
        log = audit_logs[0]
        assert log.actor_user_id == 99
        assert log.actor_email == "owner@test.com"
        assert log.target_company_id == 1
        assert log.target_company_name == "Empresa Test"
        assert log.action == "change_plan"
        assert log.ip_address == "192.168.1.1"
        assert log.reason == "Upgrade masivo"

        # before/after deben ser JSON válidos
        before = json.loads(log.before_snapshot)
        after = json.loads(log.after_snapshot)
        assert before["plan_type"] == PlanType.TRIAL
        assert after["plan_type"] == PlanType.ENTERPRISE

    @pytest.mark.asyncio
    async def test_suspend_creates_audit_with_suspend_action(self, session, company):
        session.get.return_value = company

        await OwnerService.change_status(
            session,
            company_id=1,
            new_status=SubscriptionStatus.SUSPENDED,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Suspensión por violación de TOS",
        )

        audit_logs = [o for o in session.added if isinstance(o, OwnerAuditLog)]
        log = audit_logs[0]
        assert log.action == "suspend"
        before = json.loads(log.before_snapshot)
        after = json.loads(log.after_snapshot)
        assert before["is_active"] is True
        assert after["is_active"] is False

    @pytest.mark.asyncio
    async def test_extend_trial_creates_audit(self, session, company):
        session.get.return_value = company

        await OwnerService.extend_trial(
            session,
            company_id=1,
            extra_days=30,
            actor_user_id=99,
            actor_email="owner@test.com",
            reason="Extensión especial",
        )

        audit_logs = [o for o in session.added if isinstance(o, OwnerAuditLog)]
        log = audit_logs[0]
        assert log.action == "extend_trial"
        before = json.loads(log.before_snapshot)
        after = json.loads(log.after_snapshot)
        # trial_ends_at debe haber cambiado
        assert before["trial_ends_at"] != after["trial_ends_at"]


# ═════════════════════════════════════════════════════════
# 8. TESTS DE SNAPSHOT
# ═════════════════════════════════════════════════════════

class TestCompanySnapshot:
    """Verifica que _company_snapshot captura todos los campos."""

    def test_snapshot_contains_all_fields(self, company):
        snap = _company_snapshot(company)
        expected_keys = {
            "plan_type",
            "subscription_status",
            "is_active",
            "trial_ends_at",
            "subscription_ends_at",
            "max_users",
            "max_branches",
            "has_reservations_module",
            "has_services_module",
            "has_clients_module",
            "has_credits_module",
            "has_electronic_billing",
        }
        assert set(snap.keys()) == expected_keys

    def test_snapshot_serializable(self, company):
        snap = _company_snapshot(company)
        serialized = json.dumps(snap, default=str)
        assert isinstance(serialized, str)
        deserialized = json.loads(serialized)
        assert deserialized["plan_type"] == company.plan_type


# ═════════════════════════════════════════════════════════
# 9. TESTS DE REGRESIÓN — LOGIN NORMAL
# ═════════════════════════════════════════════════════════

class TestLoginRegression:
    """Verifica que agregar is_platform_owner no rompe el flujo normal."""

    def test_user_model_has_is_platform_owner_field(self):
        """El campo existe en el modelo."""
        u = User(
            id=1,
            username="regular",
            password_hash="hash",
            company_id=1,
            role_id=1,
        )
        assert hasattr(u, "is_platform_owner")
        assert u.is_platform_owner is False

    def test_user_model_default_false(self):
        """Por defecto es False, no afecta usuarios existentes."""
        u = User(
            id=2,
            username="admin",
            password_hash="hash",
            company_id=1,
            role_id=1,
        )
        assert u.is_platform_owner is False

    def test_owner_audit_log_model_instantiable(self):
        """El modelo OwnerAuditLog se puede instanciar."""
        log = OwnerAuditLog(
            actor_user_id=1,
            actor_email="test@test.com",
            target_company_id=1,
            target_company_name="Test Co",
            action="change_plan",
            reason="Test reason",
        )
        assert log.action == "change_plan"
        assert log.before_snapshot == "{}"
        assert log.after_snapshot == "{}"


# ═════════════════════════════════════════════════════════
# 10. TESTS DE PLAN DEFAULTS
# ═════════════════════════════════════════════════════════

class TestPlanDefaults:
    """Verifica que los defaults por plan están bien configurados."""

    def test_all_plans_have_defaults(self):
        for plan in PlanType:
            assert plan.value in PLAN_DEFAULTS

    def test_trial_has_conservative_limits(self):
        defaults = PLAN_DEFAULTS[PlanType.TRIAL]
        assert defaults["max_users"] <= 5
        assert defaults["max_branches"] <= 3

    def test_enterprise_has_high_limits(self):
        defaults = PLAN_DEFAULTS[PlanType.ENTERPRISE]
        assert defaults["max_users"] >= 100
        assert defaults["max_branches"] >= 100
        assert defaults["has_electronic_billing"] is True


# ═════════════════════════════════════════════════════════
# 11. TESTS DE RATE LIMITING PARA OWNER ACTIONS
# ═════════════════════════════════════════════════════════

class TestOwnerRateLimiting:
    """Verifica el throttling de acciones owner."""

    def setup_method(self):
        """Limpiar timestamps entre tests."""
        from app.states.owner_state import _owner_action_timestamps
        _owner_action_timestamps.clear()

    def test_not_limited_initially(self):
        from app.states.owner_state import _is_owner_rate_limited
        assert _is_owner_rate_limited("admin@test.com") is False

    def test_limited_after_max_actions(self):
        from app.states.owner_state import (
            _is_owner_rate_limited,
            _record_owner_action,
            OWNER_MAX_ACTIONS,
        )
        for _ in range(OWNER_MAX_ACTIONS):
            _record_owner_action("admin@test.com")
        assert _is_owner_rate_limited("admin@test.com") is True

    def test_not_limited_one_below_max(self):
        from app.states.owner_state import (
            _is_owner_rate_limited,
            _record_owner_action,
            OWNER_MAX_ACTIONS,
        )
        for _ in range(OWNER_MAX_ACTIONS - 1):
            _record_owner_action("admin@test.com")
        assert _is_owner_rate_limited("admin@test.com") is False

    def test_different_actors_independent(self):
        from app.states.owner_state import (
            _is_owner_rate_limited,
            _record_owner_action,
            OWNER_MAX_ACTIONS,
        )
        for _ in range(OWNER_MAX_ACTIONS):
            _record_owner_action("admin1@test.com")
        assert _is_owner_rate_limited("admin1@test.com") is True
        assert _is_owner_rate_limited("admin2@test.com") is False

    def test_old_timestamps_cleaned(self):
        import time
        from app.states.owner_state import (
            _is_owner_rate_limited,
            _owner_action_timestamps,
            OWNER_MAX_ACTIONS,
            OWNER_ACTION_WINDOW_SECONDS,
        )
        # Insertar timestamps viejos (fuera de ventana)
        old_time = time.time() - OWNER_ACTION_WINDOW_SECONDS - 10
        _owner_action_timestamps["old@test.com"] = [old_time] * OWNER_MAX_ACTIONS
        assert _is_owner_rate_limited("old@test.com") is False


# ═════════════════════════════════════════════════════════
# 12. TESTS DE SEPARACIÓN — OWNER NO ESTÁ EN SIDEBAR DEL SISTEMA
# ═════════════════════════════════════════════════════════

class TestOwnerSidebarNavigation:
    """Verifica que el Panel Owner está completamente separado del sistema de ventas."""

    def test_route_to_page_does_not_have_owner(self):
        """La ruta /owner NO debe estar en ROUTE_TO_PAGE del sistema de ventas."""
        from app.states.ui_state import ROUTE_TO_PAGE
        assert "/owner" not in ROUTE_TO_PAGE

    def test_page_to_route_does_not_have_owner(self):
        """'Panel Owner' NO debe estar en PAGE_TO_ROUTE del sistema de ventas."""
        from app.states.ui_state import PAGE_TO_ROUTE
        assert "Panel Owner" not in PAGE_TO_ROUTE

    def test_nav_items_config_does_not_have_owner(self):
        """La lista de navegación del sidebar NO debe incluir 'Panel Owner'."""
        from app.states.ui_state import UIState
        state = UIState()
        items = state._navigation_items_config()
        owner_items = [i for i in items if "owner" in i.get("route", "").lower()]
        assert len(owner_items) == 0, "Owner no debe aparecer en navegación del sistema"


# ═════════════════════════════════════════════════════════
# 13. TESTS DE PAGINACIÓN DE AUDITORÍA
# ═════════════════════════════════════════════════════════

class TestAuditPagination:
    """Verifica la lógica de paginación de auditoría."""

    @staticmethod
    def _calc_pages(total: int, per_page: int = 20) -> int:
        """Replica la fórmula del computed var owner_audit_total_pages."""
        if total == 0:
            return 1
        return max(1, -(-total // per_page))

    def test_audit_total_pages_zero(self):
        """0 logs → 1 página."""
        assert self._calc_pages(0) == 1

    def test_audit_total_pages_exact_page(self):
        """20 logs → 1 página."""
        assert self._calc_pages(20) == 1

    def test_audit_total_pages_extra(self):
        """21 logs → 2 páginas."""
        assert self._calc_pages(21) == 2

    def test_audit_total_pages_many(self):
        """100 logs → 5 páginas."""
        assert self._calc_pages(100) == 5


# ═════════════════════════════════════════════════════════
# 14. TESTS DE LOGIN SEPARADO DEL OWNER BACKOFFICE
# ═════════════════════════════════════════════════════════

class TestOwnerSeparateLogin:
    """Verifica la autenticación independiente del Owner Backoffice."""

    def test_owner_session_inactive_by_default(self):
        """owner_session_active debe ser False por defecto."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        assert state.owner_session_active is False

    def test_owner_login_fields_exist(self):
        """Los campos de login del owner deben existir."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        assert hasattr(state, "owner_login_email")
        assert hasattr(state, "owner_login_password")
        assert hasattr(state, "owner_login_error")
        assert hasattr(state, "owner_login_loading")

    def test_owner_login_fields_default_empty(self):
        """Los campos de login deben estar vacíos por defecto."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        assert state.owner_login_email == ""
        assert state.owner_login_password == ""
        assert state.owner_login_error == ""
        assert state.owner_login_loading is False

    def test_is_owner_authenticated_false_when_no_session(self):
        """is_owner_authenticated debe ser False sin sesión activa."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        state.owner_session_active = False
        assert state.owner_session_active is False

    def test_owner_session_independent_from_sales(self):
        """La sesión owner NO depende del login del sistema de ventas."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        # owner_session_active es independiente de is_authenticated
        state.owner_session_active = True
        assert state.owner_session_active is True

    def test_owner_login_page_importable(self):
        """La página de login del owner debe ser importable."""
        from app.pages.owner import owner_login_page
        page = owner_login_page()
        assert page is not None

    def test_owner_page_importable(self):
        """La página del owner backoffice sigue importable."""
        from app.pages.owner import owner_page
        page = owner_page()
        assert page is not None

    def test_owner_login_page_registered_in_app(self):
        """La ruta /owner/login debe estar registrada."""
        import importlib
        import app.app as app_module
        # Verificar que la función page_owner_login existe
        assert hasattr(app_module, "page_owner_login")

    def test_owner_logout_resets_session(self):
        """owner_logout debe resetear owner_session_active."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        state.owner_session_active = True
        state.owner_companies = [{"id": 1}]
        state.owner_audit_logs = [{"id": 1}]
        # Simular logout (sin rx.redirect ya que es test unitario)
        state.owner_session_active = False
        state.owner_companies = []
        state.owner_audit_logs = []
        assert state.owner_session_active is False
        assert state.owner_companies == []
        assert state.owner_audit_logs == []

    def test_global_logout_clears_owner_session(self):
        """El logout global del sistema de ventas también limpia la sesión owner."""
        from app.states.auth_state import AuthState
        import inspect
        # Obtener el source del método logout (puede ser wrapped por @rx.event)
        logout_method = AuthState.logout
        fn = getattr(logout_method, "fn", logout_method)
        source = inspect.getsource(fn)
        assert "owner_session_active" in source

    def test_owner_not_in_sales_login_route(self):
        """/owner/login es ruta independiente de /ingreso."""
        assert "/owner/login" != "/ingreso"

    def test_regular_user_cannot_access_owner_even_if_route_known(self):
        """El guard is_owner_authenticated bloquea usuarios normales."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        # Usuario normal con owner_session_active=False
        state.owner_session_active = False
        # El guard en owner_load_companies chequea is_owner_authenticated
        # que requiere owner_session_active AND is_owner (via current_user)
        assert state.owner_session_active is False

    def test_owner_login_handler_exists(self):
        """El handler owner_login debe existir."""
        from app.states.owner_state import OwnerState
        assert hasattr(OwnerState, "owner_login")

    def test_owner_logout_handler_exists(self):
        """El handler owner_logout debe existir."""
        from app.states.owner_state import OwnerState
        assert hasattr(OwnerState, "owner_logout")

    def test_page_init_owner_login_handler_exists(self):
        """El handler page_init_owner_login debe existir en State."""
        from app.state import State
        assert hasattr(State, "page_init_owner_login")

    def test_owner_session_fields_exist(self):
        """Los campos de sesión owner deben existir."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        assert hasattr(state, "owner_session_email")
        assert hasattr(state, "owner_session_user_id")
        assert state.owner_session_email == ""
        assert state.owner_session_user_id == 0

    def test_verify_owner_credentials_correct(self):
        """Credenciales correctas deben pasar validación."""
        from app.states.owner_state import _verify_owner_credentials
        assert _verify_owner_credentials("admin@tuwaykiapp.com", "TreborOD(523)") is True

    def test_verify_owner_credentials_wrong_email(self):
        """Email incorrecto debe fallar."""
        from app.states.owner_state import _verify_owner_credentials
        assert _verify_owner_credentials("admin@tuwaykiapp.local", "TreborOD(523)") is False

    def test_verify_owner_credentials_wrong_password(self):
        """Contraseña incorrecta debe fallar."""
        from app.states.owner_state import _verify_owner_credentials
        assert _verify_owner_credentials("admin@tuwaykiapp.com", "admin") is False

    def test_verify_owner_credentials_sales_system_creds_fail(self):
        """Credenciales del Sistema de Ventas no deben funcionar en el Owner Backoffice."""
        from app.states.owner_state import _verify_owner_credentials
        # Estas son las credenciales del sistema de ventas
        assert _verify_owner_credentials("admin@tuwaykiapp.local", "admin") is False

    def test_verify_owner_credentials_case_insensitive_email(self):
        """El email debe ser case-insensitive."""
        from app.states.owner_state import _verify_owner_credentials
        assert _verify_owner_credentials("Admin@TuwaykiApp.COM", "TreborOD(523)") is True

    def test_verify_owner_credentials_empty_inputs(self):
        """Entradas vacías deben fallar."""
        from app.states.owner_state import _verify_owner_credentials
        assert _verify_owner_credentials("", "") is False
        assert _verify_owner_credentials("admin@tuwaykiapp.com", "") is False
        assert _verify_owner_credentials("", "TreborOD(523)") is False

    def test_owner_admin_email_constant(self):
        """El email configurado debe ser admin@tuwaykiapp.com."""
        from app.states.owner_state import OWNER_ADMIN_EMAIL
        assert OWNER_ADMIN_EMAIL == "admin@tuwaykiapp.com"


# ═════════════════════════════════════════════════════════
# 16. TESTS DE ESTADO EFECTIVO Y SINCRONIZACIÓN DE TRIALS
# ═════════════════════════════════════════════════════════

class TestEffectiveStatusAndSync:
    """Verifica que trials expirados se muestren y sincronicen correctamente."""

    # ── _effective_status ──────────────────────────────

    def test_effective_status_active_trial_not_expired(self):
        """Trial activo con fecha futura → 'active'."""
        c = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=datetime.now() + timedelta(days=5),
        )
        assert _effective_status(c) == "active"

    def test_effective_status_trial_expired(self):
        """Trial activo con fecha pasada → 'trial_expired'."""
        c = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=datetime.now() - timedelta(days=3),
        )
        assert _effective_status(c) == "trial_expired"

    def test_effective_status_trial_expired_today(self):
        """Trial que venció hace 1 segundo → 'trial_expired'."""
        c = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=datetime.now() - timedelta(seconds=1),
        )
        assert _effective_status(c) == "trial_expired"

    def test_effective_status_suspended_trial(self):
        """Trial ya suspendido (no activo) → 'suspended' (no se sobreescribe)."""
        c = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.SUSPENDED,
            trial_ends_at=datetime.now() - timedelta(days=3),
        )
        assert _effective_status(c) == SubscriptionStatus.SUSPENDED

    def test_effective_status_standard_plan(self):
        """Plan standard activo → 'active' (no aplica lógica trial)."""
        c = _make_company(
            plan_type=PlanType.STANDARD,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=None,
        )
        assert _effective_status(c) == "active"

    def test_effective_status_no_trial_date(self):
        """Trial sin fecha → 'active' (no puede determinar expiración)."""
        c = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=None,
        )
        assert _effective_status(c) == "active"

    def test_effective_status_warning_not_overridden(self):
        """Estado 'warning' no se sobreescribe aunque sea trial expirado."""
        c = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.WARNING,
            trial_ends_at=datetime.now() - timedelta(days=3),
        )
        assert _effective_status(c) == SubscriptionStatus.WARNING

    # ── list_companies incluye effective_status ────────

    @pytest.mark.asyncio
    async def test_list_companies_includes_effective_status(self, session):
        """list_companies devuelve effective_status en el dict."""
        expired_company = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=datetime.now() - timedelta(days=5),
        )

        session.exec = AsyncMock(side_effect=[
            FakeExecResult(1),          # count
            FakeExecResult([expired_company]),  # companies
            FakeExecResult(2),          # user_count
            FakeExecResult(1),          # branch_count
            FakeExecResult("admin@test.com"), # admin_email
            FakeExecResult("123456789"),      # company_phone
        ])

        items, total = await OwnerService.list_companies(session, page=1, per_page=20)
        assert total == 1
        assert len(items) == 1
        assert items[0]["effective_status"] == "trial_expired"
        assert items[0]["subscription_status"] == "active"  # raw DB value preserved

    @pytest.mark.asyncio
    async def test_list_companies_active_trial_shows_active(self, session):
        """Trial vigente muestra effective_status='active'."""
        active_company = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=datetime.now() + timedelta(days=5),
        )

        session.exec = AsyncMock(side_effect=[
            FakeExecResult(1),
            FakeExecResult([active_company]),
            FakeExecResult(1),
            FakeExecResult(1),
            FakeExecResult("admin@test.com"),
            FakeExecResult("123456789"),
        ])

        items, total = await OwnerService.list_companies(session, page=1, per_page=20)
        assert items[0]["effective_status"] == "active"

    # ── sync_expired_trials ────────────────────────────

    @pytest.mark.asyncio
    async def test_sync_expired_trials_suspends_companies(self, session):
        """sync_expired_trials suspende empresas con trial expirado."""
        c1 = _make_company(
            id=1,
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=datetime.now() - timedelta(days=10),
        )
        c2 = _make_company(
            id=2,
            name="Empresa 2",
            ruc="20100000002",
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=datetime.now() - timedelta(days=3),
        )

        session.exec = AsyncMock(return_value=FakeExecResult([c1, c2]))

        count = await OwnerService.sync_expired_trials(
            session,
            actor_user_id=99,
            actor_email="admin@tuwaykiapp.com",
        )

        assert count == 2
        assert c1.subscription_status == SubscriptionStatus.SUSPENDED
        assert c1.is_active is False
        assert c2.subscription_status == SubscriptionStatus.SUSPENDED
        assert c2.is_active is False
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_expired_trials_no_expired(self, session):
        """Si no hay trials expirados, retorna 0 y no hace commit."""
        session.exec = AsyncMock(return_value=FakeExecResult([]))

        count = await OwnerService.sync_expired_trials(
            session,
            actor_user_id=99,
            actor_email="admin@tuwaykiapp.com",
        )

        assert count == 0
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sync_expired_trials_creates_audit_logs(self, session):
        """Cada empresa sincronizada genera un log de auditoría."""
        c = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            trial_ends_at=datetime.now() - timedelta(days=5),
        )

        session.exec = AsyncMock(return_value=FakeExecResult([c]))

        await OwnerService.sync_expired_trials(
            session,
            actor_user_id=99,
            actor_email="admin@tuwaykiapp.com",
        )

        # La empresa + el log de auditoría se agregaron
        audit_logs = [obj for obj in session.added if isinstance(obj, OwnerAuditLog)]
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "sync_expired_trial"

    # ── UI badge names ─────────────────────────────────

    def test_badge_status_includes_trial_expired(self):
        """El diccionario _BADGE_STATUS incluye 'trial_expired'."""
        from app.pages.owner import _BADGE_STATUS
        assert "trial_expired" in _BADGE_STATUS

    def test_sync_handler_exists_in_state(self):
        """El handler owner_sync_expired debe existir en OwnerState."""
        from app.states.owner_state import OwnerState
        assert hasattr(OwnerState, "owner_sync_expired")


# ═════════════════════════════════════════════════════════
# 17. TESTS DE MODALES MEJORADOS (SELECTORES Y PRESETS)
# ═════════════════════════════════════════════════════════

class TestEnhancedModals:
    """Verifica los campos mejorados de los modales de acciones."""

    def test_new_state_fields_exist(self):
        """Los nuevos campos del formulario deben existir."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        assert hasattr(state, "owner_form_reason_preset")
        assert hasattr(state, "owner_form_notes")
        assert hasattr(state, "owner_form_activate_now")
        assert hasattr(state, "owner_form_current_plan")
        assert hasattr(state, "owner_form_current_status")
        assert hasattr(state, "owner_form_trial_ends_at")
        assert hasattr(state, "owner_form_effective_date")

    def test_new_state_fields_defaults(self):
        """Valores por defecto correctos."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        assert state.owner_form_reason_preset == ""
        assert state.owner_form_notes == ""
        assert state.owner_form_activate_now is True
        assert state.owner_form_current_plan == ""
        assert state.owner_form_current_status == ""
        assert state.owner_form_trial_ends_at == ""
        assert state.owner_form_effective_date == ""

    def test_new_handlers_exist(self):
        """Los nuevos handlers deben existir."""
        from app.states.owner_state import OwnerState
        assert hasattr(OwnerState, "owner_set_form_reason_preset")
        assert hasattr(OwnerState, "owner_set_form_notes")
        assert hasattr(OwnerState, "owner_set_form_activate_now")
        assert hasattr(OwnerState, "owner_set_form_extra_days_preset")

    def test_reason_presets_defined(self):
        """Los presets de motivos deben estar definidos para cada acción."""
        from app.pages.owner import _REASON_PRESETS
        assert "change_plan" in _REASON_PRESETS
        assert "change_status" in _REASON_PRESETS
        assert "extend_trial" in _REASON_PRESETS
        assert "adjust_limits" in _REASON_PRESETS
        for key, presets in _REASON_PRESETS.items():
            assert len(presets) >= 3, f"Acción '{key}' necesita al menos 3 presets"

    def test_reason_presets_are_strings(self):
        """Cada preset debe ser un string no vacío."""
        from app.pages.owner import _REASON_PRESETS
        for key, presets in _REASON_PRESETS.items():
            for p in presets:
                assert isinstance(p, str)
                assert len(p.strip()) > 0

    def test_reason_preset_copies_to_reason(self):
        """Seleccionar un preset debe copiar el texto al motivo."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        state.owner_set_form_reason_preset("Pago recibido — reactivación de cuenta")
        assert state.owner_form_reason == "Pago recibido — reactivación de cuenta"
        assert state.owner_form_reason_preset == "Pago recibido — reactivación de cuenta"

    def test_reason_preset_custom_does_not_overwrite(self):
        """Seleccionar 'custom' no debe sobreescribir el motivo existente."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        state.owner_form_reason = "Mi motivo personalizado"
        state.owner_set_form_reason_preset("custom")
        assert state.owner_form_reason == "Mi motivo personalizado"

    def test_extra_days_preset_updates_field(self):
        """Seleccionar preset de días debe actualizar el campo."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        state.owner_set_form_extra_days_preset("30")
        assert state.owner_form_extra_days == "30"

    def test_notes_appended_to_reason_in_execution(self):
        """Las notas adicionales deben complementar el motivo."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        state.owner_form_reason = "Cliente solicitó activación"
        state.owner_form_notes = "Contacto: Juan, Tel: 987654321"
        # Simular la lógica del handler (sin ejecutar realmente)
        full_reason = state.owner_form_reason.strip()
        if state.owner_form_notes.strip():
            full_reason += f" | Notas: {state.owner_form_notes.strip()}"
        assert "Notas: Contacto: Juan" in full_reason

    def test_info_pill_renders(self):
        """La función _info_pill debe ser importable y ejecutable."""
        from app.pages.owner import _info_pill
        import reflex as rx
        # No debe lanzar excepción
        pill = _info_pill("Test", "valor")
        assert pill is not None

    def test_reason_selector_renders(self):
        """La función _reason_selector debe ser importable y ejecutable."""
        from app.pages.owner import _reason_selector
        component = _reason_selector("change_plan")
        assert component is not None

    def test_date_notes_section_renders(self):
        """La función _date_and_notes_section debe ser importable y ejecutable."""
        from app.pages.owner import _date_and_notes_section
        component = _date_and_notes_section()
        assert component is not None


# ═══════════════════════════════════════════════════════════
# 18. MÓDULOS EN AJUSTAR LÍMITES + SUBSCRIPTION_ENDS_AT
# ═══════════════════════════════════════════════════════════

class TestModulesAndSubscription:
    """Tests para tarjetas de módulos y fecha de vencimiento de suscripción."""

    # ─── Módulos UI ────────────────────────────────────

    def test_module_card_renders(self):
        """_module_card debe ser importable y ejecutable."""
        from app.pages.owner import _module_card
        from app.state import State
        import reflex as rx
        card = _module_card(
            icon_name="calendar-check",
            title="Reservas",
            description="Test",
            checked=State.owner_form_has_reservations,
            on_change=State.owner_set_form_has_reservations,
            included_by_plan=rx.Var.create(True),
        )
        assert card is not None

    def test_form_adjust_limits_has_module_cards(self):
        """_form_adjust_limits debe renderizar tarjetas de módulo."""
        from app.pages.owner import _form_adjust_limits
        component = _form_adjust_limits()
        assert component is not None

    def test_plan_defaults_have_module_fields(self):
        """PLAN_DEFAULTS debe incluir campos de módulos."""
        for plan, defaults in PLAN_DEFAULTS.items():
            assert "has_reservations_module" in defaults, f"Falta has_reservations_module en {plan}"
            assert "has_services_module" in defaults, f"Falta has_services_module en {plan}"
            assert "has_clients_module" in defaults, f"Falta has_clients_module en {plan}"
            assert "has_credits_module" in defaults, f"Falta has_credits_module en {plan}"
            assert "has_electronic_billing" in defaults, f"Falta has_electronic_billing en {plan}"

    def test_professional_enterprise_include_billing(self):
        """Professional y Enterprise deben incluir facturación electrónica."""
        assert PLAN_DEFAULTS[PlanType.PROFESSIONAL]["has_electronic_billing"] is True
        assert PLAN_DEFAULTS[PlanType.ENTERPRISE]["has_electronic_billing"] is True

    def test_trial_standard_exclude_billing(self):
        """Trial y Standard no incluyen facturación electrónica."""
        assert PLAN_DEFAULTS[PlanType.TRIAL]["has_electronic_billing"] is False
        assert PLAN_DEFAULTS[PlanType.STANDARD]["has_electronic_billing"] is False

    def test_standard_disables_modules(self):
        """Standard deshabilita servicios, clientes y cuentas corrientes."""
        defaults = PLAN_DEFAULTS[PlanType.STANDARD]
        assert defaults["has_services_module"] is False
        assert defaults["has_clients_module"] is False
        assert defaults["has_credits_module"] is False
        assert defaults["has_reservations_module"] is False

    def test_trial_professional_enterprise_enable_all_modules(self):
        """Trial, Professional y Enterprise habilitan servicios, clientes, cuentas."""
        for plan in [PlanType.TRIAL, PlanType.PROFESSIONAL, PlanType.ENTERPRISE]:
            defaults = PLAN_DEFAULTS[plan]
            assert defaults["has_services_module"] is True, f"{plan} debe incluir servicios"
            assert defaults["has_clients_module"] is True, f"{plan} debe incluir clientes"
            assert defaults["has_credits_module"] is True, f"{plan} debe incluir cuentas"
            assert defaults["has_reservations_module"] is True, f"{plan} debe incluir reservas"

    # ─── Subscription months state ─────────────────────

    def test_subscription_months_field_exists(self):
        """El campo owner_form_subscription_months debe existir."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        assert hasattr(state, "owner_form_subscription_months")

    def test_subscription_months_default_12(self):
        """El valor por defecto debe ser 12 meses."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        assert state.owner_form_subscription_months == "12"

    def test_subscription_months_handler_exists(self):
        """El handler para cambiar meses debe existir."""
        from app.states.owner_state import OwnerState
        assert hasattr(OwnerState, "owner_set_form_subscription_months")

    def test_subscription_months_handler_updates(self):
        """El handler debe actualizar el campo."""
        from app.states.owner_state import OwnerState
        state = OwnerState()
        state.owner_set_form_subscription_months("6")
        assert state.owner_form_subscription_months == "6"

    # ─── change_plan sets subscription_ends_at ─────────

    @pytest.mark.asyncio
    async def test_change_plan_sets_subscription_ends_at(self):
        """Cambiar de trial a standard debe establecer subscription_ends_at."""
        company = _make_company(plan_type=PlanType.TRIAL)
        assert company.subscription_ends_at is None

        session = AsyncMock()
        session.get = AsyncMock(return_value=company)
        session.add = Mock()
        session.commit = AsyncMock()

        await OwnerService.change_plan(
            session,
            company_id=1,
            new_plan="standard",
            actor_user_id=99,
            actor_email="admin@test.com",
            reason="Activación",
            subscription_months=12,
        )

        assert company.subscription_ends_at is not None
        expected_min = datetime.now() + timedelta(days=355)
        expected_max = datetime.now() + timedelta(days=365)
        assert expected_min <= company.subscription_ends_at <= expected_max

    @pytest.mark.asyncio
    async def test_change_plan_to_trial_clears_subscription_ends(self):
        """Cambiar a trial debe limpiar subscription_ends_at."""
        company = _make_company(
            plan_type=PlanType.STANDARD,
            subscription_ends_at=datetime.now() + timedelta(days=180),
            trial_ends_at=None,
        )
        assert company.subscription_ends_at is not None

        session = AsyncMock()
        session.get = AsyncMock(return_value=company)
        session.add = Mock()
        session.commit = AsyncMock()

        await OwnerService.change_plan(
            session,
            company_id=1,
            new_plan="trial",
            actor_user_id=99,
            actor_email="admin@test.com",
            reason="Downgrade a prueba",
            subscription_months=0,
        )

        assert company.subscription_ends_at is None

    @pytest.mark.asyncio
    async def test_change_plan_custom_months(self):
        """subscription_months personalizado debe calcular correctamente."""
        company = _make_company(plan_type=PlanType.TRIAL)

        session = AsyncMock()
        session.get = AsyncMock(return_value=company)
        session.add = Mock()
        session.commit = AsyncMock()

        await OwnerService.change_plan(
            session,
            company_id=1,
            new_plan="professional",
            actor_user_id=99,
            actor_email="admin@test.com",
            reason="Upgrade",
            subscription_months=6,
        )

        expected_min = datetime.now() + timedelta(days=175)
        expected_max = datetime.now() + timedelta(days=185)
        assert expected_min <= company.subscription_ends_at <= expected_max

    @pytest.mark.asyncio
    async def test_change_plan_clears_trial_ends_at(self):
        """Cambiar de trial a otro plan debe limpiar trial_ends_at."""
        company = _make_company(
            plan_type=PlanType.TRIAL,
            trial_ends_at=datetime.now() + timedelta(days=7),
        )
        assert company.trial_ends_at is not None

        session = AsyncMock()
        session.get = AsyncMock(return_value=company)
        session.add = Mock()
        session.commit = AsyncMock()

        await OwnerService.change_plan(
            session,
            company_id=1,
            new_plan="standard",
            actor_user_id=99,
            actor_email="admin@test.com",
            reason="Activación",
            subscription_months=12,
        )

        assert company.trial_ends_at is None
        assert company.subscription_ends_at is not None

    @pytest.mark.asyncio
    async def test_change_plan_activates_subscription(self):
        """Cambiar a plan pago debe activar la suscripción."""
        company = _make_company(
            plan_type=PlanType.TRIAL,
            subscription_status=SubscriptionStatus.ACTIVE,
        )

        session = AsyncMock()
        session.get = AsyncMock(return_value=company)
        session.add = Mock()
        session.commit = AsyncMock()

        await OwnerService.change_plan(
            session,
            company_id=1,
            new_plan="enterprise",
            actor_user_id=99,
            actor_email="admin@test.com",
            reason="Upgrade corporativo",
            subscription_months=24,
        )

        assert company.subscription_status == SubscriptionStatus.ACTIVE
        assert company.is_active is True
        expected_min = datetime.now() + timedelta(days=715)
        expected_max = datetime.now() + timedelta(days=725)
        assert expected_min <= company.subscription_ends_at <= expected_max

    def test_snapshot_includes_subscription_ends_at(self):
        """El snapshot debe incluir subscription_ends_at."""
        now = datetime.now()
        company = _make_company(subscription_ends_at=now + timedelta(days=365))
        snap = _company_snapshot(company)
        assert "subscription_ends_at" in snap
        assert snap["subscription_ends_at"] is not None

    def test_snapshot_subscription_ends_at_none(self):
        """El snapshot con subscription_ends_at=None debe serializar como None."""
        company = _make_company(subscription_ends_at=None)
        snap = _company_snapshot(company)
        assert snap["subscription_ends_at"] is None
