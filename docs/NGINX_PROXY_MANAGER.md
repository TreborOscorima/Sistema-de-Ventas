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

## 1. Proxy Host — Landing (tuwayki.app)

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

**Advanced — Custom Nginx Configuration** (opcional, para cabeceras SEO/seguridad):

```nginx
# Cabeceras recomendadas para landing pública
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
```

Guardar y aplicar.

---

## 2. Proxy Host — Sistema de Ventas (sys.tuwayki.app)

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

**Advanced — Custom Nginx Configuration** (recomendado):

```nginx
# No indexar en buscadores (área de aplicación)
add_header X-Robots-Tag "noindex, nofollow" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
```

Guardar y aplicar.

---

## 3. Proxy Host — Admin / Gestión de plataforma (admin.tuwayki.app)

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

**Advanced — Custom Nginx Configuration** (recomendado):

```nginx
# No indexar (área interna)
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
