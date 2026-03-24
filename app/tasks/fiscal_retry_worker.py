"""Worker de reintento automático para documentos fiscales fallidos.

Este módulo puede ejecutarse:

    1. Como script independiente (cron job del sistema operativo):
       python -m app.tasks.fiscal_retry_worker

    2. Como función async importable desde otros módulos:
       from app.tasks.fiscal_retry_worker import run_auto_retry
       await run_auto_retry()

Diseño:
    - Busca todos los FiscalDocument con status in (error, pending)
      y retry_count < MAX_RETRY_ATTEMPTS, agrupados por company_id.
    - Para cada documento llama retry_fiscal_document().
    - Respeta backoff exponencial entre intentos: espera 2^retry_count segundos
      antes de cada reintento (máx. 60s).
    - Registra resultados en el logger estándar (ver app.utils.logger).
    - Idempotente: se puede ejecutar múltiples veces sin riesgo de duplicados.

Ejecución recomendada (cron Linux/Mac):
    */30 * * * * /path/to/.venv/bin/python -m app.tasks.fiscal_retry_worker

Ejecución recomendada (Task Scheduler Windows):
    Program: C:\\ruta\\.venv\\Scripts\\python.exe
    Arguments: -m app.tasks.fiscal_retry_worker
    Start in: C:\\ruta\\Sistema-de-Ventas
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Asegurar que el directorio raíz del proyecto está en el path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from sqlmodel import select

from app.enums import FiscalStatus
from app.models.billing import FiscalDocument
from app.services.billing_service import retry_fiscal_document, MAX_RETRY_ATTEMPTS
from app.utils.db import get_async_session
from app.utils.logger import get_logger
from app.utils.tenant import set_tenant_context

logger = get_logger("FiscalRetryWorker")

# Límite de documentos a procesar por ejecución (evita tiempos de ejecución excesivos)
_BATCH_LIMIT = 50
# Máximo segundos entre reintentos
_MAX_BACKOFF_SECONDS = 60.0
# Pausa entre documentos individuales (throttle para no saturar la API fiscal)
_INTER_DOC_PAUSE_SECONDS = 1.0


async def run_auto_retry(dry_run: bool = False) -> dict:
    """Reintenta automáticamente documentos fiscales en estado error/pending.

    Args:
        dry_run: Si True, solo lista los documentos que serían reintentados
                 sin ejecutar la llamada al servicio fiscal.

    Returns:
        Diccionario con estadísticas: processed, authorized, still_error, skipped.
    """
    stats = {
        "processed": 0,
        "authorized": 0,
        "still_error": 0,
        "skipped": 0,
        "dry_run": dry_run,
    }

    logger.info(
        "=== FiscalRetryWorker iniciado | dry_run=%s | batch_limit=%d ===",
        dry_run,
        _BATCH_LIMIT,
    )

    try:
        async with get_async_session() as session:
            # Obtener documentos candidatos al reintento
            docs_stmt = (
                select(FiscalDocument)
                .where(
                    FiscalDocument.fiscal_status.in_(  # type: ignore[union-attr]
                        [FiscalStatus.error, FiscalStatus.pending]
                    )
                )
                .where(FiscalDocument.retry_count < MAX_RETRY_ATTEMPTS)
                # Priorizar los más recientes
                .order_by(FiscalDocument.created_at.desc())  # type: ignore[union-attr]
                .limit(_BATCH_LIMIT)
            )
            docs = (await session.exec(docs_stmt)).all()

        if not docs:
            logger.info("No hay documentos para reintentar.")
            return stats

        logger.info("Documentos encontrados para reintento: %d", len(docs))

        for doc in docs:
            stats["processed"] += 1
            doc_id = doc.id
            sale_id = doc.sale_id
            company_id = doc.company_id
            branch_id = doc.branch_id
            retry_count = doc.retry_count or 0
            full_number = doc.full_number or f"ID:{doc_id}"

            # Backoff exponencial: 2^retry_count segundos (máx. 60s)
            backoff = min(2 ** retry_count, _MAX_BACKOFF_SECONDS)

            logger.info(
                "Reintentando doc=%s | sale_id=%s | retry_count=%d | backoff=%.1fs",
                full_number,
                sale_id,
                retry_count,
                backoff,
            )

            if dry_run:
                logger.info("[DRY RUN] Se reintentaría: %s", full_number)
                continue

            # Esperar el backoff
            if backoff > 0:
                await asyncio.sleep(backoff)

            try:
                set_tenant_context(company_id, branch_id)
                result = await retry_fiscal_document(
                    fiscal_doc_id=doc_id,
                    company_id=company_id,
                    branch_id=branch_id,
                )

                if result is None:
                    logger.warning("retry_fiscal_document retornó None para doc_id=%d", doc_id)
                    stats["still_error"] += 1
                elif result.fiscal_status == FiscalStatus.authorized:
                    logger.info(
                        "Autorizado exitosamente: %s | sale_id=%s",
                        result.full_number,
                        sale_id,
                    )
                    stats["authorized"] += 1
                else:
                    logger.warning(
                        "Sigue con errores: %s | status=%s | errors=%s",
                        result.full_number,
                        result.fiscal_status,
                        (result.fiscal_errors or "")[:200],
                    )
                    stats["still_error"] += 1

            except Exception as exc:
                logger.exception(
                    "Excepción al reintentar doc_id=%d | sale_id=%s: %s",
                    doc_id,
                    sale_id,
                    exc,
                )
                stats["still_error"] += 1

            # Pausa entre documentos para no saturar la API
            await asyncio.sleep(_INTER_DOC_PAUSE_SECONDS)

    except Exception as exc:
        logger.exception("Error crítico en FiscalRetryWorker: %s", exc)

    stats["skipped"] = stats["processed"] - stats["authorized"] - stats["still_error"]

    logger.info(
        "=== FiscalRetryWorker completado | procesados=%d | autorizados=%d | "
        "errores=%d | skipped=%d ===",
        stats["processed"],
        stats["authorized"],
        stats["still_error"],
        stats["skipped"],
    )
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Worker de reintento fiscal TUWAYKIAPP")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo lista los documentos sin ejecutar reintentos",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=_BATCH_LIMIT,
        help=f"Máximo de documentos a procesar (default: {_BATCH_LIMIT})",
    )
    args = parser.parse_args()

    if args.batch_limit != _BATCH_LIMIT:
        _BATCH_LIMIT = args.batch_limit

    result = asyncio.run(run_auto_retry(dry_run=args.dry_run))
    print("\n--- Resultado ---")
    for k, v in result.items():
        print(f"  {k}: {v}")
    sys.exit(0 if result.get("still_error", 0) == 0 else 1)
