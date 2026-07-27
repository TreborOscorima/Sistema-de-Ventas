"""Sesión de solo-lectura para descargar reportes del MySQL primario (P3 §3.4).

Si hay una **réplica de lectura** configurada (`DB_READ_URL`, o `DB_READ_HOST`
distinto del primario), los reportes pesados la usan y liberan al primario del POS.
Si NO hay réplica (default), ``read_session()`` delega en ``rx.session()`` → el
comportamiento actual, sin overhead ni riesgo.

Recomendado en host compartido/ajustado: una réplica **fuera de la caja** (AWS RDS
read replica o instancia aparte), para no robarle RAM a los otros sistemas.

Seguridad multi-tenant: los listeners de ``tuwayki_core`` (``do_orm_execute`` /
``before_flush``) están registrados sobre la clase ``Session`` con
``propagate=True`` → aplican también a esta sesión. El aislamiento por
``company_id`` se preserva igual que en ``rx.session()``.

Sólo para LECTURAS. No escribir por esta sesión (una réplica es read-only; además
rompería el ruteo). Para escrituras, seguir usando ``rx.session()``.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator
from urllib.parse import quote_plus

import reflex as rx
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _read_url() -> str | None:
    """URL de la réplica de lectura, o None si no hay réplica (usar primario)."""
    direct = (os.getenv("DB_READ_URL") or "").strip()
    if direct:
        return direct
    read_host = (os.getenv("DB_READ_HOST") or "").strip()
    primary_host = (os.getenv("DB_HOST") or "").strip()
    # Sin host de lectura, o igual al primario → no hay réplica real.
    if not read_host or read_host == primary_host:
        return None
    user = quote_plus(os.getenv("DB_USER") or "")
    pw = quote_plus(os.getenv("DB_PASSWORD") or "")
    port = (os.getenv("DB_READ_PORT") or os.getenv("DB_PORT") or "3306").strip()
    name = (os.getenv("DB_NAME") or "").strip()
    return f"mysql+pymysql://{user}:{pw}@{read_host}:{port}/{name}?charset=utf8mb4"


@lru_cache(maxsize=1)
def _read_engine() -> Engine | None:
    """Engine de la réplica (lazy, cacheado). None si no hay réplica configurada."""
    url = _read_url()
    if not url:
        return None
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_READ_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_READ_MAX_OVERFLOW", "5")),
        pool_recycle=int(os.getenv("DB_READ_POOL_RECYCLE", "1800")),
    )


def read_replica_configured() -> bool:
    """True si hay una réplica de lectura configurada (para logs/health)."""
    return _read_engine() is not None


@contextmanager
def read_session() -> Iterator[Session]:
    """Sesión de SOLO-LECTURA.

    Usa la réplica si está configurada; si no, delega en ``rx.session()`` (primario).
    Drop-in para reportes: ``with read_session() as session: ...``.
    """
    engine = _read_engine()
    if engine is None:
        # Sin réplica: comportamiento idéntico al actual.
        with rx.session() as session:
            yield session
        return
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
