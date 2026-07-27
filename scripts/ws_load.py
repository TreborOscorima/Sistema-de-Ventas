"""Harness de latencia bajo carga de websockets Reflex (Fase P2).

Mide la latencia del pipeline de eventos REAL de Reflex (socket.io → backend
asyncio → delta de estado de vuelta) bajo N conexiones concurrentes, y produce la
curva "usuarios concurrentes vs latencia" — el entregable de P2
(docs/PERF_SCALABILITY_PLAN.md §4).

A diferencia de `scripts/stress_concurrency.py` (que golpea la capa de servicio/BD
directamente), este harness abre websockets socket.io reales contra el endpoint
`/_event` de Reflex, hace el handshake con `token`, y cronometra el round-trip
emit→delta. Reflex NO se mide con `ab`/`wrk`: el evento viaja por socket.io.

Escenarios
----------
- ``ping`` (default): emite el evento socket ``ping`` y espera el ``pong`` del
  namespace. Sin auth, sin estado, sin BD → mide la salud del event-loop del
  backend single-process bajo carga de conexiones concurrentes. Es el probe base.
- ``hydrate``: dispara el evento de estado real
  ``reflex___state____on_load_internal_state.on_load_internal`` y espera el delta
  ``event`` de vuelta → mide el pipeline completo (state manager + Redis).

Uso
---
    # levantar un backend Reflex de PRUEBA (NUNCA prod) y apuntar el harness ahí
    WS_TARGET=http://localhost:8000 \
      python scripts/ws_load.py --scenario ping --ramp 10,50,100,200 --duration 30

    # salida a CSV/JSON para graficar
    python scripts/ws_load.py --ramp 25,50,100 --out-json build/ws_p2.json

SLOs propuestos (§4): p95 evento POS < 400 ms; confirmar venta p95 < 1 s;
0 errores 5xx / desconexiones bajo carga sostenida 10 min.

Requiere ``aiohttp`` (requirements-dev.txt) como transport de ``socketio.AsyncClient``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

try:
    import socketio
except ImportError:  # pragma: no cover
    print("ERROR: falta python-socketio. pip install -r requirements-dev.txt", file=sys.stderr)
    sys.exit(2)

# Endpoint/namespace donde Reflex monta socket.io (constante en 0.9.x).
EVENT_PATH = "/_event"
NAMESPACE = "/_event"
# Evento de estado que dispara el frontend al cargar la página (hydrate real).
ON_LOAD_INTERNAL = "reflex___state____on_load_internal_state.on_load_internal"

# Hosts de producción: el harness se niega a golpearlos salvo --unsafe.
PROD_MARKERS = ("tuwayki.app", "tuwayki.com")


@dataclass
class UserResult:
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0
    disconnects: int = 0
    connect_ms: float | None = None
    connect_error: str | None = None


class VirtualUser:
    """Una conexión websocket socket.io = un "usuario" virtual del navegador."""

    def __init__(self, target: str, scenario: str, think_ms: int):
        self.target = target
        self.scenario = scenario
        self.think = think_ms / 1000.0
        self.token = uuid.uuid4().hex
        self.sio = socketio.AsyncClient(reconnection=False, logger=False, engineio_logger=False)
        self.result = UserResult()
        self._waiter: asyncio.Future | None = None
        self._stopping = False  # True = cierre intencional al terminar el test
        self._loop = asyncio.get_event_loop()

        @self.sio.on("event", namespace=NAMESPACE)
        async def _on_event(data):  # noqa: ANN001 (delta de estado)
            self._resolve()

        @self.sio.on("ping", namespace=NAMESPACE)
        async def _on_ping(data):  # noqa: ANN001 (respuesta "pong")
            self._resolve()

        @self.sio.event(namespace=NAMESPACE)
        async def disconnect():  # noqa: D401
            # Sólo cuenta como caída si NO es el cierre intencional del test.
            if not self._stopping:
                self.result.disconnects += 1
                self._resolve(error=True)

    def _resolve(self, error: bool = False) -> None:
        if self._waiter is not None and not self._waiter.done():
            self._waiter.set_result(error)

    async def connect(self) -> bool:
        # El token va como query param: Reflex lo lee en on_connect (sid_to_token).
        url = f"{self.target}?token={self.token}"
        t0 = time.perf_counter()
        try:
            await self.sio.connect(
                url,
                socketio_path=EVENT_PATH,
                namespaces=[NAMESPACE],
                transports=["websocket"],
                wait_timeout=15,
            )
            self.result.connect_ms = (time.perf_counter() - t0) * 1000
            return True
        except Exception as exc:  # noqa: BLE001
            self.result.connect_error = f"{type(exc).__name__}: {exc}"
            return False

    async def _one_round_trip(self) -> None:
        """Emite un evento y cronometra hasta recibir la respuesta correlacionada."""
        self._waiter = self._loop.create_future()
        t0 = time.perf_counter()
        try:
            if self.scenario == "ping":
                await self.sio.emit("ping", namespace=NAMESPACE)
            else:  # hydrate / evento de estado
                payload = {
                    "name": ON_LOAD_INTERNAL,
                    "payload": {},
                    "router_data": {"pathname": "/", "query": {}},
                }
                await self.sio.emit("event", payload, namespace=NAMESPACE)
            errored = await asyncio.wait_for(self._waiter, timeout=20)
            if errored:
                self.result.errors += 1
            else:
                self.result.latencies_ms.append((time.perf_counter() - t0) * 1000)
        except asyncio.TimeoutError:
            self.result.errors += 1
        finally:
            self._waiter = None

    async def run(self, deadline: float) -> UserResult:
        if not await self.connect():
            return self.result
        try:
            while time.perf_counter() < deadline:
                await self._one_round_trip()
                if self.think:
                    await asyncio.sleep(self.think)
        finally:
            self._stopping = True
            try:
                await self.sio.disconnect()
            except Exception:  # noqa: BLE001
                pass
        return self.result


def _pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    k = (len(values) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


@dataclass
class LevelStats:
    users: int
    samples: int
    errors: int
    disconnects: int
    connect_fail: int
    p50: float
    p95: float
    p99: float
    maxv: float
    connect_p95: float
    throughput_rps: float


def _summarize(users: int, results: list[UserResult], wall_s: float) -> LevelStats:
    lat = [x for r in results for x in r.latencies_ms]
    conn = [r.connect_ms for r in results if r.connect_ms is not None]
    return LevelStats(
        users=users,
        samples=len(lat),
        errors=sum(r.errors for r in results),
        disconnects=sum(r.disconnects for r in results),
        connect_fail=sum(1 for r in results if r.connect_error),
        p50=_pct(lat, 0.50),
        p95=_pct(lat, 0.95),
        p99=_pct(lat, 0.99),
        maxv=max(lat) if lat else float("nan"),
        connect_p95=_pct(conn, 0.95),
        throughput_rps=(len(lat) / wall_s) if wall_s > 0 else 0.0,
    )


async def _run_level(target: str, scenario: str, users: int, duration: int, think_ms: int) -> LevelStats:
    vusers = [VirtualUser(target, scenario, think_ms) for _ in range(users)]
    t0 = time.perf_counter()
    deadline = t0 + duration
    results = await asyncio.gather(*(u.run(deadline) for u in vusers))
    wall = time.perf_counter() - t0
    return _summarize(users, results, wall)


def _print_table(rows: list[LevelStats], slo_p95: float) -> None:
    print()
    print(f"{'users':>6} {'samples':>8} {'p50':>8} {'p95':>8} {'p99':>8} {'max':>8} "
          f"{'conn_p95':>9} {'rps':>8} {'err':>5} {'disc':>5} {'cfail':>6} {'SLO':>5}")
    print("-" * 100)
    for r in rows:
        slo = "OK" if (r.p95 == r.p95 and r.p95 <= slo_p95 and r.errors == 0 and r.disconnects == 0) else "FAIL"
        print(f"{r.users:>6} {r.samples:>8} {r.p50:>8.1f} {r.p95:>8.1f} {r.p99:>8.1f} "
              f"{r.maxv:>8.1f} {r.connect_p95:>9.1f} {r.throughput_rps:>8.1f} "
              f"{r.errors:>5} {r.disconnects:>5} {r.connect_fail:>6} {slo:>5}")
    print()
    print(f"SLO p95 = {slo_p95:.0f} ms. 'conn_p95' = latencia de conexión; 'cfail' = conexiones fallidas.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Harness de carga websocket Reflex (P2).")
    parser.add_argument("--target", default=os.getenv("WS_TARGET", "http://localhost:8000"),
                        help="URL base del backend Reflex de PRUEBA (default env WS_TARGET).")
    parser.add_argument("--scenario", choices=["ping", "hydrate"], default="ping")
    parser.add_argument("--ramp", default="10,50,100,200",
                        help="Niveles de usuarios concurrentes, coma-separados.")
    parser.add_argument("--duration", type=int, default=30, help="Segundos por nivel.")
    parser.add_argument("--think-ms", type=int, default=200,
                        help="Pausa entre eventos por usuario (simula pensamiento humano).")
    parser.add_argument("--slo-p95", type=float, default=400.0, help="SLO p95 en ms.")
    parser.add_argument("--out-json", default="", help="Ruta para volcar métricas en JSON.")
    parser.add_argument("--unsafe", action="store_true",
                        help="Permite apuntar a hosts de producción (peligroso).")
    args = parser.parse_args()

    target = args.target.rstrip("/")
    if not args.unsafe and any(m in target for m in PROD_MARKERS):
        print(f"ERROR: '{target}' parece PRODUCCIÓN. Usá un backend de prueba o --unsafe.",
              file=sys.stderr)
        sys.exit(2)

    levels = [int(x) for x in args.ramp.split(",") if x.strip()]
    print(f"Target={target}  escenario={args.scenario}  ramp={levels}  "
          f"duration={args.duration}s  think={args.think_ms}ms")

    rows: list[LevelStats] = []
    for users in levels:
        print(f"  -> nivel {users} usuarios ...", flush=True)
        stats = await _run_level(target, args.scenario, users, args.duration, args.think_ms)
        rows.append(stats)
        if stats.connect_fail == users:
            print(f"    todas las conexiones fallaron en nivel {users}; aborto la rampa.")
            break

    _print_table(rows, args.slo_p95)

    if args.out_json:
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"target": target, "scenario": args.scenario,
                                    "levels": [vars(r) for r in rows]}, indent=2))
        print(f"Métricas escritas en {out}")


if __name__ == "__main__":
    asyncio.run(main())
