# Domain Split Runbook (tuwayki/sys/admin)

Objetivo final:

- `https://tuwayki.app/` -> Landing publica.
- `https://sys.tuwayki.app/` -> Sistema de Ventas.
- `https://admin.tuwayki.app/login` -> Gestion de Plataforma interna.

## 1. Pre-cambio (obligatorio)

1. Crear rama de release:
   - `git checkout -b release/domain-split`
2. Backup de DB:
   - `python scripts/backup_db.py`
3. Snapshot del servidor (EBS/VM).
4. Definir ventana de cambio (30-60 min) con rollback listo.

## 2. Preparar 3 superficies con el mismo codigo

Archivo de servicio:

- `ops/systemd/tuwayki-surface@.service`

Copiar en servidor:

- `/etc/systemd/system/tuwayki-surface@.service`

Crear env por instancia:

- `/etc/tuwayki/landing.env`
- `/etc/tuwayki/sys.env`
- `/etc/tuwayki/admin.env`

Contenido sugerido:

```env
# /etc/tuwayki/landing.env
APP_SURFACE=landing
REFLEX_PORT=3100
PUBLIC_SITE_URL=https://tuwayki.app
PUBLIC_APP_URL=https://sys.tuwayki.app
PUBLIC_OWNER_URL=https://admin.tuwayki.app
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=3306
DB_NAME=...
AUTH_SECRET_KEY=...
```

```env
# /etc/tuwayki/sys.env
APP_SURFACE=app
REFLEX_PORT=3200
PUBLIC_SITE_URL=https://tuwayki.app
PUBLIC_APP_URL=https://sys.tuwayki.app
PUBLIC_OWNER_URL=https://admin.tuwayki.app
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=3306
DB_NAME=...
AUTH_SECRET_KEY=...
```

```env
# /etc/tuwayki/admin.env
APP_SURFACE=owner
REFLEX_PORT=3300
PUBLIC_SITE_URL=https://tuwayki.app
PUBLIC_APP_URL=https://sys.tuwayki.app
PUBLIC_OWNER_URL=https://admin.tuwayki.app
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=3306
DB_NAME=...
AUTH_SECRET_KEY=...
```

Levantar servicios:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tuwayki-surface@landing
sudo systemctl enable --now tuwayki-surface@sys
sudo systemctl enable --now tuwayki-surface@admin
```

Validar puertos locales:

```bash
ss -ltnp | grep -E "3100|3200|3300"
curl -I http://127.0.0.1:3100/
curl -I http://127.0.0.1:3200/
curl -I http://127.0.0.1:3300/login
```

## 3. DNS y TLS

Crear/validar registros:

1. `tuwayki.app` -> A/ALIAS al LB/instancia.
2. `www.tuwayki.app` -> CNAME a `tuwayki.app`.
3. `sys.tuwayki.app` -> CNAME/ALIAS al LB/instancia.
4. `admin.tuwayki.app` -> CNAME/ALIAS al LB/instancia.

Certificado TLS SAN:

- `tuwayki.app`
- `www.tuwayki.app`
- `sys.tuwayki.app`
- `admin.tuwayki.app`

## 4. Nginx/OpenResty host-based routing

Archivo:

- `ops/nginx/tuwayki-domain-split.conf`

Instalar en:

- `/etc/nginx/conf.d/tuwayki-domain-split.conf`

Activar:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 5. Validacion inmediata (sin downtime)

Ejecutar:

```bash
curl -I https://tuwayki.app/
curl -I https://tuwayki.app/robots.txt
curl -I https://tuwayki.app/sitemap.xml
curl -I https://www.tuwayki.app/
curl -I https://sys.tuwayki.app/
curl -I https://admin.tuwayki.app/login
curl -I https://tuwayki.app/home
curl -I https://tuwayki.app/owner/login
```

Esperado:

1. `https://tuwayki.app/` devuelve landing.
2. `www` redirige a `https://tuwayki.app/*`.
3. `https://sys.tuwayki.app/` devuelve app/login.
4. `https://admin.tuwayki.app/login` devuelve owner login.
5. `https://tuwayki.app/home` redirige a `https://tuwayki.app/`.
6. `https://tuwayki.app/owner/login` redirige a `https://admin.tuwayki.app/login`.

Validar flujo de navegador:

1. Landing -> boton Ingresar -> `sys`.
2. Login en `sys`.
3. Volver atras -> landing sin pantalla vacia.

## 6. Compatibilidad 30 dias

Mantener redirecciones legacy activas por 30 dias:

1. `/home` -> landing root.
2. `/owner/login` -> admin login.
3. rutas app legacy en apex -> `sys`.

Despues de 30 dias, revisar logs 404/301 y retirar reglas que ya no se usen.

## 7. Seguridad de admin (critico)

Minimo recomendado:

1. `X-Robots-Tag: noindex, nofollow` (ya aplicado en Nginx).
2. Allowlist IP o VPN para `admin.tuwayki.app`.
3. Rate limiting y monitoreo de intentos de login.
4. MFA para cuentas owner.

## 8. Rollback (objetivo 10-15 min)

Si hay incidente:

1. Restaurar config Nginx previa:
   - `sudo cp /etc/nginx/conf.d/tuwayki-domain-split.conf.bak /etc/nginx/conf.d/tuwayki-domain-split.conf`
   - `sudo nginx -t && sudo systemctl reload nginx`
2. Volver a servicio unico anterior.
3. Mantener DNS sin cambios destructivos.
4. Revisar logs y reintentar en nueva ventana.

