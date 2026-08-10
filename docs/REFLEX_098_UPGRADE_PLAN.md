# Plan de Upgrade: Reflex 0.9.4 → 0.9.8 + Sincronización de Dependencias

**Creado:** 2026-08-09
**Autor:** Trebor Oscorima + Claude Code
**Estado:** 🟡 PLANIFICACIÓN — ninguna fase ejecutada aún
**Propósito:** Guía sesión a sesión, retomable en cualquier punto sin perder contexto.
**Alcance:** Este documento cubre **SHOP (Sistema-de-Ventas) únicamente**. Es parte de un rollout **coordinado de flota** a Reflex 0.9.8 (SHOP + FOOD + LIFE), gestionado en 3 sesiones paralelas.
**Documentos relacionados:**
- Plan de flota / FOOD: [`Sistema-para-Food/PLAN_ACTUALIZACION_REFLEX.md`](../../Sistema-para-Food/PLAN_ACTUALIZACION_REFLEX.md) — plan transversal de la suite (core → Food → Life → Ventas).
- Upgrade previo (misma mecánica): [`REFLEX_094_UPGRADE_PLAN.md`](REFLEX_094_UPGRADE_PLAN.md) — 0.9.3→0.9.4.

---

## Contexto rápido (leer SIEMPRE al inicio de cada sesión)

Este documento es la **única fuente de verdad** para este upgrade. Marca cada paso con `[x]` al completarlo. Si una sesión termina a mitad de una fase, anota el punto exacto en **"Dónde quedamos"** al final.

### Por qué hacemos esto (motivación real)

El disparador fue "el fix del Tooltip de Reflex", pero tras investigar (ver [Análisis de impacto](#análisis-de-impacto)):

- **El fix del tooltip NO es el motivo real** para nosotros. El bug corregido es de Radix UI (tooltip que se reabre al reenfocar la pestaña / requiere segundo hover). En este sistema `rx.tooltip` nativo se usa en **un solo lugar** ([`app/pages/caja/_sales.py:77`](../app/pages/caja/_sales.py)). El resto de tooltips son propios ([`assets/js/twk-tooltip.js`](../assets/js/twk-tooltip.js) + CSS `group-hover`), así que el beneficio del fix es marginal. **No desmontar el sistema custom.**
- **Los motivos que SÍ justifican el upgrade** (todos afectan a este sistema porque corre en Windows con Redis en prod):
  1. **Fix de stylesheets con backslash en Windows** (0.9.8) — rompe imports CSS con rutas `\`.
  2. **Fix de hidratación en producción en Windows** (MIME `text/plain`, 0.9.8).
  3. **Cierre correcto de conexiones Redis / token manager** (0.9.7) — usamos Redis para sesiones distribuidas.
  4. **Fix de hidratación por doble evaluación de estado** (0.9.7).
  5. Parches CVE (Pillow, aiohttp, cryptography, Starlette, Granian) — bajo impacto porque ya pinneamos versiones propias recientes, pero suma.

**Conclusión:** upgrade **recomendado pero NO urgente**. Riesgo **bajo-moderado** (ver hallazgos abajo). Hacerlo en rama, con la red de los 1024 tests + verificación local antes de tocar prod.

### Hallazgos que reducen el riesgo (verificados 2026-08-09)

- ✅ **Único breaking change oficial 0.9.4→0.9.8:** se eliminó la env var `REFLEX_USE_TURBOPACK` (muerta desde 0.8). **No la usamos** → cero impacto de API. (Confirmado en el plan de flota de FOOD.)
- ✅ **Deprecación `ArrayVar.foreach` → `.map`:** SHOP tiene **0 ocurrencias** del método deprecado. Los ~180 usos son `rx.foreach(...)` (el componente, NO deprecado). **Nada que migrar aquí** (a diferencia de FOOD, que tenía 1).
- ✅ **`TailwindV3Plugin` existe en 0.9.8** sin deprecación (verificado en el `__init__.py` de la 0.9.8).
- ✅ **`tuwayki-core` es agnóstico a Reflex** — no lo importa. El upgrade no obliga a tocar el core.

### Estado inicial a verificar (rellenar en FASE 1)

| Ítem | Estado esperado (pre-upgrade) | Estado tras upgrade |
|---|---|---|
| `reflex` en `.venv` | `0.9.4` | → `0.9.8` |
| `reflex-base` | `0.9.4` | → `0.9.8` |
| `reflex-components-core` | `0.9.3` | → `0.9.8` |
| `reflex-components-radix` | `0.9.3` | → `0.9.7` (trae el fix tooltip) |
| `reflex-components-code` | `0.9.2` | → `0.9.3` |
| `reflex-components-lucide` | `1.0.1` | → `1.0.3` |
| `reflex-components-recharts` | `0.9.1` | → `0.9.2` |
| `reflex-components-plotly` | `0.9.2` | → `0.9.4` |
| `reflex-components-moment` | `0.9.1` | → `0.9.3` |
| `sonner`, `dataeditor`, `gridjs`, `markdown`, `react-player`, `hosting-cli` | mixto | resuelto por pip + freeze |
| Tests en suite | `____` (esperado ≥1024) | debe mantenerse, 0 failed |
| `TailwindV3Plugin` disponible en 0.9.8 | ✅ **YA VERIFICADO** (existe, sin deprecación) | — |
| Branch principal | `main` (clean) | rama `chore/reflex-0.9.8` |

> **Set objetivo confirmado con el plan de flota (FOOD).** No pinneamos los componentes a mano de forma exhaustiva: instalamos `reflex==0.9.8` + `reflex-base==0.9.8`, **pip resuelve** el resto, y `pip freeze` los captura. Las versiones de arriba son las esperadas del release 0.9.8; los 6 de la fila gris se resuelven en ejecución.
>
> ⚠️ **`reflex-hosting-cli==0.1.66`** (exclusivo de SHOP): verificar en FASE 3 que es compatible con reflex 0.9.8 o si requiere bump.

---

## Análisis de impacto

### 1. Sistema SHOP (este repo — Sistema-de-Ventas) — IMPACTO DIRECTO

Es el único sistema que cambia. Superficies a re-testear tras el upgrade (una por cada `reflex-components-*` que usamos):

| Componente Reflex | Dónde se usa | Riesgo de regresión |
|---|---|---|
| `radix` (themes + tooltip) | Global (`RadixThemesPlugin`), `rx.tooltip` en `_sales.py` | 🟢 El fix es a favor; verificar theme (indigo/slate) intacto |
| `recharts` | Dashboard ([`dashboard.py`](../app/pages/dashboard.py)) | 🔴 **Alto** — en el upgrade previo la cache de Vite corrompió recharts. Limpiar `.web` sí o sí |
| `sonner` | Toasts/notificaciones | 🟡 Verificar que disparan |
| `lucide` | Iconos en toda la app + `twk-tooltip.js` infiere labels de clases `lucide-*` | 🟡 46 iconos nuevos; verificar que ninguno cambió de nombre de clase |
| `plotly`, `dataeditor`, `gridjs`, `markdown`, `moment`, `react-player`, `code` | Según módulos | 🟡 Smoke test de cada módulo que los use |
| `TailwindV3Plugin` config | `rxconfig.py` (fuentes Inter/Grotesk, screens motion-safe) | 🟡 Clase existe; verificar esquema interno de `config={...}` al compilar |

### 2. `tuwayki-core` (paquete compartido) — SIN IMPACTO POR REFLEX ✅

**Hallazgo verificado:** `tuwayki-core` **no importa Reflex en ningún archivo** (grep de `import reflex` → 0 resultados). Es una librería agnóstica (db, crypto, auth, validators, exports, formatting…). Sus deps tienen límites muy laxos (`sqlalchemy>=2.0`, `cryptography>=42`, `redis>=5.0`, `PyJWT>=2.8`) → los bumps transitivos de Reflex 0.9.8 **no violan** sus constraints.

**Cómo instala SHOP el core (3 vías, verificado):**

| Entorno | Fuente del core | Detalle |
|---|---|---|
| Local `.venv` | `_vendor/tuwayki-core` **editable** | `__editable__.tuwayki_core-1.0.0.pth` |
| Docker | `_vendor/tuwayki-core` (copiado) | `Dockerfile:27` — `pip install /build/_vendor/tuwayki-core` |
| CI (`tests.yml`) | GitHub **SHA fijo** | `git+…/tuwayki-core.git@ef852f2…` |

> ⚠️ **Drift preexistente de core (NO es de este upgrade):** SHOP fija el core en CI en `@ef852f2`, mientras FOOD lo fija en `@64850c8`. Son commits distintos → los sistemas corren contra versiones potencialmente distintas del core. Es un tema de higiene aparte; **no lo tocamos en esta migración de Reflex**. Anotado para un cleanup futuro coordinado.

> ### ⚠️ REGLA DE ORO DEL ROLLOUT (compartida por las 3 sesiones)
> **NADIE modifica `tuwayki-core` como parte del upgrade de Reflex.** Si el core necesitara un cambio, se hace **una sola vez** en el repo canónico (`D:\PROYECTOS\tuwayki-core`) y se actualiza el SHA en los 3 `requirements.txt`/`Dockerfile` de forma coordinada, con re-test de los 3 sistemas. Fuera de eso, el upgrade de cada sistema es independiente.

### 3. Coordinación de flota (SHOP + FOOD + LIFE)

El rollout se ejecuta en **3 sesiones paralelas**, una por sistema. Cada `.venv`, `.web`, `requirements.txt` y `rxconfig.py` es independiente: "en paralelo" = correr el mismo runbook 3 veces, no un cambio único.

**Estado de la flota (2026-08-09):**

| Sistema | Reflex hoy | Salto | Riesgo | Plan |
|---|---|---|---|---|
| FOOD (`Sistema-para-Food`) | 0.9.6.post1 | 2 minors | 🟡 Medio | ✅ existe (`PLAN_ACTUALIZACION_REFLEX.md`) |
| LIFE (`Sistema-Gestion-Clinica`) | 0.9.4 | 4 minors | 🟢 Bajo | ⬜ pendiente |
| **SHOP (este repo)** | 0.9.4 | 4 minors | 🔴 Alto | ✅ **este documento** |

**Orden de flota acordado (del plan de FOOD):** core (smoke) → **FOOD** (piloto) → **LIFE** (valida el patrón) → **SHOP** (último, el más complejo, con toda la experiencia acumulada) → despliegue coordinado. SHOP va al final a propósito: es el que más superficie tiene (recharts, plotly, dataeditor, gridjs, sonner, hosting-cli) y el que hospeda el Owner Panel.

**Interacción runtime entre sistemas — Owner Panel:** el Owner Panel vive en SHOP y orquesta a FOOD y LIFE vía `/api/admin/companies/*` (owner-api). Por eso SHOP se actualiza cuando FOOD y LIFE **ya están en 0.9.8**, y en la verificación (FASE 8/10) hay que confirmar que **el Owner Panel sigue viendo y gestionando los 3 productos** correctamente. Ver [`OWNER_PARIDAD_FOOD_LIFE.md`](OWNER_PARIDAD_FOOD_LIFE.md).

**Por qué FOOD/LIFE no se rompen por el upgrade de SHOP:** core agnóstico + no lo tocamos + venvs independientes. La verificación cross-system se reduce a confirmar que el diff de SHOP **no incluye `_vendor/tuwayki-core/`** y que el Owner Panel sigue operando (FASE 8).

---

## Pipeline de deploy (referencia de toda la operación)

```
Local (.venv Python 3.13) — rama chore/reflex-0.9.8
    │
    ├─ FASE 1-6: Upgrade, recompilación limpia, tests, verificación local
    │
    ├─ FASE 7: merge a main → git push origin HEAD:main HEAD:docker-deploy-prod
    │              │
    │              ├─► GitHub Actions (tests.yml) — CI automático (Python 3.13, pip check + compileall + pytest)
    │              │
    │              ├─► FASE 9: SVR de PRUEBA (Docker Compose: build + up -d)
    │              │
    │              └─► FASE 10: SVR de PRODUCCIÓN (Docker Compose: build + up -d)
    │
    └─ FASE 8: Verificación cross-system (FOOD/LIFE intactos)
```

> **Recordatorio del proyecto:** Local usa `.venv` + `reflex run`. SVR Prueba y Prod usan Docker Compose (`docker compose build && up -d`) o `scripts/deploy.sh`. El `docker compose build` reinstala `requirements.txt` y reconstruye Vite dentro del contenedor.

---

## FASE 1 — Preparación, snapshot y línea base

**Duración:** ~15 min · **Prerequisito:** working tree limpio en `main`.
**Objetivo:** foto del estado actual + tests verdes ANTES de tocar nada.

```powershell
# 1.1 Rama limpia
git status
git rev-parse HEAD    # anotar hash de rollback: ________________________________

# 1.2 Versión actual de Reflex
.venv\Scripts\pip.exe show reflex | Select-String "Version"   # Esperado: 0.9.4

# 1.3 Tests línea base (si algo falla AQUÍ, resolver antes de continuar)
$env:PYTHONPATH = "."; .venv\Scripts\pytest.exe -q --no-header 2>&1 | Select-Object -Last 10
# Anotar N tests: ________  (esperado >= 1024, 0 failed)

# 1.4 Backup del entorno actual (NO se commitea)
.venv\Scripts\pip.exe freeze > docs\requirements_backup_pre_098.txt

# 1.5 Backup de requirements.txt versionado actual
Copy-Item requirements.txt docs\requirements_pre_098.txt
```

**Criterio de éxito:** tests 100% verdes, ambos backups creados.
**Si los tests fallan aquí:** detener y resolver primero.

- [ ] 1.1 Rama `main` limpia, hash de rollback anotado
- [ ] 1.2 Reflex 0.9.4 confirmado
- [ ] 1.3 Tests base verdes (N = ____)
- [ ] 1.4 `requirements_backup_pre_098.txt` creado
- [ ] 1.5 `requirements_pre_098.txt` creado

---

## FASE 2 — Crear rama de trabajo

**Duración:** 1 min · **Prerequisito:** FASE 1.
**Objetivo:** aislar todo el experimento fuera de `main`.

```powershell
git checkout -b chore/reflex-0.9.8
git branch --show-current    # Esperado: chore/reflex-0.9.8
```

- [ ] 2.1 Rama `chore/reflex-0.9.8` creada y activa

---

## FASE 3 — Upgrade de dependencias (dry-run primero)

**Duración:** ~15 min · **Prerequisito:** FASE 2.
**Objetivo:** instalar Reflex 0.9.8 dejando que pip resuelva el set de componentes, y ver el diff exacto ANTES de congelar.

```powershell
# 3.1 DRY-RUN: ver qué cambiaría sin instalar nada
.venv\Scripts\pip.exe install reflex==0.9.8 --dry-run 2>&1 | Select-Object -Last 40
# Revisar la lista de "Would install". Anotar qué reflex-components-* cambian.

# 3.2 Instalar de verdad (pip resuelve reflex-components-* compatibles)
.venv\Scripts\pip.exe install reflex==0.9.8

# 3.3 Confirmar versiones núcleo
.venv\Scripts\pip.exe show reflex      | Select-String "Version"   # 0.9.8
.venv\Scripts\pip.exe show reflex-base | Select-String "Version"   # 0.9.8

# 3.4 Confirmar que el fix del tooltip entró (radix)
.venv\Scripts\pip.exe show reflex-components-radix | Select-String "Version"   # >= 0.9.7

# 3.5 Grafo de dependencias consistente
.venv\Scripts\pip.exe check    # Esperado: silencio = OK

# 3.6 Reinstalar tuwayki-core editable por si el resolver lo tocó (NO debería)
#     Verificar que el .pth sigue apuntando a _vendor.
.venv\Scripts\pip.exe show tuwayki-core | Select-String "Location|Editable"
# Si dejó de ser editable: .venv\Scripts\pip.exe install -e _vendor\tuwayki-core

# 3.7 Congelar requirements.txt sincronizado
.venv\Scripts\pip.exe freeze > requirements.txt
```

### Verificación post-freeze

```powershell
# Todos los paquetes reflex-* presentes y coherentes
Select-String "^reflex" requirements.txt

# Paquetes de negocio críticos presentes (no perder ninguno en el freeze)
@("aiomysql","alembic","bcrypt","cryptography","granian","httpx","openpyxl",
  "pydantic","PyJWT","PyMySQL","redis","reflex","reflex-base","reportlab",
  "SQLAlchemy","sqlmodel","starlette","reportlab","pyotp") | ForEach-Object {
    $f = Select-String "^$_==" requirements.txt
    if ($f) { Write-Host "OK: $_" } else { Write-Host "FALTA: $_" -ForegroundColor Red }
}
```

> **Ojo — `pip freeze` NO incluye `tuwayki-core`** (es editable en local). Es correcto y ya está resuelto en los pipelines: Docker lo instala desde `_vendor` (`Dockerfile:27`) y CI desde el SHA git `@ef852f2` (`tests.yml`). **No añadir `tuwayki-core` a `requirements.txt`.** No cambiar el SHA del core en este upgrade (regla de oro).

**Criterio de éxito:** `pip check` sin errores, `reflex==0.9.8` y `reflex-components-radix>=0.9.7` en `requirements.txt`, ningún paquete de negocio "FALTA".

- [ ] 3.1 Dry-run revisado, componentes que cambian anotados
- [ ] 3.2 Reflex 0.9.8 instalado
- [ ] 3.3 reflex + reflex-base en 0.9.8
- [ ] 3.4 reflex-components-radix ≥ 0.9.7 (fix tooltip)
- [ ] 3.5 `pip check` OK
- [ ] 3.6 tuwayki-core sigue editable → _vendor
- [ ] 3.7 requirements.txt congelado y verificado

---

## FASE 4 — Recompilación limpia del frontend

**Duración:** ~10 min · **Prerequisito:** FASE 3.
**Objetivo:** eliminar restos de la 0.9.4 y forzar que Vite/bun reconstruyan desde cero (evita el bug de cache de recharts del upgrade anterior).

```powershell
# 4.1 Borrar el frontend compilado y la cache de Vite
Remove-Item -Recurse -Force .web -ErrorAction SilentlyContinue

# 4.2 Recompilar (Reflex regenera .web con las versiones nuevas)
$env:PYTHONPATH = "."; .venv\Scripts\reflex.exe compile 2>&1 | Select-Object -Last 30
# Aquí se detectan cambios de esquema del TailwindV3Plugin o de componentes.
```

**Si `reflex compile` falla:** el error suele apuntar al componente o plugin incompatible. Anotar en [Incidencias](#registro-de-incidencias) y diagnosticar (no continuar hasta compilar limpio).

- [ ] 4.1 `.web/` borrado
- [ ] 4.2 `reflex compile` termina sin error

---

## FASE 5 — Tests y verificación estática

**Duración:** ~15 min · **Prerequisito:** FASE 4.
**Objetivo:** confirmar que nada se rompió a nivel Python antes de la verificación visual.

```powershell
# 5.1 Suite completa (mismo N que FASE 1, 0 failed)
$env:PYTHONPATH = "."; .venv\Scripts\pytest.exe -q --no-header 2>&1 | Select-Object -Last 15

# 5.2 Compilación de fuentes (sin errores de sintaxis)
.venv\Scripts\python.exe -m compileall -q app scripts

# 5.3 Import del entry point
$env:PYTHONPATH = "."; .venv\Scripts\python.exe -c "import app.app; print('OK')"

# 5.4 Grafo de deps
.venv\Scripts\pip.exe check
```

**Criterio de éxito:** pytest = N/N, compileall silencioso, import "OK", pip check OK.

- [ ] 5.1 pytest N/N verdes (N = ____)
- [ ] 5.2 compileall sin errores
- [ ] 5.3 import `app.app` OK
- [ ] 5.4 pip check OK

---

## FASE 6 — Verificación funcional local (regresión dirigida)

**Duración:** ~30 min · **Prerequisito:** FASE 5.
**Objetivo:** arrancar la app y probar cada superficie que depende de un `reflex-components-*` que cambió.

```powershell
$env:PYTHONPATH = "."; .venv\Scripts\reflex.exe run
# Esperar "App running at http://localhost:3000"
```

Verificar en el navegador (consola abierta para cazar errores de hidratación):

- [ ] 6.1 Landing (`/`) carga sin errores de consola
- [ ] 6.2 Login (`/login`) carga y acepta credenciales
- [ ] 6.3 **Dashboard** — gráficos recharts renderizan (⚠️ punto crítico histórico)
- [ ] 6.4 **Caja** — el `rx.tooltip` de detalles de pago (`_sales.py`) abre/cierra bien (aquí se ve el fix)
- [ ] 6.5 Tooltips custom (iconos) siguen funcionando — `twk-tooltip.js` intacto
- [ ] 6.6 **Toasts/sonner** — disparar una acción y confirmar notificación
- [ ] 6.7 **Iconos lucide** — ninguno aparece roto/vacío (verificar que no cambiaron nombres de clase)
- [ ] 6.8 Owner/backoffice (`/owner`) — badges y botones con tooltip CSS
- [ ] 6.9 Módulos que usen plotly / dataeditor / gridjs / markdown / moment / react-player (si aplica)
- [ ] 6.10 Tema Radix (indigo/slate, radius medium) sin cambios visuales
- [ ] 6.11 No hay errores 500 ni nuevos errores React de hidratación en consola

> **Errores internos de Reflex ESPERADOS (no corregir — heredados del plan 0.9.4):**
> - `UNSAFE_componentWillMount` en `react-helmet` (dependencia interna de Reflex).
> - `TextField.Root` con `value`+`defaultValue` en `rx.debounce_input`.
> - React #418 hydration mismatch solo en prod/Docker (la UI se regenera en cliente, funciona).
> Anotar solo errores **nuevos** que no estén en esta lista.

**Criterio de éxito:** todas las superficies OK, sin errores nuevos.

---

## FASE 7 — Commit, push y CI

**Duración:** ~10 min · **Prerequisito:** FASE 6 exitosa.

```powershell
# 7.1 Revisar el diff — DEBE ser solo requirements.txt (+ cualquier fix puntual necesario)
git diff --name-only
# ⚠️ Si aparece algo bajo _vendor/tuwayki-core/ → DETENER (viola la regla de oro)

# 7.2 Merge a main (o abrir PR si prefieres revisión)
git add requirements.txt
# (agregar aquí SOLO archivos que haya que tocar por incompatibilidad real)
git commit -m "chore(deps): upgrade reflex 0.9.4 -> 0.9.8 + sync requirements

- reflex/reflex-base 0.9.4 -> 0.9.8; componentes resueltos por pip
- radix 0.9.3 -> 0.9.7 (fix tooltip Radix reopen/second-hover)
- Motivos: fixes Windows (stylesheet backslash, hydration MIME) + cierre Redis
- Sin cambios en _vendor/tuwayki-core (upgrade aislado a SHOP)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"

git checkout main
git merge --no-ff chore/reflex-0.9.8

# 7.3 Push dual (convención del proyecto)
git push origin HEAD:main HEAD:docker-deploy-prod
```

Verificar CI en GitHub Actions (`tests.yml`): install → pip check → compileall → pytest. Debe quedar **verde**.

- [ ] 7.1 Diff limpio (sin `_vendor/tuwayki-core`)
- [ ] 7.2 Commit + merge a main
- [ ] 7.3 Push dual realizado
- [ ] 7.4 CI GitHub Actions verde

---

## FASE 8 — Verificación cross-system (core intacto + Owner Panel)

**Duración:** ~10 min · **Prerequisito:** FASE 7. **Idealmente:** FOOD y LIFE ya en 0.9.8.
**Objetivo:** confirmar que no tocamos el core y que el Owner Panel sigue orquestando los 3 productos.

```powershell
# 8.1 Confirmar que el commit del upgrade NO tocó el core compartido ni su SHA
git show --stat HEAD | Select-String "tuwayki"
# Esperado: 0 resultados. Si aparece algo, el upgrade se salió de alcance (viola la regla de oro).
```

- [ ] 8.1 El diff del upgrade no incluye `_vendor/tuwayki-core/` ni cambia el SHA del core en `tests.yml`/`Dockerfile`
- [ ] 8.2 **Owner Panel** — `/owner` lista y gestiona empresas contra los 3 productos (SHOP/FOOD/LIFE) sin error
- [ ] 8.3 `/api/admin/companies/*` (owner-api) responde OK contra FOOD y LIFE ya actualizados
- [ ] 8.4 Dejar constancia en el plan de flota (FOOD): "SHOP a 0.9.8 OK; core sin cambios; Owner Panel operativo"

> Cada sistema se actualiza con **su propio runbook** (venv/`.web`/requirements independientes). Este documento cubre **SHOP**; FOOD y LIFE tienen los suyos. SHOP va **último** en el orden de flota, así que al llegar aquí FOOD y LIFE ya deberían estar en 0.9.8.

---

## FASE 9 — Deploy SVR de Prueba (Docker)

**Duración:** ~15-25 min · **Prerequisito:** CI verde.

```bash
ssh <usuario>@<ip-prueba>
cd /ruta/al/proyecto

git log --oneline -3
git pull origin main
docker compose build          # reinstala requirements.txt (Reflex 0.9.8) + reconstruye Vite
docker compose up -d
docker compose ps             # todos "Up (healthy)" (esperar hasta ~5 min primer arranque)

docker compose logs tuwayki_landing --tail=50   # migraciones/arranque
```

Smoke + manual:

```bash
bash scripts/smoke_deploy.sh https://<dominio-prueba>   # 0 FAIL
```

- [ ] 9.1 git pull en SVR prueba
- [ ] 9.2 docker compose build OK (3 imágenes)
- [ ] 9.3 docker compose up -d
- [ ] 9.4 `docker compose ps` todos healthy
- [ ] 9.5 `/api/ping` OK en los 3 servicios
- [ ] 9.6 Smoke test 0 FAIL
- [ ] 9.7 Barrido manual: dashboard (recharts), caja (tooltip), toasts, iconos

**Si algo falla:** ver [Rollback](#rollback). NO continuar a producción.

---

## FASE 10 — Deploy SVR de Producción (Docker)

**Duración:** ~20 min · **Prerequisito:** FASE 9 exitosa.
**Recomendación:** horario de baja carga.

```bash
# Pre-check en local: main y docker-deploy-prod en el mismo commit
git log --oneline origin/main -3
git log --oneline origin/docker-deploy-prod -3

# En el SVR de producción
ssh <usuario>@<ip-prod>
cd /ruta/al/proyecto
git pull origin main
docker compose build
docker compose up -d
docker compose ps
```

Verificar en los 3 dominios:

```bash
curl -sf https://tuwayki.app/api/health
curl -sf https://sys.tuwayki.app/api/health
curl -sf https://admin.tuwayki.app/api/health
bash scripts/smoke_deploy.sh https://sys.tuwayki.app
```

- [ ] 10.1 git pull en prod
- [ ] 10.2 docker compose build
- [ ] 10.3 docker compose up -d → healthy
- [ ] 10.4 /api/health OK en los 3 dominios
- [ ] 10.5 Smoke test prod 0 FAIL
- [ ] 10.6 Verificación manual: login real, dashboard, caja, owner

---

## FASE 11 — Cierre

**Duración:** ~5 min · **Prerequisito:** FASE 10.

```powershell
# Limpiar backups temporales
Remove-Item docs\requirements_backup_pre_098.txt, docs\requirements_pre_098.txt -ErrorAction SilentlyContinue
```

- [ ] 11.1 Backups temporales eliminados
- [ ] 11.2 Memoria del proyecto actualizada (registrar: Reflex 0.9.8, motivo real = fixes Windows+Redis, core no tocado)
- [ ] 11.3 Este documento marcado **COMPLETADO** y sección "Estado inicial" actualizada
- [ ] 11.4 Borrar rama: `git branch -d chore/reflex-0.9.8`

---

## Rollback — qué hacer si algo sale mal

### Local (antes de push)

```powershell
# Descartar todo el experimento: volver a main intacto
git checkout main
git branch -D chore/reflex-0.9.8

# Restaurar el entorno 0.9.4 exacto
.venv\Scripts\pip.exe install -r docs\requirements_backup_pre_098.txt
Remove-Item -Recurse -Force .web    # recompila limpio en el próximo run
```

### SVR Prueba/Prod (si el deploy falló)

```bash
# Opción A: script del proyecto
bash scripts/deploy.sh --rollback    # git reset al commit en .deploy_prev_commit

# Opción B: manual
git log --oneline -5                 # identificar commit pre-upgrade
git reset --hard <hash-pre-upgrade>
docker compose build && docker compose up -d
```

### GitHub (si CI pasó pero el código es malo)

```bash
git revert HEAD --no-edit
git push origin HEAD:main HEAD:docker-deploy-prod
```

---

## Registro de incidencias

| # | Fase | Archivo/Componente | Síntoma | Fix aplicado | Estado |
|---|---|---|---|---|---|
| 1 | 1 | venv (`pip.exe`/`reflex.exe`) | Shims `.exe` rotos (exit 1) por venv creado en ruta vieja `C:\...` y proyecto movido a `D:\`. | **Regenerados** con `pip install --force-reinstall --no-deps <pkg>` (reescribe el `.exe` con ruta D:). alembic revertido a pin 1.18.4 tras el reinstall. Los 4 shims (pip/reflex/pytest/alembic) OK desde D:. | ✅ Resuelto |
| 2 | 3 | `requirements.txt` | `pip freeze` completo contamina la lista curada de producción con dev-deps (pytest, playwright, pandas…). | Restaurar original y editar solo las 12 líneas de Reflex a mano. | ✅ Resuelto |
| 3 | 4 | `app/pages/owner/_page.py:94` | Icono `check-circle` inválido en lucide 1.0.3 → caía a `circle_help`. | Cambiado a `circle-check` (nombre válido, coherente con el resto). | ✅ Corregido |
| 4 | — | `.claude/launch.json` | 4 `runtimeExecutable` con ruta vieja `C:\...\Sistema-de-Ventas\.venv`. | Reemplazadas por `D:\PROYECTOS\...`. (Archivo local, no trackeado.) | ✅ Corregido |
| 5 | 6 | Smoke websocket (dev) | "Connection Error" en pruebas manuales → parecía fallo de ws en puertos alternos. | **RESUELTO**: era el token viejo en `localStorage` (navegador manual reutilizado). Playwright con navegador limpio → ws round-trip OK. `/_event` sí se proxea en 3010. | ✅ Resuelto |
| 6 | 6 | `rxconfig.py` — TailwindV3Plugin (content-glob) | **REGRESIÓN 0.9.x**: los botones "Ingresar/Registro" del header de la landing (`/shop`, `/food`, `/life`) quedaban `display:none` en desktop. Causa: Reflex 0.9.x compila los componentes compartidos a `.web/app_components/**`, dir que NO está en el content-glob por defecto (`./app/**`, `./utils/**`). La clase `md:inline-flex` usada SOLO en el header nunca se generaba en el CSS. | Se pasa `content` explícito incluyendo `./app_components/**` y `./components/**`. Verificado: `md\:inline-flex` ahora sí en el CSS y los 3 detail-pages muestran login+registro en desktop. Menú móvil (details/summary) ya funcionaba. Commit `67fe7ee`. | ✅ Corregido |
| — | 8 | **FLOTA**: FOOD y LIFE | La incidencia #6 es del build 0.9.x compartido → **FOOD y LIFE muy probablemente tienen el mismo content-glob incompleto**. Si usan clases responsivas SOLO en componentes de `app_components/`, quedarán ocultas. | Cada sesión debe añadir `./app_components/**` (y `./components/**`) al `content` de su `TailwindV3Plugin` y rebuildear. **Pendiente de coordinar.** | ⚠️ A verificar en FOOD/LIFE |
| — | 1/5 | `tests/test_e2e.py` (×4) | Fallan por Playwright sin navegador/servidor. **Pre-existente** (mismo fallo antes y después del upgrade). | N/A — infra, no del upgrade. | ⚪ Baseline |
| — | — | core editable local | `import tuwayki_core` resuelve a `D:\PROYECTOS\tuwayki-core` (repo canónico), no a `_vendor/`. Docker usa `_vendor`; CI usa git SHA. | Solo dato — sin acción. | ℹ️ Nota |

---

## Dependencias entre fases

```
FASE 1 (snapshot+tests) → FASE 2 (rama) → FASE 3 (upgrade+freeze) → FASE 4 (recompile limpio)
    → FASE 5 (tests/estático) → FASE 6 (verificación funcional) → FASE 7 (commit+push+CI)
        → FASE 8 (cross-system FOOD/LIFE) 
        → FASE 9 (SVR prueba) → FASE 10 (SVR prod) → FASE 11 (cierre)
```

Todas secuenciales. FASE 8 puede correr en paralelo a FASE 9 (es solo verificación documental).

---

## Dónde quedamos (actualizar al final de cada sesión)

```
Fecha última sesión: 2026-08-09 (FASE 1-6 + E2E END-TO-END total 3 servicios + fix landing #6)
Última fase completada: FASE 6 COMPLETA — E2E END-TO-END de TODO el stack SHOP en 0.9.8:
   - Landing(3000): publico, hidratación OK, /shop /food /life muestran login+registro (fix #6)
   - Sys(3001): login real + dashboard(6 recharts) + 17 módulos autenticados => 20/20
   - Admin/Owner(3002): login owner + 4 secciones + 7 empresas + modales abren/cierran => 11/11
   - Interactivo Sys: búsqueda, combobox, modal "Ver desglose", reportes (5 rangos + generar) OK
   - 0 errores de consola en los 3 servicios. Overlays/modales (motivo del upgrade) confirmados.
   commits 3f286a4 + 70a2247 + ed6b577 + 84ca1ec + 9fb46bc + 67fe7ee (fix landing) en chore/reflex-0.9.8
Próxima acción: FASE 7 (merge+push, lo hace Trebor) → 9/10 (deploy ordenado, SHOP último)
   Stack SHOP local 100% en 0.9.8 (landing+sys+admin healthy, reflex 0.9.8 verificado en los 3)
   PENDIENTE FLOTA: avisar a FOOD/LIFE del fix #6 (content-glob app_components) — ver Incidencias
Resultado E2E publico (runner standalone dev, frontend 3010):
   [PASS] /api/ping  [PASS] login renderiza  [PASS] login invalido->error (ws round-trip)
   [PASS] /venta sin auth->login  [PASS] /caja sin auth->login   => 5/5
Resultado E2E AUTENTICADO (Docker 0.9.8 real, single-origin localhost:3001, DB real):
   [PASS] login admin  [PASS] dashboard recharts OK (6 charts)
   [PASS] 17 modulos autenticados sin errores de consola:
     venta, caja, inventario, ingreso, compras, reposicion, clientes, cuentas,
     historial, reportes, servicios, presupuestos, documentos-fiscales,
     configuracion, listas-precios, etiquetas, promociones   => 20/20
   STACK LOCAL COMPLETO EN 0.9.8: landing(3000)+sys(3001)+admin(3002) reconstruidos y
   healthy, los 3 con reflex 0.9.8 verificado. /api/ping=200 en los 3. mysql/redis intactos.
Hash de rollback: cef73ab5a4c2ed0b8eb1dd981ec307018104e853
Resultado FASE 1-5:
  - Reflex 0.9.8 + radix 0.9.7 instalado; pip check OK; reflex compile OK (74 pág, 134s)
  - pytest: 1274 passed, 1 skipped, 4 failed (e2e Playwright, pre-existentes por infra)
  - Fix aplicado: icono check-circle->circle-check (owner/_page.py). Ver Incidencias.
  - venv: usar `python -m <tool>` (shims .exe rotos por relocalización C:->D:)
Notas:
  - ROLLOUT DE FLOTA en 3 sesiones paralelas. Orden: core → FOOD → LIFE → SHOP → deploy.
    Plan maestro en Sistema-para-Food/PLAN_ACTUALIZACION_REFLEX.md
  - VERIFICADO: TailwindV3Plugin existe en 0.9.8 sin deprecación (riesgo #1 descartado)
  - VERIFICADO: único breaking 0.9.4→0.9.8 = REFLEX_USE_TURBOPACK (no usado) → cero impacto API
  - VERIFICADO: SHOP tiene 0 usos del método .foreach deprecado (nada que migrar)
  - VERIFICADO: tuwayki-core agnóstico de Reflex → FOOD/LIFE no afectados por el upgrade de SHOP
  - OJO drift de core: SHOP CI @ef852f2 vs FOOD @64850c8 (SHAs distintos). Higiene aparte, NO tocar aquí.
  - Owner Panel (en SHOP) orquesta FOOD+LIFE vía /api/admin/companies/* → verificar en FASE 8
  - Motivo real del upgrade = fixes Windows (stylesheet/hydration) + cierre Redis, NO el tooltip
  - El sistema custom de tooltips (twk-tooltip.js) se MANTIENE, no se desmonta
```

---

## Deuda técnica / follow-ups (post-0.9.8, NO bloquean el rollout)

| # | Tema | Detalle | Decisión sugerida |
|---|---|---|---|
| DT-1 | **Unificar plugin de Tailwind → v4** | Inconsistencia de flota: **SHOP usa `TailwindV3Plugin`**, **FOOD y LIFE usan `TailwindV4Plugin`**. La versión de Reflex sí quedó alineada (0.9.8); el plugin de Tailwind no. No bloquea nada (los 3 andan al 100%). | **Iniciativa separada, DESPUÉS de que 0.9.8 esté en prod.** Rama propia por sistema, migrar SHOP v3→v4, y **E2E visual completo** (riesgo de regresión de estilos en toda la app). No mezclar con este upgrade de versión. Unificar hacia v4 (donde ya están 2 de 3). |
| DT-2 | **Drift de SHA de `tuwayki-core`** | SHOP CI `@ef852f2` vs FOOD `@64850c8`; LIFE sin `_vendor`. Pre-existente, higiene aparte. | Re-pinnear los 3 al mismo SHA canónico de forma coordinada, en su propia tarea. |
| DT-3 | **content-glob `app_components`** | Regresión 0.9.x ya **corregida en los 3** (SHOP `67fe7ee` real; LIFE `9b80fbf` y FOOD `f9bb1be` como blindaje). Ver [Incidencias](#registro-de-incidencias) #6. | Cerrado. Solo queda que FOOD/LIFE incluyan su commit en el merge y no lo dupliquen. |

---

## Referencia rápida

```powershell
# Tests
$env:PYTHONPATH = "."; .venv\Scripts\pytest.exe -q --no-header

# Versión Reflex
.venv\Scripts\pip.exe show reflex | Select-String "Version"

# Recompilar limpio
Remove-Item -Recurse -Force .web; $env:PYTHONPATH="."; .venv\Scripts\reflex.exe compile

# Arrancar dev
$env:PYTHONPATH = "."; .venv\Scripts\reflex.exe run

# Push dual
git push origin HEAD:main HEAD:docker-deploy-prod
```

| Archivo clave | Propósito |
|---|---|
| `requirements.txt` | Deps Python (venv + Docker) — lo que cambia en este upgrade |
| `rxconfig.py` | Config Reflex (plugins Tailwind/Radix, DB, Redis) |
| `app/app.py` | Entry point, routing, carga de `twk-tooltip.js` |
| `_vendor/tuwayki-core/` | ⛔ NO TOCAR en este upgrade (compartido con FOOD/LIFE) |
| `Dockerfile` / `docker-compose.yml` | Deploy multi-contenedor |
| `scripts/deploy.sh` / `smoke_deploy.sh` | Deploy y smoke test en SVR |
| `.github/workflows/tests.yml` | CI automático |
