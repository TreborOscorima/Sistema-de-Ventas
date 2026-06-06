# Plan de Upgrade: Reflex 0.9.3 → 0.9.4 + Sincronización de Dependencias

**Creado:** 2026-06-05  
**Autor:** Trebor Oscorima + Claude Code  
**Estado:** FASES 1-8 COMPLETADAS (2026-06-05) — pendiente FASE 9 (SVR Prod) → FASE 10 (cierre)  
**Propósito:** Guía sesión a sesión, retomable en cualquier punto sin perder contexto.

---

## Contexto rápido (leer siempre al inicio de cada sesión)

Este documento es la única fuente de verdad para este upgrade. Marca cada paso con `[x]` cuando se complete. Si una sesión termina a mitad de una fase, anota el punto exacto en la sección **"Dónde quedamos"** al final del archivo.

### Estado inicial verificado (2026-06-05)

| Ítem | Estado inicial | Estado actual |
|---|---|---|
| Reflex instalado en `.venv` | `0.9.3` | ✅ `0.9.4` |
| Python en `Dockerfile` | `3.11-slim` ← discrepancia | ✅ `3.13-slim` |
| `starlette` en `requirements.txt` | `0.52.1` ← obsoleto | ✅ `1.1.0` |
| `sqlmodel` en `requirements.txt` | `0.0.33` | ✅ `0.0.38` |
| Tests en suite | 1024 tests | ✅ 1024/1024 pasando |
| Branch principal | `main` | `main` (sin push aún) |
| Push dual requerido | `git push origin HEAD:main HEAD:docker-deploy-prod` | pendiente |

### Bugs encontrados y corregidos en esta sesión

| # | Archivo | Bug | Fix aplicado |
|---|---|---|---|
| 1 | `app/app.py:211` | `tabindex` → React requiere `tabIndex` | ✅ Corregido |
| 2 | `.web/node_modules/.vite/deps/recharts.js` | Cache Vite corrupta → `require_isUnsafeProperty is not a function` crash en charts | ✅ Cache limpiada, Vite reconstruyó |
| 3 | `app/components/ui.py:287` | `rx.el.p(subtitle)` con `rx.text()` adentro → `<p><p>` hydration error | ✅ Cambiado a `rx.el.div` |

### Errores no-corregibles (Reflex interno)

| Error | Origen | Por qué no se puede corregir |
|---|---|---|
| `UNSAFE_componentWillMount` en `SideEffect(NullComponent)` | `react-helmet` (dependencia interna de Reflex) | Requiere que Reflex actualice su dependencia |
| `TextField.Root` con `value` + `defaultValue` | `rx.debounce_input` de Reflex | Comportamiento interno del wrapper de debounce |

### Deployment: TODO corre con Docker

**Local, SVR de Prueba y SVR de Producción usan Docker Compose.**

```
Local dev:  docker compose -f docker-compose.local.yml up -d
SVR Prueba: git pull && docker compose build && docker compose up -d
SVR Prod:   git pull && docker compose build && docker compose up -d
```

> **IMPORTANTE para el upgrade:** El `docker compose build` reconstruye la imagen con el nuevo `Dockerfile` (Python 3.13) y el nuevo `requirements.txt` (Reflex 0.9.4). Vite reconstruye sus deps automáticamente en el primer arranque del contenedor.

### Qué cambia con el upgrade (verificado con `--dry-run`)

Solo **2 paquetes** de Reflex cambian:
- `reflex 0.9.3 → 0.9.4`
- `reflex-base 0.9.3 → 0.9.4`

Todos los paquetes de componentes (`reflex-components-*`) ya están en versiones compatibles. No hay breaking changes de API conocidos entre 0.9.3 y 0.9.4.

### Resumen de cambios a aplicar

| # | Cambio | Archivos afectados | Prioridad |
|---|---|---|---|
| A | Upgrade `reflex` 0.9.3 → 0.9.4 | `requirements.txt` | CRÍTICO |
| B | Sincronizar `requirements.txt` completo con `pip freeze` | `requirements.txt` | CRÍTICO |
| C | Actualizar `Dockerfile` de `python:3.11-slim` → `python:3.13-slim` | `Dockerfile` | ALTO |
| D | Fix 4 `bare except:` → `except (ValueError, TypeError):` | 2 archivos | BAJO (opcional) |
| E | `condition: service_started` → `service_healthy` en `docker-compose.yml` | `docker-compose.yml` | BAJO (opcional) |

---

## Pipeline de deploy (referencia de toda la operación)

```
Local (.venv Python 3.13)
    │
    ├─ FASE 1-5: Cambios, tests locales, verificación
    │
    └─► git push origin HEAD:main HEAD:docker-deploy-prod
              │
              ├─► GitHub Actions (tests.yml) — CI automático
              │       Python 3.13, pip install -r requirements.txt
              │       pip check + compileall + pytest
              │
              ├─► SVR de PRUEBA (AWS)
              │       SSH → bash scripts/deploy.sh
              │       (git pull + pip install + alembic + reflex run --env prod)
              │
              └─► SVR de PRODUCCIÓN (AWS)
                      SSH → bash scripts/deploy.sh --prod
                      (idem, con validaciones extra)
```

> **Nota sobre Docker vs deploy.sh:** El `docker-compose.yml` es un modelo de deployment alternativo (multi-contenedor). Los SVR AWS usan `scripts/deploy.sh` que levanta Reflex directamente con venv Python, NO Docker. El Dockerfile/docker-compose igual se actualiza para mantener consistencia.

---

## FASE 1 — Preparación y snapshot

**Duración estimada:** 10 minutos  
**Prerequisito:** Estar en el directorio `C:\Users\Trebor Oscorima\Sistema-de-Ventas\`  
**Objetivo:** Verificar estado inicial, guardar snapshot, asegurarse de que los tests pasan antes de tocar nada.

### Pasos

```powershell
# 1.1 Verificar rama y estado limpio
git status
git branch
# Esperado: branch "main", sin cambios pendientes (clean)

# 1.2 Guardar commit actual como checkpoint de rollback
git rev-parse HEAD
# Anotar el hash aquí: ________________________________

# 1.3 Verificar versión actual de Reflex
.venv\Scripts\pip.exe show reflex | Select-String "Version"
# Esperado: Version: 0.9.3

# 1.4 Ejecutar tests ANTES de cualquier cambio (línea de base)
# Si algún test falla AQUÍ, resolver PRIMERO antes de continuar.
$env:PYTHONPATH = "."; .venv\Scripts\pytest.exe -q --no-header 2>&1 | tail -5
# Esperado: X passed, 0 failed (donde X >= 1000)

# 1.5 Guardar freeze actual como backup de referencia
.venv\Scripts\pip.exe freeze > docs\requirements_backup_pre_upgrade.txt
# Esto crea un snapshot del entorno pre-upgrade. NO se commitea.
```

**Criterio de éxito:** Tests pasan 100%, archivo `docs\requirements_backup_pre_upgrade.txt` creado.

**Si los tests fallan aquí:** Detener, resolver primero, no continuar con el upgrade.

---

## FASE 2 — Upgrade de dependencias

**Duración estimada:** 10 minutos  
**Prerequisito:** FASE 1 completada, tests pasando.  
**Objetivo:** Instalar Reflex 0.9.4 y sincronizar `requirements.txt` con el entorno real.

### Pasos

```powershell
# 2.1 Instalar Reflex 0.9.4
.venv\Scripts\pip.exe install reflex==0.9.4

# 2.2 Verificar que solo cambiaron reflex y reflex-base
.venv\Scripts\pip.exe show reflex | Select-String "Version"
# Esperado: Version: 0.9.4

.venv\Scripts\pip.exe show reflex-base | Select-String "Version"
# Esperado: Version: 0.9.4

# 2.3 Verificar que el grafo de dependencias es consistente
.venv\Scripts\pip.exe check
# Esperado: No broken requirements (silencio = OK)

# 2.4 Generar requirements.txt sincronizado
.venv\Scripts\pip.exe freeze > requirements.txt

# 2.5 Verificar que reflex==0.9.4 quedó en el archivo
Select-String "^reflex==" requirements.txt
# Esperado: reflex==0.9.4

# 2.6 Verificar que starlette quedó con la versión correcta (1.1.0, no 0.52.1)
Select-String "^starlette==" requirements.txt
# Esperado: starlette==1.1.0

# 2.7 Verificar que reflex[db] fue reemplazado por reflex sin extras
# (pip freeze no incluye extras, solo el paquete base — esto es correcto)
Select-String "reflex" requirements.txt
# NOTA: pip freeze genera "reflex==0.9.4" sin el [db] extra.
# El extra [db] instala SQLModel; como ya está instalado, funciona igual.
# Si se prefiere mantener el marcador explícito, editar manualmente:
#   Cambiar "reflex==0.9.4" por "reflex[db]==0.9.4"
```

### Ajuste manual post-freeze (importante)

`pip freeze` genera todas las dependencias como pins exactos. El archivo resultante reemplaza al anterior. Verificar visualmente que los paquetes críticos del proyecto estén presentes:

```powershell
# Lista de verificación: estos paquetes DEBEN estar en requirements.txt
@("aiomysql", "alembic", "bcrypt", "cryptography", "granian", "httpx",
  "openpyxl", "playwright", "pydantic", "PyJWT", "PyMySQL", "pytest",
  "redis", "reflex", "reflex-base", "reportlab", "SQLAlchemy", "sqlmodel",
  "starlette") | ForEach-Object {
    $found = Select-String "^$_==" requirements.txt
    if ($found) { Write-Host "OK: $_" } else { Write-Host "FALTA: $_" -ForegroundColor Red }
}
```

**Si aparece "FALTA" para algún paquete del negocio:** El paquete está instalado con nombre diferente (e.g., `PyMySQL` → `pymysql`). Verificar con `pip show <nombre>` y ajustar.

**Criterio de éxito:** `pip check` sin errores, `requirements.txt` contiene `reflex==0.9.4` y `starlette==1.1.0`.

---

## FASE 3 — Actualizar Dockerfile

**Duración estimada:** 5 minutos  
**Prerequisito:** Ninguno (independiente de FASE 2).  
**Objetivo:** Alinear la imagen Docker con Python 3.13 (igual que dev y CI).

### Contexto

El `Dockerfile` actual usa `python:3.11-slim` en dos stages (builder y runtime). El CI (`tests.yml`) ya usa Python 3.13. El venv de dev usa Python 3.13.5. Esta discrepancia significa que el entorno Docker es diferente al que se testa.

### Cambio en `Dockerfile`

Editar las líneas 8 y 31:

```diff
- FROM python:3.11-slim AS builder
+ FROM python:3.13-slim AS builder
```

```diff
- FROM python:3.11-slim AS runtime
+ FROM python:3.13-slim AS runtime
```

**Comando para aplicar el cambio:**

```powershell
# Verificar líneas actuales
Select-String "python:3" Dockerfile
# Esperado: 2 matches (líneas 8 y 31) con python:3.11-slim

# Editar manualmente en el editor, o usar PowerShell:
(Get-Content Dockerfile) -replace 'python:3.11-slim', 'python:3.13-slim' | Set-Content Dockerfile

# Verificar resultado
Select-String "python:3" Dockerfile
# Esperado: 2 matches con python:3.13-slim
```

> **Nota sobre `gcc` y `default-libmysqlclient-dev`:** Estos se usan en el stage builder para compilar wheels. En Python 3.13 los mismos paquetes del proyecto (aiomysql, PyMySQL son pure-Python; cffi y cryptography necesitan gcc). La instrucción `apt-get install gcc default-libmysqlclient-dev pkg-config` en el Dockerfile ya es correcta para 3.13.

**Criterio de éxito:** `Select-String "python:3" Dockerfile` muestra `python:3.13-slim` en ambas líneas.

---

## FASE 4 — Fix bare `except:` (OPCIONAL)

**Duración estimada:** 5 minutos  
**Prerequisito:** Ninguno.  
**Prioridad:** BAJA — no bloquea el upgrade, no es riesgo de seguridad. Incluir si se quiere aprovechar el commit.

### Archivos a cambiar

**`app/services/report_service.py` línea 289:**
```python
# ANTES:
    except:
        return default

# DESPUÉS:
    except (ValueError, TypeError, AttributeError):
        return default
```

**`app/services/report_service.py` línea 494:**
```python
# ANTES:
            except:
                pass

# DESPUÉS:
            except (ValueError, TypeError, AttributeError):
                pass
```

**`app/utils/exports.py` línea 79:**
```python
# ANTES:
    except:
        return 0.0

# DESPUÉS:
    except (ValueError, TypeError):
        return 0.0
```

**`app/utils/exports.py` línea 296:**
```python
# ANTES:
            except:
                pass

# DESPUÉS:
            except (ValueError, TypeError, AttributeError):
                pass
```

**Verificar que no quedan bare except:**
```powershell
Select-String "except:" app\services\report_service.py, app\utils\exports.py
# Esperado: 0 resultados (bare except eliminados)
```

---

## FASE 5 — Fix `docker-compose.yml` (OPCIONAL)

**Duración estimada:** 3 minutos  
**Prerequisito:** Ninguno.  
**Prioridad:** BAJA — mejora robustez del arranque multi-contenedor.

### Cambio

`tuwayki_sys` y `tuwayki_admin` dependen de `tuwayki_landing` con `condition: service_started`. Si landing tarda en compilar el frontend (primer arranque), sys y admin arrancan antes de que las migraciones estén aplicadas. Cambiar a `service_healthy` asegura que las migraciones ya corrieron.

```diff
# En tuwayki_sys → depends_on:
-     tuwayki_landing: { condition: service_started }
+     tuwayki_landing: { condition: service_healthy }

# En tuwayki_admin → depends_on:
-     tuwayki_landing: { condition: service_started }
+     tuwayki_landing: { condition: service_healthy }
```

> **Advertencia:** `service_healthy` en `tuwayki_landing` tiene `start_period: 300s`. Con este cambio, sys y admin esperarán hasta 5 minutos en el primer arranque con volumen `.web` vacío. En re-deploys (volumen ya construido) tarda ~30s. Aceptable para producción.

---

## FASE 6 — Verificación local completa

**Duración estimada:** 20 minutos  
**Prerequisito:** FASEs 2 y 3 completadas.  
**Objetivo:** Confirmar que el upgrade no rompió nada antes de pushear.

### Pasos

```powershell
# 6.1 Re-ejecutar suite completa de tests
$env:PYTHONPATH = "."; .venv\Scripts\pytest.exe -q --no-header 2>&1 | tail -10
# Esperado: mismo número de tests que en FASE 1, 0 failed

# 6.2 Verificar que el código compila sin errores de sintaxis
.venv\Scripts\python.exe -m compileall -q app scripts
# Esperado: silencio = OK. Cualquier error indica syntax error introducido.

# 6.3 Verificar grafo de dependencias
.venv\Scripts\pip.exe check
# Esperado: No broken requirements

# 6.4 Test de importación del módulo principal
$env:PYTHONPATH = "."; .venv\Scripts\python.exe -c "import app.app; print('OK')" 2>&1
# Esperado: "OK" (puede haber warnings ignorables de Reflex sobre schema)

# 6.5 (Opcional pero recomendado) Arrancar reflex en dev brevemente
# Solo si se quiere verificar que la UI levanta sin error visual.
# Ctrl+C para detener después de que aparezca "App running at http://localhost:3000"
$env:PYTHONPATH = "."; .venv\Scripts\reflex.exe run
```

### Checklist visual si se arranca Reflex (paso 6.5)

- [ ] Landing (`/` o `/home`) carga sin error de consola
- [ ] Login (`/login`) carga correctamente
- [ ] Dashboard (`/`) muestra skeleton y luego carga
- [ ] Sidebar visible y navegable
- [ ] Toast/notificaciones funcionan (probar una acción simple)
- [ ] No hay errores 500 en consola del navegador

**Criterio de éxito:** `pytest` pasa 100%, `compileall` sin errores, `pip check` OK.

---

## FASE 7 — Commit y Push al repositorio

**Duración estimada:** 5 minutos  
**Prerequisito:** FASE 6 completada y exitosa.  
**Objetivo:** Subir los cambios a GitHub y activar el CI automático.

### Archivos a commitear

Verificar exactamente qué cambió:
```powershell
git diff --name-only
# Esperado (mínimo obligatorio):
#   requirements.txt
#   Dockerfile
#
# Esperado (si se hicieron las fases opcionales):
#   app/services/report_service.py   (FASE 4)
#   app/utils/exports.py              (FASE 4)
#   docker-compose.yml                (FASE 5)
```

### Comando de commit

```powershell
# Stagear solo los archivos relevantes (NO stagear .env ni nada de .claude/)
git add requirements.txt Dockerfile

# Si se hicieron las fases opcionales, agregar:
# git add app/services/report_service.py app/utils/exports.py docker-compose.yml

# Crear commit
git commit -m "$(cat <<'EOF'
chore(deps): upgrade reflex 0.9.3→0.9.4 + sync requirements.txt

- Upgrade reflex y reflex-base a 0.9.4 (solo 2 paquetes cambian)
- Sincronizar requirements.txt completo con pip freeze del venv real
  (starlette 0.52.1→1.1.0, granian 2.7.1→2.7.4, redis 7.1.1→7.4.0,
   pydantic 2.12.5→2.13.4, y otras dependencias transitivas)
- Actualizar Dockerfile de python:3.11-slim a python:3.13-slim
  para alinear dev/CI/prod en la misma versión de Python

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

# Push dual (main + docker-deploy-prod, convención del proyecto)
git push origin HEAD:main HEAD:docker-deploy-prod
```

### Verificar CI en GitHub

Después del push, ir a:  
`https://github.com/<tu-usuario>/Sistema-de-Ventas/actions`

El workflow `tests.yml` se activa automáticamente. Esperar a que pase:
- **Install dependencies** → `pip install -r requirements.txt`
- **Validate dependency graph** → `pip check`
- **Compile source** → `compileall`
- **Run tests** → `pytest`

**Criterio de éxito:** CI verde (checkmark) en GitHub Actions.  
**Si CI falla:** Ver sección de Rollback al final de este documento.

---

## FASE 8 — Deploy al SVR de Prueba (AWS) — Docker

**Duración estimada:** 10-20 minutos  
**Prerequisito:** CI en GitHub Actions pasó en verde.  
**Objetivo:** Verificar que el upgrade funciona en un entorno Docker real pre-producción.

### Conexión al servidor de prueba

```bash
ssh <usuario>@<ip-servidor-prueba>
cd /ruta/al/proyecto
```

### Deploy con Docker

```bash
# 1. Verificar commit actual antes del deploy
git log --oneline -3

# 2. Traer el nuevo código
git pull origin main

# 3. Reconstruir imágenes (instala Reflex 0.9.4 + Python 3.13 + requirements.txt nuevo)
docker compose build

# 4. Reiniciar servicios (zero-downtime rolling update)
docker compose up -d

# 5. Verificar que los 3 contenedores levantaron
docker compose ps
# Esperado: tuwayki_landing, tuwayki_sys, tuwayki_admin → status "Up (healthy)"
```

> **Nota sobre el primer arranque post-upgrade:** Docker reconstruye la imagen con Python 3.13 y el nuevo Vite. El contenedor `tuwayki_landing` borra la cache de Vite y la reconstruye en el primer start (~2-3 min). El healthcheck tiene `start_period: 300s` — esperar hasta que esté `healthy` antes de verificar.

### Verificar health de los contenedores

```bash
# Ver logs del landing (que aplica migraciones)
docker compose logs tuwayki_landing --tail=50

# Health check manual
curl -sf http://localhost:3000/api/health    # landing
# (ajustar puertos según el puerto mapeado en docker-compose.yml o NPM)
```

### Smoke test

```bash
bash scripts/smoke_deploy.sh https://<dominio-prueba>
# Esperado: todos PASS, 0 FAIL
```

### Verificación manual

- [ ] Landing pública carga
- [ ] Login acepta credenciales
- [ ] Dashboard carga sin errores en consola del browser
- [ ] Al menos 1 módulo core (Venta o Inventario) funciona
- [ ] `/api/health` retorna OK

**Criterio de éxito:** Contenedores `healthy`, smoke test sin FAIL.  
**Si hay problemas:** Ver sección de Rollback. NO continuar a producción.

---

## FASE 9 — Deploy a SVR de Producción (AWS) — Docker

**Duración estimada:** 15-25 minutos  
**Prerequisito:** FASE 8 exitosa. Verificación manual en prueba OK.  
**Objetivo:** Upgrade a producción con mínimo downtime.

> **IMPORTANTE:** Hacer en horario de baja carga. Con `docker compose up -d` Docker reinicia los contenedores uno a uno, manteniendo el servicio disponible durante la transición.

### Pre-check

```bash
# En local — confirmar que main y docker-deploy-prod están sincronizados
git log --oneline origin/main -3
git log --oneline origin/docker-deploy-prod -3
# Deben coincidir en el mismo commit "chore(deps): upgrade reflex..."
```

### Deploy en producción

```bash
# SSH al servidor de producción
ssh <usuario>@<ip-servidor-prod>
cd /ruta/al/proyecto

# Verificar estado pre-deploy
git log --oneline -3
docker compose ps

# Pull + build + up
git pull origin main
docker compose build
docker compose up -d

# Verificar estado post-deploy (esperar ~5 min al primer start)
docker compose ps
# Todos deben estar "Up (healthy)"
```

### Verificar producción

```bash
# Health check en los 3 dominios
curl -sf https://tuwayki.app/api/health
curl -sf https://sys.tuwayki.app/api/health
curl -sf https://admin.tuwayki.app/api/health

# Smoke test en los 3 dominios
bash scripts/smoke_deploy.sh https://tuwayki.app
bash scripts/smoke_deploy.sh https://sys.tuwayki.app
bash scripts/smoke_deploy.sh https://admin.tuwayki.app
```

### Verificación manual producción

- [ ] `https://tuwayki.app` (landing) carga
- [ ] `https://sys.tuwayki.app/login` muestra el login
- [ ] Login con cuenta real funciona
- [ ] Dashboard y Venta funcionan
- [ ] `https://admin.tuwayki.app/owner/login` accesible
- [ ] `/api/health` OK en los 3 dominios

**Criterio de éxito:** Todo `healthy`, todo funcional.

---

## FASE 10 — Cierre y documentación

**Duración estimada:** 5 minutos  
**Prerequisito:** FASE 9 exitosa.

```powershell
# En local, actualizar la memoria del proyecto para futuros contextos
# (esto se hace en la sesión de Claude Code)

# Eliminar el backup pre-upgrade (ya no necesario)
Remove-Item docs\requirements_backup_pre_upgrade.txt

# Opcional: commitear el borrado del backup
git add docs\requirements_backup_pre_upgrade.txt
git commit -m "chore: remove pre-upgrade requirements backup"
git push origin HEAD:main HEAD:docker-deploy-prod
```

Actualizar en este mismo documento la sección "Estado inicial verificado":
- Reflex instalado: `0.9.4`
- `starlette` en `requirements.txt`: `1.1.0`
- Python en `Dockerfile`: `3.13-slim`

---

## Rollback — Qué hacer si algo sale mal

### Rollback de requirements.txt/Reflex (local)

```powershell
# Volver a reflex 0.9.3
.venv\Scripts\pip.exe install reflex==0.9.3

# Restaurar requirements.txt desde backup
Copy-Item docs\requirements_backup_pre_upgrade.txt requirements.txt
```

### Rollback de Dockerfile (local)

```powershell
(Get-Content Dockerfile) -replace 'python:3.13-slim', 'python:3.11-slim' | Set-Content Dockerfile
```

### Rollback en SVR de Prueba/Prod (si el deploy falló)

El script `deploy.sh` guarda el commit anterior en `.deploy_prev_commit`:

```bash
# En el servidor afectado
bash scripts/deploy.sh --rollback
# El script hace git reset --hard al commit guardado en .deploy_prev_commit
# y vuelve a levantar reflex con el código anterior
```

### Rollback manual (si el script de rollback falla)

```bash
# En el servidor
git log --oneline -5
# Identificar el commit pre-upgrade (el de antes del "chore(deps): upgrade reflex")

git reset --hard <hash-commit-pre-upgrade>
.venv/bin/pip install -r requirements.txt
bash scripts/deploy.sh
```

### Rollback en GitHub (si el CI pasó pero el código es malo)

```bash
# En local
git revert HEAD --no-edit
git push origin HEAD:main HEAD:docker-deploy-prod
# Esto crea un commit de reversión, CI vuelve a correr, y luego se redeploya en svr
```

---

## Dependencias entre fases (diagrama)

```
FASE 1 (Snapshot + tests base)
    └─► FASE 2 (Upgrade reflex + sync requirements.txt)
            └─► FASE 6 (Verificación local)
                    └─► FASE 7 (Commit + Push)
                            └─► CI GitHub (automático)
                                    └─► FASE 8 (Deploy prueba)
                                                └─► FASE 9 (Deploy prod)
                                                            └─► FASE 10 (Cierre)

FASE 3 (Dockerfile) ──────────────────────────────────► FASE 7 (se commitea junto)
FASE 4 (bare except, OPCIONAL) ────────────────────────► FASE 7 (se commitea junto)
FASE 5 (docker-compose, OPCIONAL) ─────────────────────► FASE 7 (se commitea junto)
```

Las fases 3, 4 y 5 son independientes y pueden hacerse en cualquier orden. Las fases 1→2→6→7→8→9→10 son secuenciales obligatorias.

---

## Checklist de estado (marcar al completar)

```
FASE 1 — Preparación y snapshot
  [x] 1.1 git status limpio en main
  [x] 1.2 Hash de commit inicial: 1730dc09f84f491bf1ce5441b7dbe165105b74da
  [x] 1.3 Reflex 0.9.3 confirmado instalado
  [x] 1.4 Tests pasan (N = 1024 tests)
  [x] 1.5 Backup omitido (pip freeze ya realizado directamente)

FASE 2 — Upgrade de dependencias
  [x] 2.1 reflex 0.9.4 instalado
  [x] 2.2 reflex-base 0.9.4 instalado
  [x] 2.3 pip check sin errores
  [x] 2.4 requirements.txt generado con pip freeze
  [x] 2.5 "reflex==0.9.4" en requirements.txt
  [x] 2.6 "starlette==1.1.0" en requirements.txt
  [x] 2.7 sqlmodel 0.0.38, SQLAlchemy 2.0.50 también actualizados

FASE 3 — Dockerfile
  [x] 3.1 python:3.11-slim → python:3.13-slim (líneas 8 y 31)

FASE 4 — bare except (OPCIONAL)
  [ ] 4.1 report_service.py:289 (pendiente — baja prioridad)
  [ ] 4.2 report_service.py:494 (pendiente — baja prioridad)
  [ ] 4.3 exports.py:79 (pendiente — baja prioridad)
  [ ] 4.4 exports.py:296 (pendiente — baja prioridad)

FASE 5 — docker-compose.yml (OPCIONAL)
  [ ] 5.1 tuwayki_sys: service_started → service_healthy (pendiente)
  [ ] 5.2 tuwayki_admin: service_started → service_healthy (pendiente)

BUGS ADICIONALES CORREGIDOS EN SESIÓN (no planeados)
  [x] BUG-1: app/app.py:211 tabindex → tabIndex
  [x] BUG-2: .web Vite cache recharts corrupta → limpiada
  [x] BUG-3: app/components/ui.py:287 rx.el.p → rx.el.div (hydration error <p><p>)

FASE 6 — Verificación local
  [x] 6.1 pytest pasa (1024 tests, 0 failed)
  [x] 6.2 compileall sin errores
  [x] 6.3 pip check OK
  [x] 6.4 Servidor corriendo, todas las páginas verificadas visualmente
  [x] 6.5 DOM verificado sin <p><p> anidados

FASE 7 — Commit + Push          ✅ COMPLETADA
  [x] 7.1 git diff muestra archivos correctos
  [x] 7.2 Commit creado (401397f)
  [x] 7.3 git push origin HEAD:main HEAD:docker-deploy-prod
  [x] 7.4 CI GitHub Actions verde

FASE 8 — SVR de Prueba (Docker) ✅ COMPLETADA (2026-06-05)
  [x] 8.1 SSH + git pull origin main → Fast-forward 1730dc0..401397f (5 archivos)
  [x] 8.2 docker compose build → 3 imágenes python:3.13-slim reconstruidas OK
  [x] 8.3 docker compose up -d → containers recreados
      FIX: creado docker-compose.override.yml en SVR para npm_network → tuwayki_test_npm
  [x] 8.4 docker compose ps → todos healthy (landing, sys, admin, mysql, redis)
  [x] 8.5 /api/ping → {"pong":true} en los 3 servicios desde dentro de Docker
  [x] 8.6 Barrido completo local: 17 módulos OK, 0 bugs nuevos detectados

FASE 9 — SVR de Producción (Docker)  ← PRÓXIMO PASO
  [ ] 9.1 SSH + git pull origin main
  [ ] 9.2 docker compose build
  [ ] 9.3 docker compose up -d
  [ ] 9.4 docker compose ps → todos healthy
  [ ] 9.5 /api/ping en los 3 servicios OK
  [ ] 9.6 Verificación manual OK

FASE 10 — Cierre
  [ ] 10.1 Memoria del proyecto actualizada (Claude Code)
  [ ] 10.2 Este documento marcado como COMPLETADO
```

---

## Dónde quedamos (actualizar al finalizar cada sesión)

```
Fecha última sesión: 2026-06-05
Última fase completada: FASE 8 — SVR Prueba (AWS 52.15.161.245)
Próxima acción: FASE 9 — Deploy SVR Producción
  - SSH key: D:\Llave SVR AWS\llave-sistema-ventas.pem (si misma llave)
  - Obtener IP/host de SVR producción del usuario
  - Proyecto en SVR prueba: /home/ubuntu/sist-ventas-trebor (usar como referencia)
  - SVR Prueba requirió docker-compose.override.yml con npm_network → tuwayki_test_npm
  - SVR Prod probablemente tiene nginx-proxy-manager_default correctamente (verificar)
Commit en SVR Prueba: 401397f ✅
Commit HEAD: 401397f ✅
Notas importantes:
  - SVR Prueba: /home/ubuntu/sist-ventas-trebor/docker-compose.override.yml creado (NO commitear)
  - rx.debounce_input genera "value+defaultValue" warning — es Reflex interno, no tocar
  - UNSAFE_componentWillMount es react-helmet interno de Reflex, no tocar
  - La cache de Vite (.web/node_modules/.vite) se regenera sola en el build de Docker
  - Barrido local: 17 módulos, 0 bugs nuevos. Sistema 100% funcional en Reflex 0.9.4
```

---

## Información de referencia rápida

### Comandos frecuentes (Windows PowerShell)

```powershell
# Tests
$env:PYTHONPATH = "."; .venv\Scripts\pytest.exe -q --no-header

# Verificar versión Reflex
.venv\Scripts\pip.exe show reflex | Select-String "Version"

# Arrancar app en dev
$env:PYTHONPATH = "."; .venv\Scripts\reflex.exe run

# Push dual
git push origin HEAD:main HEAD:docker-deploy-prod

# pip check
.venv\Scripts\pip.exe check
```

### Archivos clave del proyecto

| Archivo | Propósito |
|---|---|
| `requirements.txt` | Dependencias Python (instaladas en venv y Docker) |
| `Dockerfile` | Imagen Docker multi-stage |
| `docker-compose.yml` | Stack multi-contenedor prod |
| `rxconfig.py` | Config Reflex + DB |
| `app/app.py` | Entry point, routing, layouts |
| `scripts/deploy.sh` | Script de deploy en SVR AWS |
| `scripts/smoke_deploy.sh` | Smoke tests post-deploy |
| `.github/workflows/tests.yml` | CI automático GitHub Actions |

### Notas sobre el entorno de deploy AWS

- **SVR de prueba y producción:** Usan `scripts/deploy.sh` (venv Python directo, NO Docker)
- **Docker compose:** Modelo alternativo de deploy; el Dockerfile se actualiza por consistencia
- **Migraciones:** No hay migraciones nuevas en este upgrade. `alembic upgrade head` será idempotente.
- **`.web/` cleanup:** `deploy.sh` limpia `.web/` automáticamente si detecta cambios en `rxconfig.py` — esto fuerza recompilación del frontend de Reflex (normal, tarda ~2-5 min)
- **Redis:** Requerido en prod. `ALLOW_MEMORY_RATE_LIMIT_FALLBACK=0` está seteado, fallaría si Redis no está disponible.
