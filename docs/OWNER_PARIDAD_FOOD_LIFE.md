# Owner Panel — Paridad SHOP → FOOD → LIFE

Objetivo: que el Owner Panel (`Sistema-de-Ventas`, servicio `tuwayki_admin`) ofrezca
para **TUWAYKIFOOD** y **TUWAYKILIFE** las mismas capacidades de gestión que hoy
tiene **TUWAYKISHOP**, **cada una adaptada a su propio software** (los planes,
módulos, usuarios y facturación de cada producto son distintos).

## Arquitectura (clave)

- **SHOP** vive en la **misma base** que el Owner Panel → el panel opera directo.
- **FOOD** (`Sistema-para-Food`, DB `food_db`) y **LIFE** (`Sistema-Gestion-Clinica`)
  son **apps/bases separadas**. El panel les habla por HTTP con
  `app/services/food_owner_client.py` y `life_owner_client.py`, autenticando con
  el header `X-Admin-Secret`.
- Regla de oro: **el panel no debe hardcodear los planes/módulos de cada producto**.
  Cada app expone su catálogo por su owner API; el panel lo renderiza por pestaña.

## Estado actual (relevado en código)

Acciones ricas gateadas a SHOP en `app/pages/owner/_companies_section.py`
(`rx.cond(owner_active_product_tab == "ventas", ...)`). FOOD/LIFE reciben fragment vacío.

| Capacidad | SHOP | FOOD | LIFE | Backend FOOD/LIFE |
|---|---|---|---|---|
| Cambiar Estado (activar/suspender) | ✅ | ✅ | ✅ | ya existe |
| Extender Prueba | ✅ | ✅ | ✅ | ya existe |
| Renovar / Planes | ✅ | ✅ (Fase 2) | ✅ (Fase 2) | listo |
| Resetear Contraseña | ✅ | ✅ | ✅ | listo (Fase 1) |
| Listar Usuarios (para reset) | ✅ | ✅ (el dueño) | ✅ (multi-usuario) | listo (Fase 1) |
| Ajustar Límites + Módulos | ✅ | ❌ | ❌ | falta (definir módulos por producto) |
| Billing / Facturación | ✅ (Nubefact PE / AFIP AR) | ❌ en panel* | ❌ | falta (*FOOD ya tiene Nubefact propio) |
| Sucursales (gestión) | ✅ | ⚠️ solo conteo | ⚠️ | a definir |
| Sync Expirados | ✅ | ✅ | ✅ | ya existe |
| Auditoría de acciones | ✅ | ✅ (el panel audita) | ✅ | ya existe |

`food_owner_client` hoy: `list_companies`, `get_company_detail`, `activate`,
`suspend`, `extend_trial`, `set_plan`. **No** tiene `list_users` ni `reset_password`.

FOOD `app/api.py` (gateado por `X-Admin-Secret`) hoy: register/provision, list,
detail, activate, suspend, extend_trial, set_plan. Falta el resto.

Nota FOOD: "resetear contraseña" = la clave del **Panel del Dueño**
(`ConfigImpresora.admin_password_hash`), no un usuario multi-cuenta como SHOP.
Los cambios de esa clave ya quedan auditados (`cambio_credenciales_admin`).

## Patrón por capacidad (se repite para cada una)

1. **App producto** (FOOD y LIFE) → endpoint owner en `app/api.py` (auth `X-Admin-Secret`) + auditoría interna.
2. **Owner client** (`food_owner_client` / `life_owner_client`) → método que llama al endpoint.
3. **Owner state** (`owner_state.py`) → rutear el handler por `owner_active_product_tab`.
4. **Owner UI** (`_companies_section.py`) → des-gatear / renderizar la acción para food/life.
5. **Prueba** end-to-end por producto + registro en auditoría del panel.

## Plan por fases (propuesto)

- **Fase 1 — Resetear Contraseña (FOOD + LIFE). ✅ HECHA.**
  Endpoints reset + listar cuentas, client, ruteo del modal, botón des-gateado.
  FOOD: una cuenta de dueño (`ConfigImpresora`). LIFE: multi-usuario real
  (tabla `usuarios`, se elige la cuenta por `user_id`; se resetea con
  `User.set_password`). El panel guarda su propia auditoría; FOOD además audita
  internamente (`reset_password_owner`) y LIFE deja traza en el log.
- **Fase 2 — Renovar / Planes (FOOD + LIFE). ✅ HECHA.**
  - **Cambiar Plan** ya funcionaba por `set_plan`; se corrigió el desplegable del
    modal para LIFE (mostraba los planes de SHOP: professional/enterprise). FOOD y
    LIFE comparten catálogo real: `trial / standard / profesional`.
  - **Renovar Suscripción**: endpoint nuevo `POST /api/admin/companies/{id}/renew`
    en ambas apps + `renew_subscription(company_id, months)` en los clients. Mantiene
    el plan y extiende `plan_expires_at` desde `max(hoy, vencimiento actual)`
    (`months` × 30 días). Trial no se renueva por acá (409 → usar Cambiar Plan o
    Extender Prueba). El botón "Renovar Suscripción" quedó des-gateado para FOOD/LIFE.
  - Nota: el catálogo de planes hoy es **estático por producto** (definido en el
    código de cada app). Un endpoint dinámico `GET /api/admin/plans` queda diferido
    (los planes son idénticos entre FOOD y LIFE, no justifica aún el dinamismo).
- **Fase 3 — Ajustar Límites + Módulos.** Definir el catálogo de módulos de cada
  software (FOOD: mozos, caja, cocina, mostrador, delivery, reservas, inventario…;
  LIFE: los suyos) y exponerlo por owner API; UI de toggles por pestaña.
- **Fase 4 — Billing / Facturación por software.** Según país/integrador de cada
  producto (FOOD ya tiene su Nubefact integrador propio; ver si se centraliza o
  queda en cada app).
- **Fase 5 — Usuarios / Sucursales.** Gestión (no solo conteo) si aplica a cada producto.

Cada fase: se construye, se prueba en Docker local (rebuild + verificación en vivo)
y se despliega. Texto de producto en **español neutro**.

## Repos involucrados

- `D:\PROYECTOS\Sistema-de-Ventas` — Owner Panel (hub, UI + clients + state).
- `D:\PROYECTOS\Sistema-para-Food` — app FOOD (endpoints owner).
- `D:\PROYECTOS\Sistema-Gestion-Clinica` — app LIFE (endpoints owner).
