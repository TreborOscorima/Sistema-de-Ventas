# Plan Comercial Web - TUWAYKIAPP

## Objetivo
Convertir visitas de internet en pruebas gratuitas de 15 dias y luego en clientes de pago.

## Arquitectura recomendada de dominios
- `www.tudominio.com` -> sitio comercial (landing, contenido, planes).
- `app.tudominio.com` -> aplicacion SaaS (login, registro, operacion).

## Embudo minimo viable
1. Trafico (SEO + anuncios + redes).
2. Landing de conversion.
3. Registro trial (`/registro`).
4. Activacion en primeras 48 horas.
5. Conversion a Standard/Professional.

## Ruta publica ya implementada
- Landing comercial en: `/sitio`
- CTA principal a trial: `/registro`
- Acceso al sistema: `/`

## Mensaje comercial recomendado
- Propuesta de valor:
  "Controla ventas, caja e inventario en una sola plataforma."
- Beneficios directos:
  - Menos errores de caja y stock.
  - Cobros mas rapidos (productos y servicios).
  - Reportes para decisiones diarias.
  - Multiempresa con roles por tenant.

## Piezas de contenido para marketing
1. Pagina principal (`/sitio`) con CTA repetido.
2. Pagina de precios (si se decide separar de la landing).
3. Casos por rubro:
   - tienda de barrio
   - negocio con reservas
   - operacion con sucursales
4. FAQ comercial y tecnico.
5. Politicas:
   - terminos y condiciones
   - privacidad
   - cookies

## Tracking minimo (obligatorio)
Instrumentar eventos:
- `view_landing`
- `click_trial_cta`
- `start_registration`
- `complete_registration`
- `activate_day_1`
- `activate_day_7`
- `start_checkout_plan`
- `purchase_plan`

### Configuracion productiva de tracking (GA4 + Meta Pixel)

Variables de entorno para habilitar tags en la landing (`/sitio`):
- `GA4_MEASUREMENT_ID=G-XXXXXXXXXX`
- `META_PIXEL_ID=123456789012345`

Comportamiento implementado:
- Si `GA4_MEASUREMENT_ID` existe: carga `gtag.js` y envía eventos custom.
- Si `META_PIXEL_ID` existe: carga `fbq` y envía `trackCustom`.
- Siempre conserva fallback local (`dataLayer` + `localStorage`) para depuración.

Eventos ya conectados en la landing:
- `view_landing` (1 vez por sesión)
- `click_trial_cta` (header, hero, FAQ, banner final y footer)

Validacion rapida:
1. Abrir `/sitio`.
2. En DevTools verificar `window.dataLayer` con `view_landing`.
3. Hacer click en CTA trial y confirmar `click_trial_cta`.
4. En producción validar en GA4 DebugView y Meta Test Events.

## KPIs de lanzamiento
- Conversion Landing -> Trial (%)
- Trial -> Activado 48h (%)
- Trial -> Pago (%)
- CAC (costo de adquisicion)
- MRR (ingreso recurrente mensual)

## Canales recomendados para iniciar
1. Google Ads (busqueda):
   - Keywords de alta intencion, ejemplo:
     - "sistema de ventas para tiendas"
     - "software punto de venta con inventario"
     - "sistema para reservas y cobros"
2. Meta Ads:
   - Videos cortos mostrando flujos reales (venta, reserva, cierre de caja).
3. Retargeting:
   - Visitantes que no completaron registro.

## Plan de 14 dias (ejecucion rapida)
1. Publicar landing y tracking.
2. Activar 2-3 campañas de busqueda.
3. Revisar eventos y embudo a diario.
4. Ajustar copy/CTA segun conversion.
5. Reforzar onboarding de trial para subir activacion.

## Antes de lanzar anuncios
- Definir dominio final y SSL.
- Activar correo transaccional para onboarding.
- Preparar WhatsApp comercial y guion de demo.
- Verificar que el registro funcione de punta a punta.
- Confirmar backup/restore y monitoreo basico.
