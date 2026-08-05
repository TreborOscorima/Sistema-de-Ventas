"""Estado efectivo (Trial Vencido / Suspendido) para empresas FOOD y LIFE.

Verifica que el panel calcule el mismo `effective_status` que ya aplica sobre
las empresas de SHOP, ahora también para los productos consultados por HTTP.
"""
from datetime import datetime, timedelta

from app.utils.timezone import utc_now_naive
from app.services._owner_effective_status import _parse_dt, effective_status
from app.services.food_owner_client import _normalize_food_company
from app.services.life_owner_client import _normalize_life_company

_PAST = "2020-01-01"
_FUTURE = "2999-12-31"


class TestParseDt:
    def test_date_only(self):
        assert _parse_dt("2026-07-18") == datetime(2026, 7, 18)

    def test_iso_with_z(self):
        assert _parse_dt("2026-07-03T11:02:03Z") == datetime(2026, 7, 3, 11, 2, 3)

    def test_empty_and_none(self):
        assert _parse_dt(None) is None
        assert _parse_dt("") is None
        assert _parse_dt("   ") is None

    def test_garbage(self):
        assert _parse_dt("no-es-fecha") is None


class TestEffectiveStatus:
    def test_trial_future_active(self):
        te = (utc_now_naive() + timedelta(days=5)).date().isoformat()
        assert effective_status(
            plan="trial", is_active=True, trial_ends_at=te, plan_expires_at=None
        ) == "active"

    def test_trial_past_expired(self):
        te = (utc_now_naive() - timedelta(days=3)).date().isoformat()
        assert effective_status(
            plan="trial", is_active=True, trial_ends_at=te, plan_expires_at=None
        ) == "trial_expired"

    def test_trial_no_date_expired(self):
        assert effective_status(
            plan="trial", is_active=True, trial_ends_at=None, plan_expires_at=None
        ) == "trial_expired"

    def test_trial_expired_even_if_inactive(self):
        te = (utc_now_naive() - timedelta(days=3)).date().isoformat()
        assert effective_status(
            plan="trial", is_active=False, trial_ends_at=te, plan_expires_at=None
        ) == "trial_expired"

    def test_paid_future_active(self):
        pe = (utc_now_naive() + timedelta(days=30)).date().isoformat()
        assert effective_status(
            plan="profesional", is_active=True, trial_ends_at=None, plan_expires_at=pe
        ) == "active"

    def test_paid_past_suspended(self):
        pe = (utc_now_naive() - timedelta(days=1)).date().isoformat()
        assert effective_status(
            plan="profesional", is_active=True, trial_ends_at=None, plan_expires_at=pe
        ) == "suspended"

    def test_paid_no_date_active(self):
        assert effective_status(
            plan="standard", is_active=True, trial_ends_at=None, plan_expires_at=None
        ) == "active"

    def test_inactive_base_suspended(self):
        pe = (utc_now_naive() + timedelta(days=30)).date().isoformat()
        assert effective_status(
            plan="profesional", is_active=False, trial_ends_at=None, plan_expires_at=pe
        ) == "suspended"


class TestNormalizeWiring:
    def _food_raw(self, **over):
        raw = {
            "id": 1, "name": "X", "slug": "x", "admin_email": "a@x.com",
            "is_active": True, "plan": "trial",
            "trial_ends_at": _FUTURE, "plan_expires_at": None,
        }
        raw.update(over)
        return raw

    def test_food_trial_expired(self):
        c = _normalize_food_company(self._food_raw(trial_ends_at=_PAST))
        assert c["effective_status"] == "trial_expired"
        assert c["subscription_status"] == "active"  # crudo preservado

    def test_food_trial_active(self):
        c = _normalize_food_company(self._food_raw(trial_ends_at=_FUTURE))
        assert c["effective_status"] == "active"

    def test_food_paid_expired_suspended(self):
        c = _normalize_food_company(
            self._food_raw(plan="profesional", trial_ends_at=None, plan_expires_at=_PAST)
        )
        assert c["effective_status"] == "suspended"

    def test_life_trial_expired(self):
        raw = {
            "id": 1, "name": "C", "slug": "c", "admin_email": "a@c.com",
            "is_active": True, "plan": "trial",
            "trial_ends_at": _PAST, "plan_expires_at": None,
        }
        c = _normalize_life_company(raw)
        assert c["effective_status"] == "trial_expired"

    def test_life_paid_active(self):
        raw = {
            "id": 1, "name": "C", "slug": "c", "admin_email": "a@c.com",
            "is_active": True, "plan": "profesional",
            "trial_ends_at": None, "plan_expires_at": _FUTURE,
        }
        c = _normalize_life_company(raw)
        assert c["effective_status"] == "active"
