"""Harness de latencia bajo carga de websockets Reflex (Fase P2).

Mide la latencia del pipeline de eventos REAL de Reflex (socket.io -> backend
asyncio -> delta de estado de vuelta) bajo N conexiones concurrentes, y produce la
curva "usuarios concurrentes vs latencia" — el entregable de P2
(docs/PERF_SCALABILITY_PLAN.md §4).

A diferencia de `scripts/stress_concurrency.py` (que golpea la capa de servicio/BD
directamente), este harness abre websockets socket.io reales contra el endpoint
`/_event` de Reflex, hace el handshake con `token`, y cronometra el round-trip
emit->delta. Reflex NO se mide con `ab`/`wrk`: el evento viaja por socket.io.

Un escenario = (pasos de SETUP ejecutados una vez por conexión) + (pasos de LOOP
repetidos hasta agotar la duración). Cada paso emite un evento y espera el delta;
se registra la latencia por-etiqueta.

Escenarios
----------
- ``ping`` (default): emite el evento socket ``ping`` y espera el ``pong``.
  Sin auth, sin estado, sin BD -> mide la salud del event-loop del backend
  single-process bajo carga de conexiones. Es el probe base y SEGURO.
- ``hydrate``: dispara el evento de estado real ``...on_load_internal`` y espera
  el delta -> mide el pipeline completo (state manager + Redis). Sin auth.
- ``supervisor``: login -> re-hidratar (lectura). Requiere entorno de PRUEBA.
- ``cajero``: login -> agregar producto(s) -> confirmar venta. **ESCRIBE ventas**
  -> correr SOLO contra un schema descartable, NUNCA `sistema_ventas`.

Los escenarios autenticados necesitan un backend apuntando a un schema de prueba
sembrado con usuario/empresa/producto y con rate-limit de login relajado
(``ALLOW_MEMORY_RATE_LIMIT_FALLBACK`` no alcanza: el login limita por identificador
+IP). Ver docs/PERF_SCALABILITY_PLAN.md §4. Credenciales/ids por env o flags.

Uso
---
    # backend Reflex de PRUEBA (NUNCA prod):
    WS_TARGET=http://localhost:8000 \
      python scripts/ws_load.py --scenario ping --ramp 10,50,100,200 --duration 30

    # escenario cajero contra un schema descartable, con creds e ids de prueba:
    python scripts/ws_load.py --scenario cajero --ramp 10,25 \
      --login-user cajero1 --login-pass secret --product-ids 1,2,3

Requiere ``aiohttp`` (requirements-dev.txt) como transport de ``socketio.AsyncClient``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
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

_STATE_NAME_CACHE: str | None = None


def resolve_state_name(override: str = "") -> str:
    """Nombre completo del State de Reflex (para nombrar eventos de handlers).

    Los escenarios autenticados lo necesitan. Se resuelve importando
    ``app.state.State`` (pesado) SÓLO cuando hace falta; se puede forzar con
    ``--state-name`` para tests/mocks sin cargar la app.
    """
    global _STATE_NAME_CACHE
    if override:
        return override
    if _STATE_NAME_CACHE is not None:
        return _STATE_NAME_CACHE
    try:
        from app.state import State  # import perezoso: requiere env de la app
        _STATE_NAME_CACHE = State.get_full_name()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: no pude resolver el nombre del State ({type(exc).__name__}: {exc}).\n"
              "Pasá --state-name explícito o corré con el env de la app.", file=sys.stderr)
        sys.exit(2)
    return _STATE_NAME_CACHE


@dataclass
class Step:
    """Un paso del escenario: emite un evento socket y espera su respuesta."""
    label: str
    socket_event: str          # "ping" | "event"
    payload: dict | None = None


def _router_data() -> dict:
    return {"pathname": "/", "query": {}}


def build_scenario(name: str, args: argparse.Namespace) -> tuple[list[Step], list[Step]]:
    """Devuelve (pasos_setup, pasos_loop) para el escenario dado."""
    if name == "ping":
        return [], [Step("ping", "ping")]

    if name == "hydrate":
        return [], [Step("hydrate", "event",
                         {"name": ON_LOAD_INTERNAL, "payload": {}, "router_data": _router_data()})]

    sn = resolve_state_name(args.state_name)
    login = Step("login", "event", {
        "name": f"{sn}.login",
        "payload": {"form_data": {"username": args.login_user, "password": args.login_pass}},
        "router_data": _router_data(),
    })

    if name == "supervisor":
        # login una vez; luego re-hidratar (lectura de dashboard/estado).
        return [login], [Step("rehydrate", "event",
                              {"name": ON_LOAD_INTERNAL, "payload": {}, "router_data": _router_data()})]

    if name == "cajero":
        pids = [int(x) for x in args.product_ids.split(",") if x.strip()] or [1]
        loop = [Step(f"add_product[{pid}]", "event", {
            "name": f"{sn}.add_product_to_sale_by_id",
            "payload": {"product_id": pid},
            "router_data": _router_data(),
        }) for pid in pids]
        loop.append(Step("confirm_sale", "event", {
            "name": f"{sn}.confirm_sale", "payload": {}, "router_data": _router_data(),
        }))
        return [login], loop

    raise ValueError(f"escenario desconocido: {name}")


@dataclass
class UserResult:
    latencies_ms: dict[str, list[float]] = field(default_factory=dict)
    errors: int = 0
    disconnects: int = 0
    setup_ok: bool = False
    connect_ms: float | None = None
    connect_error: str | None = None

    def record(self, label: str, ms: float) -> None:
        self.latencies_ms.setdefault(label, []).append(ms)


class VirtualUser:
    """Una conexión websocket socket.io = un "usuario" virtual del navegador."""

    def __init__(self, target: str, setup: list[Step], loop: list[Step], think_ms: int):
        self.target = target
        self.setup = setup
        self.loop = loop
        self.think = think_ms / 1000.0
        self.token = uuid.uuid4().hex
        self.sio = socketio.AsyncClient(reconnection=False, logger=False, engineio_logger=False)
        self.result = UserResult()
        self._waiter: asyncio.Future | None = None
        self._stopping = False
        self._eloop = asyncio.get_event_loop()

        @self.sio.on("event", namespace=NAMESPACE)
        async def _on_event(data):  # noqa: ANN001
            self._resolve()

        @self.sio.on("ping", namespace=NAMESPACE)
        async def _on_ping(data):  # noqa: ANN001
            self._resolve()

        @self.sio.event(namespace=NAMESPACE)
        async def disconnect():  # noqa: D401
            if not self._stopping:
                self.result.disconnects += 1
                self._resolve(error=True)

    def _resolve(self, error: bool = False) -> None:
        if self._waiter is not None and not self._waiter.done():
            self._waiter.set_result(error)

    async def connect(self) -> bool:
        url = f"{self.target}?token={self.token}"
        t0 = time.perf_counter()
        try:
            await self.sio.connect(url, socketio_path=EVENT_PATH, namespaces=[NAMESPACE],
                                   transports=["websocket"], wait_timeout=15)
            self.result.connect_ms = (time.perf_counter() - t0) * 1000
            return True
        except Exception as exc:  # noqa: BLE001
            self.result.connect_error = f"{type(exc).__name__}: {exc}"
            return False

    async def _emit_step(self, step: Step) -> bool:
        """Emite un paso, cronometra el round-trip. Devuelve True si OK."""
        self._waiter = self._eloop.create_future()
        t0 = time.perf_counter()
        try:
            if step.socket_event == "ping":
                await self.sio.emit("ping", namespace=NAMESPACE)
            else:
                await self.sio.emit("event", step.payload, namespace=NAMESPACE)
            errored = await asyncio.wait_for(self._waiter, timeout=20)
            if errored:
                self.result.errors += 1
                return False
            self.result.record(step.label, (time.perf_counter() - t0) * 1000)
            return True
        except asyncio.TimeoutError:
            self.result.errors += 1
            return False
        finally:
            self._waiter = None

    async def run(self, deadline: float) -> UserResult:
        if not await self.connect():
            return self.result
        try:
            # SETUP (login, etc.) una vez; si falla, no seguimos con el loop.
            self.result.setup_ok = True
            for step in self.setup:
                if not await self._emit_step(step):
                    self.result.setup_ok = False
                    return self.result
            while time.perf_counter() < deadline:
                for step in self.loop:
                    await self._emit_step(step)
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
    setup_fail: int
    p50: float
    p95: float
    p99: float
    maxv: float
    connect_p95: float
    throughput_rps: float
    per_label_p95: dict[str, float]


def _summarize(users: int, results: list[UserResult], wall_s: float) -> LevelStats:
    all_lat: list[float] = []
    by_label: dict[str, list[float]] = {}
    for r in results:
        for label, xs in r.latencies_ms.items():
            all_lat.extend(xs)
            by_label.setdefault(label, []).extend(xs)
    conn = [r.connect_ms for r in results if r.connect_ms is not None]
    return LevelStats(
        users=users,
        samples=len(all_lat),
        errors=sum(r.errors for r in results),
        disconnects=sum(r.disconnects for r in results),
        connect_fail=sum(1 for r in results if r.connect_error),
        setup_fail=sum(1 for r in results if r.connect_error is None and not r.setup_ok),
        p50=_pct(all_lat, 0.50),
        p95=_pct(all_lat, 0.95),
        p99=_pct(all_lat, 0.99),
        maxv=max(all_lat) if all_lat else float("nan"),
        connect_p95=_pct(conn, 0.95),
        throughput_rps=(len(all_lat) / wall_s) if wall_s > 0 else 0.0,
        per_label_p95={k: _pct(v, 0.95) for k, v in by_label.items()},
    )


async def _run_level(target: str, setup: list[Step], loop: list[Step],
                     users: int, duration: int, think_ms: int) -> LevelStats:
    vusers = [VirtualUser(target, setup, loop, think_ms) for _ in range(users)]
    t0 = time.perf_counter()
    deadline = t0 + duration
    results = await asyncio.gather(*(u.run(deadline) for u in vusers))
    return _summarize(users, results, time.perf_counter() - t0)


def _print_table(rows: list[LevelStats], slo_p95: float) -> None:
    print()
    print(f"{'users':>6} {'samples':>8} {'p50':>8} {'p95':>8} {'p99':>8} {'max':>9} "
          f"{'conn_p95':>9} {'rps':>8} {'err':>5} {'disc':>5} {'cfail':>6} {'sfail':>6} {'SLO':>5}")
    print("-" * 108)
    for r in rows:
        ok = (r.p95 == r.p95 and r.p95 <= slo_p95 and r.errors == 0
              and r.disconnects == 0 and r.setup_fail == 0)
        print(f"{r.users:>6} {r.samples:>8} {r.p50:>8.1f} {r.p95:>8.1f} {r.p99:>8.1f} "
              f"{r.maxv:>9.1f} {r.connect_p95:>9.1f} {r.throughput_rps:>8.1f} "
              f"{r.errors:>5} {r.disconnects:>5} {r.connect_fail:>6} {r.setup_fail:>6} "
              f"{'OK' if ok else 'FAIL':>5}")
    # desglose por-etiqueta del último nivel (útil en escenarios multi-paso)
    if rows and len(rows[-1].per_label_p95) > 1:
        print(f"\np95 por paso (nivel {rows[-1].users}): " +
              "  ".join(f"{k}={v:.1f}ms" for k, v in rows[-1].per_label_p95.items()))
    print(f"\nSLO p95 = {slo_p95:.0f} ms. conn_p95=latencia de conexión; "
          "cfail=conexiones fallidas; sfail=setup(login) fallido.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Harness de carga websocket Reflex (P2).")
    parser.add_argument("--target", default=os.getenv("WS_TARGET", "http://localhost:8000"))
    parser.add_argument("--scenario", choices=["ping", "hydrate", "supervisor", "cajero"],
                        default="ping")
    parser.add_argument("--ramp", default="10,50,100,200")
    parser.add_argument("--duration", type=int, default=30, help="Segundos por nivel.")
    parser.add_argument("--think-ms", type=int, default=200)
    parser.add_argument("--slo-p95", type=float, default=400.0)
    parser.add_argument("--out-json", default="")
    parser.add_argument("--unsafe", action="store_true", help="Permite apuntar a producción.")
    # escenarios autenticados
    parser.add_argument("--login-user", default=os.getenv("WS_LOGIN_USER", ""))
    parser.add_argument("--login-pass", default=os.getenv("WS_LOGIN_PASS", ""))
    parser.add_argument("--product-ids", default="1", help="IDs de producto (coma) para cajero.")
    parser.add_argument("--state-name", default="",
                        help="Fuerza el nombre del State (evita importar la app; para tests).")
    args = parser.parse_args()

    target = args.target.rstrip("/")
    if not args.unsafe and any(m in target for m in PROD_MARKERS):
        print(f"ERROR: '{target}' parece PRODUCCIÓN. Usá un backend de prueba o --unsafe.",
              file=sys.stderr)
        sys.exit(2)

    if args.scenario in ("supervisor", "cajero") and not (args.login_user and args.login_pass):
        print(f"ERROR: el escenario '{args.scenario}' requiere --login-user y --login-pass "
              "(o WS_LOGIN_USER/WS_LOGIN_PASS). Ver §4 del plan (necesita schema de prueba).",
              file=sys.stderr)
        sys.exit(2)

    setup, loop = build_scenario(args.scenario, args)
    levels = [int(x) for x in args.ramp.split(",") if x.strip()]
    print(f"Target={target}  escenario={args.scenario}  ramp={levels}  "
          f"duration={args.duration}s  think={args.think_ms}ms  "
          f"setup={[s.label for s in setup]}  loop={[s.label for s in loop]}")

    rows: list[LevelStats] = []
    for users in levels:
        print(f"  -> nivel {users} usuarios ...", flush=True)
        stats = await _run_level(target, setup, loop, users, args.duration, args.think_ms)
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
