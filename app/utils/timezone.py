from __future__ import annotations

import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for environments without tzdata
    ZoneInfo = None  # type: ignore

from app.utils.db_seeds import get_country_config

DEFAULT_TZ = "UTC"


def _resolve_timezone_key(
    country_code: str | None,
    timezone: str | None = None,
) -> str:
    tz_key = (timezone or "").strip()
    if tz_key:
        return tz_key
    config = get_country_config(country_code or "PE")
    tz_key = config.get("timezone") or DEFAULT_TZ
    return tz_key


def is_valid_timezone(timezone: str | None) -> bool:
    tz_key = (timezone or "").strip()
    if not tz_key:
        return True
    if ZoneInfo is None:
        return True
    try:
        ZoneInfo(tz_key)
        return True
    except Exception:
        return False


def country_now(
    country_code: str | None,
    timezone: str | None = None,
) -> datetime.datetime:
    tz_key = _resolve_timezone_key(country_code, timezone)
    if ZoneInfo is not None:
        try:
            return datetime.datetime.now(ZoneInfo(tz_key))
        except Exception:
            pass
    return datetime.datetime.now()


def country_today_date(
    country_code: str | None,
    timezone: str | None = None,
) -> datetime.date:
    return country_now(country_code, timezone=timezone).date()


def country_today_start(
    country_code: str | None,
    timezone: str | None = None,
) -> datetime.datetime:
    now = country_now(country_code, timezone=timezone)
    return now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


def argentina_now() -> datetime.datetime:
    return country_now("AR")


def argentina_today_date() -> datetime.date:
    return country_today_date("AR")


def argentina_today_start() -> datetime.datetime:
    return country_today_start("AR")
