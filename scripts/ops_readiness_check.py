from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import List
from urllib.parse import quote_plus
import sys

import reflex as rx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlmodel import select

# Permite ejecutar el script directamente desde scripts/.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.models import Branch, Company
from app.services.alert_service import get_alert_summary
from app.utils.logger import get_logger
from app.utils.rate_limit import get_rate_limit_status
from app.utils.tenant import set_tenant_context, tenant_bypass


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | WARN | FAIL
    detail: str


def _db_url(database: str | None = None) -> str:
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    db_name = database or os.getenv("DB_NAME")
    if not user or password is None or not db_name:
        raise RuntimeError("Faltan variables DB_USER/DB_PASSWORD/DB_NAME.")
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db_name}"
    )


def _check_db_latency() -> CheckResult:
    start = perf_counter()
    engine = create_engine(_db_url())
    with engine.begin() as conn:
        conn.execute(text("SELECT 1"))
    elapsed_ms = round((perf_counter() - start) * 1000, 2)
    if elapsed_ms > 500:
        return CheckResult(
            "db_ping_latency",
            "WARN",
            f"latency={elapsed_ms}ms (alto, revisar red/DB pool)",
        )
    return CheckResult("db_ping_latency", "PASS", f"latency={elapsed_ms}ms")


def _check_backup_freshness(hours: int) -> CheckResult:
    db_name = os.getenv("DB_NAME", "sistema_ventas")
    backup_dir = ROOT_DIR / "backups"
    files = sorted(
        backup_dir.glob(f"{db_name}_backup_*.sql*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return CheckResult("backup_freshness", "FAIL", "no hay backups en /backups")
    latest = files[0]
    latest_dt = datetime.fromtimestamp(latest.stat().st_mtime)
    age = datetime.now() - latest_dt
    if age > timedelta(hours=hours):
        return CheckResult(
            "backup_freshness",
            "WARN",
            f"ultimo backup={latest.name} age_hours={age.total_seconds()/3600:.2f}",
        )
    return CheckResult(
        "backup_freshness",
        "PASS",
        f"ultimo backup={latest.name} age_hours={age.total_seconds()/3600:.2f}",
    )


def _check_logger_write() -> CheckResult:
    logger = get_logger("OpsReadiness")
    marker = f"ops-readiness-check {datetime.now().isoformat(timespec='seconds')}"
    logger.warning(marker)
    log_file = ROOT_DIR / "logs" / "app.log"
    if not log_file.exists():
        return CheckResult("logger_write", "FAIL", "logs/app.log no existe")
    text_tail = log_file.read_text(encoding="utf-8", errors="ignore")[-4000:]
    if marker not in text_tail:
        return CheckResult("logger_write", "WARN", "marker no encontrado en tail de logs")
    return CheckResult("logger_write", "PASS", "log write verificado")


def _check_rate_limit_backend(require_redis: bool) -> CheckResult:
    status = get_rate_limit_status()
    backend = status.get("backend")
    strict = bool(status.get("strict_backend"))
    redis_connected = bool(status.get("redis_connected"))
    if require_redis and not redis_connected:
        return CheckResult(
            "rate_limit_backend",
            "FAIL",
            f"backend={backend} strict={strict} redis_connected={redis_connected}",
        )
    if strict and not redis_connected:
        return CheckResult(
            "rate_limit_backend",
            "FAIL",
            f"modo estricto sin Redis (backend={backend})",
        )
    if not redis_connected:
        return CheckResult(
            "rate_limit_backend",
            "WARN",
            f"backend={backend} strict={strict} (Redis no conectado)",
        )
    return CheckResult(
        "rate_limit_backend",
        "PASS",
        f"backend={backend} strict={strict} redis_connected={redis_connected}",
    )


def _check_alert_pipeline() -> CheckResult:
    with tenant_bypass():
        with rx.session() as session:
            company = session.exec(select(Company).order_by(Company.id.desc())).first()
            if not company:
                return CheckResult("alert_pipeline", "WARN", "no hay companies en BD")
            branch = session.exec(
                select(Branch)
                .where(Branch.company_id == company.id)
                .order_by(Branch.id.desc())
            ).first()
            if not branch:
                return CheckResult(
                    "alert_pipeline",
                    "WARN",
                    f"company_id={company.id} sin sucursales",
                )

    set_tenant_context(company.id, branch.id)
    summary = get_alert_summary(company_id=company.id, branch_id=branch.id)
    total = int(summary.get("total", 0))
    critical = int(summary.get("critical", 0))
    error = int(summary.get("error", 0))
    warning = int(summary.get("warning", 0))
    return CheckResult(
        "alert_pipeline",
        "PASS",
        (
            f"company_id={company.id} branch_id={branch.id} "
            f"total={total} critical={critical} error={error} warning={warning}"
        ),
    )


def _check_alembic_version() -> CheckResult:
    engine = create_engine(_db_url())
    with engine.begin() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    if not version:
        return CheckResult("alembic_version", "FAIL", "tabla alembic_version vacia")
    return CheckResult("alembic_version", "PASS", f"current={version}")


def run_checks(require_redis: bool, backup_hours: int) -> List[CheckResult]:
    checks = [
        _check_db_latency(),
        _check_alembic_version(),
        _check_backup_freshness(hours=backup_hours),
        _check_logger_write(),
        _check_rate_limit_backend(require_redis=require_redis),
        _check_alert_pipeline(),
    ]
    return checks


def summarize(results: List[CheckResult]) -> int:
    print("== Ops Readiness Check ==")
    print(f"timestamp={datetime.now().isoformat(timespec='seconds')}")
    for result in results:
        print(f"[{result.status}] {result.name}: {result.detail}")
    fail = sum(1 for r in results if r.status == "FAIL")
    warn = sum(1 for r in results if r.status == "WARN")
    ok = sum(1 for r in results if r.status == "PASS")
    print(f"summary: PASS={ok} WARN={warn} FAIL={fail}")
    return 1 if fail > 0 else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-redis",
        action="store_true",
        help="Falla si Redis no está conectado (recomendado para producción).",
    )
    parser.add_argument(
        "--backup-max-age-hours",
        type=int,
        default=24,
        help="Edad máxima permitida del último backup para considerar PASS.",
    )
    args = parser.parse_args()

    load_dotenv(".env")
    results = run_checks(
        require_redis=bool(args.require_redis),
        backup_hours=int(args.backup_max_age_hours),
    )
    return summarize(results)


if __name__ == "__main__":
    raise SystemExit(main())
