# Nginx Proxy Manager (NPM) — tuwayki.app

Instrucciones para exponer las tres superficies de la aplicación vía HTTPS con NPM.

---

## Checklist antes de entrar a producción

Antes de ejecutar `docker compose up -d` por primera vez:

1. **Crear `.env`** (obligatorio; el compose usa `env_file: .env`):
   ```bash
   cp .env.example .env
   ```
   Editar `.env` y definir al menos:
   - `DB_PASSWORD` — contraseña de MySQL (y de usuario `app`).
   - `AUTH_SECRET_KEY` — clave secreta para sesiones (mín. 32 caracteres; ej: `python -c "import secrets; print(secrets.token_urlsafe(32))"`).

2. **Crear la red de NPM** (para que los contenedores sean alcanzables por NPM):
   ```bash
   docker network create nginx-proxy-manager_default
   ```
   Si tu NPM usa otra red, comprobar con `docker network ls` y poner ese nombre en `docker-compose.yml` en `networks.npm_network.name`.

3. **Build y arranque:**
   ```bash
   docker compose build && docker compose up -d
   ```

4. **Configurar los Proxy Hosts** en la UI de Nginx Proxy Manager según las secciones siguientes.

**Comprobar que el stack está en marcha:**
```bash
docker compose ps
```
Los cinco contenedores (mysql, redis, tuwayki_landing, tuwayki_sys, tuwayki_admin) deben estar `Up` y (salvo los app) `healthy`. Si alguno reinicia, revisar logs: `docker compose logs -f tuwayki_landing` (o el servicio que falle).

**Si los app muestran "MySQL no disponible después de 120s":** Los contenedores de la app deben estar en la misma red que MySQL. Verificar:
```bash
# Nombre de la red interna (sustituir sist-ventas-trebor por tu nombre de proyecto si aplica)
docker network ls | grep internal

# Que mysql y tuwayki_landing estén en esa red
docker network inspect sist-ventas-trebor_internal_net
```
En `Containers` deben aparecer `sistema_ventas_mysql`, `tuwayki_landing`, `tuwayki_sys` y `tuwayki_admin`. Si no, revisar que en `docker-compose.yml` los servicios app tengan `networks: - internal_net` (y `- npm_network`). Tras cambiar el entrypoint (sleep inicial), reconstruir: `docker compose build tuwayki_landing tuwayki_sys tuwayki_admin && docker compose up -d`.

---

## Red y requisitos

Los contenedores del stack deben estar en la misma red que NPM. En `docker-compose.yml` se usa la red externa `nginx-proxy-manager_default`. Si tu NPM usa otra red, cambia en el compose:

```yaml
npm_network:
  external: true
  name: <nombre_de_la_red_de_tu_npm>
```

Para ver el nombre de la red de NPM: `docker network ls` y localizar la red del contenedor de Nginx Proxy Manager.

---

## Si el landing (o sys/admin) no se muestra

1. **Logs del contenedor sin “colgar”** (las últimas líneas):
   ```bash
   docker logs --tail 80 tuwayki_landing
   ```
   Debe terminar con Reflex en marcha (ej. “Compiling … 100%” o “Listening”). Si ves errores o reinicios, ese es el problema.

2. **Que el contenedor esté en la red de NPM:**
   ```bash
   docker network inspect nginx-proxy-manager_default
   ```
   En `Containers` debe aparecer **tuwayki_landing** (y tuwayki_sys, tuwayki_admin). Si no está, el compose debe tener `networks: - npm_network` para ese servicio y la red debe existir.

3. **Comprobar que NPM llega al contenedor** (desde el host):
   ```bash
   docker run --rm --network nginx-proxy-manager_default curlimages/curl:latest curl -s -o /dev/null -w "%{http_code}" http://tuwayki_landing:3000/
   ```
   Debe devolver **200** (o 302 si redirige). Si falla o timeout, el problema es red/contenedor, no NPM.

4. **Revisar el Proxy Host en NPM:**
   - **Domain Names:** exactamente `tuwayki.app` (sin www para el host del landing).
   - **Forward Hostname:** exactamente `tuwayki_landing` (mismo nombre que el contenedor; distinto a tuwayki_sys / tuwayki_admin).
   - **Forward Port:** `3000`.
   - **Scheme:** `http` (NPM termina SSL y habla HTTP con el contenedor).
   - **Websockets Support:** ON.

5. **DNS:** En tu PC o móvil, `tuwayki.app` debe resolver a la IP del servidor donde corre NPM (la misma que tiene los contenedores). Comprueba con `ping tuwayki.app` o `nslookup tuwayki.app`.

6. **Certificado SSL:** Si usas “Request a new certificate”, el primer acceso puede tardar hasta que Let’s Encrypt emita el cert. Revisa en NPM que el proxy esté en verde (certificado válido) y sin errores en el log del proxy.

---

## 1. Proxy Host — Landing (tuwayki.app)

Si el landing usa Reflex con backend (WebSocket), las rutas `/_event`, `/_upload`, `/ping` deben ir al puerto **8000** de `tuwayki_landing`. Si solo sirve estático, no hace falta el bloque `location`.

| Campo | Valor |
|-------|--------|
| **Domain Names** | `tuwayki.app` |
| **Scheme** | `http` |
| **Forward Hostname** | `tuwayki_landing` |
| **Forward Port** | `3000` |
| **Cache Assets** | Opcional |
| **Block Common Exploits** | Recomendado ✅ |
| **Websockets Support** | **ON** ✅ |

**SSL:**
- **SSL Certificate**: Request a new SSL Certificate (Let's Encrypt).
- **Force SSL**: Activado.
- **HTTP/2 Support**: Activado.
- **HSTS Enabled**: Activado (opcional pero recomendado).

**Advanced — Custom Nginx Configuration** (si el landing usa backend/WebSocket, incluir los `location`; si no, solo las cabeceras):

```nginx
location /_event {
    proxy_pass http://tuwayki_landing:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
    proxy_buffering off;
    proxy_cache off;
}
location /_upload {
    proxy_pass http://tuwayki_landing:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
    proxy_buffering off;
}
location /ping {
    proxy_pass http://tuwayki_landing:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
```

Guardar y aplicar.

---

## 2. Proxy Host — Sistema de Ventas (sys.tuwayki.app)

El frontend (HTML/JS) se sirve desde el puerto **3000**; el backend de Reflex (WebSocket `/_event`, `/_upload`, `/ping`) corre en el puerto **8000**. NPM debe enviar esas rutas al 8000 con soporte WebSocket; si no, verás "Cannot connect to server: timeout" en `wss://sys.tuwayki.app/_event`.

| Campo | Valor |
|-------|--------|
| **Domain Names** | `sys.tuwayki.app` |
| **Scheme** | `http` |
| **Forward Hostname** | `tuwayki_sys` |
| **Forward Port** | `3000` |
| **Cache Assets** | Opcional |
| **Block Common Exploits** | Recomendado ✅ |
| **Websockets Support** | **ON** ✅ |

**SSL:**
- **SSL Certificate**: Request a new SSL Certificate (Let's Encrypt).
- **Force SSL**: Activado.
- **HTTP/2 Support**: Activado.
- **HSTS Enabled**: Activado.

**Advanced — Custom Nginx Configuration** (obligatorio para que el WebSocket y el backend funcionen):

```nginx
# Backend Reflex (puerto 8000): WebSocket /_event y rutas de API
location /_event {
    proxy_pass http://tuwayki_sys:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
    proxy_buffering off;
    proxy_cache off;
}
location /_upload {
    proxy_pass http://tuwayki_sys:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
    proxy_buffering off;
}
location /ping {
    proxy_pass http://tuwayki_sys:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Cabeceras recomendadas
add_header X-Robots-Tag "noindex, nofollow" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
```

Guardar y aplicar.

---

## 3. Proxy Host — Admin / Gestión de plataforma (admin.tuwayki.app)

Igual que sys: el backend (/_event, /_upload, /ping) debe ir al puerto **8000** de `tuwayki_admin`.

| Campo | Valor |
|-------|--------|
| **Domain Names** | `admin.tuwayki.app` |
| **Scheme** | `http` |
| **Forward Hostname** | `tuwayki_admin` |
| **Forward Port** | `3000` |
| **Cache Assets** | Opcional |
| **Block Common Exploits** | Recomendado ✅ |
| **Websockets Support** | **ON** ✅ |

**SSL:**
- **SSL Certificate**: Request a new SSL Certificate (Let's Encrypt).
- **Force SSL**: Activado.
- **HTTP/2 Support**: Activado.
- **HSTS Enabled**: Activado.

**Advanced — Custom Nginx Configuration** (obligatorio para WebSocket/backend):

```nginx
location /_event {
    proxy_pass http://tuwayki_admin:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
    proxy_buffering off;
    proxy_cache off;
}
location /_upload {
    proxy_pass http://tuwayki_admin:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
    proxy_buffering off;
}
location /ping {
    proxy_pass http://tuwayki_admin:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
add_header X-Robots-Tag "noindex, nofollow" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
```

Guardar y aplicar.

---

## 4. Redirect — www.tuwayki.app → tuwayki.app

Redirigir `www` al dominio principal para evitar contenido duplicado.

| Campo | Valor |
|-------|--------|
| **Domain Names** | `www.tuwayki.app` |
| **Scheme** | `http` |
| **Forward Hostname** | `tuwayki_landing` |
| **Forward Port** | `3000` |

**SSL:** Request a new SSL Certificate (para que la redirección HTTPS funcione).

**Advanced — Custom Nginx Configuration** (obligatorio para el redirect):

```nginx
return 301 https://tuwayki.app$request_uri;
```

Con esto, toda petición a `https://www.tuwayki.app/...` responde con un 301 a `https://tuwayki.app/...`.

---

## Resumen de URLs

| URL | Contenedor | Uso |
|-----|------------|-----|
| https://tuwayki.app/ | tuwayki_landing | Landing pública |
| https://www.tuwayki.app/ | (redirect 301 → tuwayki.app) | Evitar duplicado |
| https://sys.tuwayki.app/ | tuwayki_sys | Sistema de Ventas |
| https://admin.tuwayki.app/login | tuwayki_admin | Gestión de plataforma (interna) |

---

## Comprobar que NPM ve los contenedores

En el servidor donde corre Docker:

```bash
# Red usada en este proyecto (por defecto)
docker network inspect nginx-proxy-manager_default
```

Deben aparecer los contenedores `tuwayki_landing`, `tuwayki_sys` y `tuwayki_admin`. Si NPM está en otra red, hay que añadirla al `docker-compose.yml` (o conectar los contenedores a esa red).

Si NPM está en otro host (no en el mismo Docker daemon), no podrás usar el hostname del contenedor. En ese caso tendrías que poner la IP del host y exponer el puerto 3000 de cada superficie en el host (por ejemplo con `ports: "3001:3000"`, `3002:3000"`, `3003:3000"`) y en NPM usar esa IP y el puerto correspondiente.
