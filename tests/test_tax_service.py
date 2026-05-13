"""Tests unitarios para app/services/tax_service.py.

Usa SQLite in-memory para aislar los tests de la BD de producción.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-tax-service-32-chars-xx")
os.environ.setdefault("TENANT_STRICT", "0")

from app.models.taxes import CompanyTaxRate
from app.services import tax_service
from app.utils.tenant import tenant_bypass


@pytest.fixture
def session():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(eng)
    with tenant_bypass(), Session(eng) as sess:
        yield sess
        sess.rollback()
    eng.dispose()


def _make_rate(
    session: Session,
    company_id: int,
    *,
    tax_name: str = "IGV",
    label: str = "Estándar",
    rate: Decimal = Decimal("18.00"),
    is_default: bool = False,
    is_active: bool = True,
    display_order: int = 1,
) -> CompanyTaxRate:
    obj = CompanyTaxRate(
        company_id=company_id,
        tax_name=tax_name,
        label=label,
        rate=rate,
        is_default=is_default,
        is_active=is_active,
        display_order=display_order,
    )
    session.add(obj)
    session.flush()
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# get_company_tax_rates
# ─────────────────────────────────────────────────────────────────────────────


class TestGetCompanyTaxRates:
    def test_returns_active_rates(self, session):
        company_id = 100
        _make_rate(session, company_id, label="A", is_active=True)
        _make_rate(session, company_id, label="B", is_active=False)

        rates = tax_service.get_company_tax_rates(company_id, session)
        assert len(rates) == 1
        assert rates[0].label == "A"

    def test_empty_when_no_rates(self, session):
        assert tax_service.get_company_tax_rates(999, session) == []

    def test_ordered_by_display_order(self, session):
        company_id = 101
        _make_rate(session, company_id, label="Last", display_order=3)
        _make_rate(session, company_id, label="First", display_order=1)
        _make_rate(session, company_id, label="Mid", display_order=2)

        rates = tax_service.get_company_tax_rates(company_id, session)
        assert [r.label for r in rates] == ["First", "Mid", "Last"]

    def test_scoped_to_company(self, session):
        _make_rate(session, 200, label="Empresa A")
        _make_rate(session, 201, label="Empresa B")

        rates_200 = tax_service.get_company_tax_rates(200, session)
        labels = [r.label for r in rates_200]
        assert "Empresa A" in labels
        assert "Empresa B" not in labels


# ─────────────────────────────────────────────────────────────────────────────
# get_default_rate
# ─────────────────────────────────────────────────────────────────────────────


class TestGetDefaultRate:
    def test_returns_default_as_fraction(self, session):
        company_id = 300
        _make_rate(session, company_id, rate=Decimal("18.00"), is_default=True)

        rate = tax_service.get_default_rate(company_id, session)
        assert rate == Decimal("0.18")

    def test_fallback_to_first_active_when_no_default(self, session):
        company_id = 301
        _make_rate(session, company_id, rate=Decimal("21.00"), is_default=False, display_order=1)

        rate = tax_service.get_default_rate(company_id, session)
        assert rate == Decimal("0.21")

    def test_fallback_constant_when_no_rates(self, session):
        rate = tax_service.get_default_rate(9999, session)
        assert rate == Decimal("0.18")


# ─────────────────────────────────────────────────────────────────────────────
# initialize_country_defaults
# ─────────────────────────────────────────────────────────────────────────────


class TestInitializeCountryDefaults:
    def test_creates_pe_preset(self, session):
        company_id = 400
        tax_service.initialize_country_defaults(company_id, "PE", session)

        rates = tax_service.get_company_tax_rates(company_id, session)
        assert len(rates) == 1
        assert rates[0].tax_name == "IGV"
        assert rates[0].rate == Decimal("18.00")
        assert rates[0].is_default is True

    def test_creates_ar_presets(self, session):
        company_id = 401
        tax_service.initialize_country_defaults(company_id, "AR", session)

        rates = tax_service.get_company_tax_rates(company_id, session)
        assert len(rates) == 3
        assert all(r.tax_name == "IVA" for r in rates)
        rate_values = {r.label: r.rate for r in rates}
        assert rate_values["Estándar"] == Decimal("21.00")
        assert rate_values["Reducida"] == Decimal("10.50")
        assert rate_values["Incrementada"] == Decimal("27.00")

    def test_soft_deletes_previous_rates(self, session):
        company_id = 402
        old = _make_rate(session, company_id, label="Old", is_active=True)
        session.flush()

        tax_service.initialize_country_defaults(company_id, "PE", session)

        session.refresh(old)
        assert old.is_active is False

    def test_reinitialize_replaces_rates(self, session):
        company_id = 403
        tax_service.initialize_country_defaults(company_id, "PE", session)
        tax_service.initialize_country_defaults(company_id, "AR", session)

        rates = tax_service.get_company_tax_rates(company_id, session)
        assert all(r.tax_name == "IVA" for r in rates)

    def test_unknown_country_uses_fallback(self, session):
        company_id = 404
        tax_service.initialize_country_defaults(company_id, "ZZ", session)

        rates = tax_service.get_company_tax_rates(company_id, session)
        assert len(rates) == 1
        assert rates[0].is_default is True


# ─────────────────────────────────────────────────────────────────────────────
# upsert_tax_rate
# ─────────────────────────────────────────────────────────────────────────────


class TestUpsertTaxRate:
    def test_creates_new_rate(self, session):
        company_id = 500
        obj = tax_service.upsert_tax_rate(
            company_id=company_id,
            tax_name="IGV",
            label="Estándar",
            rate=Decimal("18.00"),
            is_default=True,
            session=session,
        )
        assert obj.id is not None
        assert obj.rate == Decimal("18.00")
        assert obj.is_default is True

    def test_updates_existing_rate(self, session):
        company_id = 501
        existing = _make_rate(session, company_id, label="Old Label", rate=Decimal("18.00"))

        updated = tax_service.upsert_tax_rate(
            company_id=company_id,
            tax_name="IGV",
            label="New Label",
            rate=Decimal("19.00"),
            is_default=False,
            session=session,
            rate_id=existing.id,
        )
        assert updated.id == existing.id
        assert updated.label == "New Label"
        assert updated.rate == Decimal("19.00")

    def test_setting_default_clears_others(self, session):
        company_id = 502
        r1 = _make_rate(session, company_id, label="A", is_default=True)
        r2 = _make_rate(session, company_id, label="B", is_default=False)

        tax_service.upsert_tax_rate(
            company_id=company_id,
            tax_name="IVA",
            label="B",
            rate=Decimal("21.00"),
            is_default=True,
            session=session,
            rate_id=r2.id,
        )
        session.refresh(r1)
        assert r1.is_default is False

    def test_raises_for_nonexistent_rate_id(self, session):
        with pytest.raises(ValueError, match="no encontrada"):
            tax_service.upsert_tax_rate(
                company_id=999,
                tax_name="X",
                label="Y",
                rate=Decimal("5.00"),
                is_default=False,
                session=session,
                rate_id=99999,
            )


# ─────────────────────────────────────────────────────────────────────────────
# set_default_rate
# ─────────────────────────────────────────────────────────────────────────────


class TestSetDefaultRate:
    def test_promotes_rate_to_default(self, session):
        company_id = 600
        r1 = _make_rate(session, company_id, label="A", is_default=True)
        r2 = _make_rate(session, company_id, label="B", is_default=False)

        tax_service.set_default_rate(r2.id, company_id, session)

        session.refresh(r1)
        session.refresh(r2)
        assert r2.is_default is True
        assert r1.is_default is False


# ─────────────────────────────────────────────────────────────────────────────
# delete_tax_rate
# ─────────────────────────────────────────────────────────────────────────────


class TestDeleteTaxRate:
    def test_soft_deletes_rate(self, session):
        company_id = 700
        r = _make_rate(session, company_id, label="A", is_default=False)

        tax_service.delete_tax_rate(r.id, company_id, session)

        session.refresh(r)
        assert r.is_active is False

    def test_promotes_next_when_default_deleted(self, session):
        company_id = 701
        r1 = _make_rate(session, company_id, label="A", is_default=True, display_order=1)
        r2 = _make_rate(session, company_id, label="B", is_default=False, display_order=2)

        tax_service.delete_tax_rate(r1.id, company_id, session)

        session.refresh(r2)
        assert r2.is_default is True

    def test_noop_for_nonexistent_id(self, session):
        tax_service.delete_tax_rate(99999, 999, session)


# ─────────────────────────────────────────────────────────────────────────────
# _compute_fiscal_amounts (regresión)
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeFiscalAmounts:
    def test_18_percent(self):
        from unittest.mock import MagicMock
        from app.services.billing_service import _compute_fiscal_amounts

        sale = MagicMock()
        sale.total_amount = Decimal("118.00")
        base, tax, total = _compute_fiscal_amounts(sale, [], tax_rate=Decimal("0.18"))
        assert base == Decimal("100.00")
        assert tax == Decimal("18.00")
        assert total == Decimal("118.00")

    def test_21_percent(self):
        from unittest.mock import MagicMock
        from app.services.billing_service import _compute_fiscal_amounts

        sale = MagicMock()
        sale.total_amount = Decimal("121.00")
        base, tax, total = _compute_fiscal_amounts(sale, [], tax_rate=Decimal("0.21"))
        assert base == Decimal("100.00")
        assert tax == Decimal("21.00")

    def test_10_5_percent(self):
        from unittest.mock import MagicMock
        from app.services.billing_service import _compute_fiscal_amounts

        sale = MagicMock()
        sale.total_amount = Decimal("110.50")
        base, tax, total = _compute_fiscal_amounts(sale, [], tax_rate=Decimal("0.105"))
        assert base + tax == total

    def test_zero_rate(self):
        from unittest.mock import MagicMock
        from app.services.billing_service import _compute_fiscal_amounts

        sale = MagicMock()
        sale.total_amount = Decimal("100.00")
        base, tax, total = _compute_fiscal_amounts(sale, [], tax_rate=Decimal("0"))
        assert base == Decimal("100.00")
        assert tax == Decimal("0.00")
