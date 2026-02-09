# 🔒 Guía de Deployment Seguro - Sistema de Ventas

Esta guía documenta las configuraciones de seguridad recomendadas para producción.

## Índice

1. [Variables de Entorno](#1-variables-de-entorno)
2. [Headers de Seguridad HTTP](#2-headers-de-seguridad-http)
3. [Configuración de Base de Datos](#3-configuración-de-base-de-datos)
4. [Rate Limiting](#4-rate-limiting)
5. [SSL/TLS](#5-ssltls)
6. [Monitoreo y Logs](#6-monitoreo-y-logs)
7. [Checklist de Producción](#7-checklist-de-producción)

---

## 1. Variables de Entorno

### Archivo `.env` (NUNCA SUBIR A GIT)

```env
# === OBLIGATORIAS ===
AUTH_SECRET_KEY=<clave-secreta-minimo-32-caracteres>
DB_HOST=localhost
DB_PORT=3306
DB_USER=app_user
DB_PASSWORD=<contraseña-segura>
DB_NAME=ventas_db
REDIS_URL=redis://localhost:6379
ALLOW_MEMORY_RATE_LIMIT_FALLBACK=0

# === OPCIONALES ===
ENV=prod
LOG_LEVEL=WARNING
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
```

### Generar AUTH_SECRET_KEY Segura

```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

⚠️ **IMPORTANTE**: La SECRET_KEY debe:
- Tener mínimo 32 caracteres
- Ser única por entorno (dev, staging, prod)
- Rotarse periódicamente (cada 6-12 meses)
- Invalidar tokens existentes al rotar

---

## 2. Headers de Seguridad HTTP

### Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name tudominio.com;

    # SSL Configuration (ver sección 5)
    ssl_certificate /etc/letsencrypt/live/tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tudominio.com/privkey.pem;

    # ===== HEADERS DE SEGURIDAD =====
    
    # Prevenir clickjacking
    add_header X-Frame-Options "SAMEORIGIN" always;
    
    # Prevenir MIME-type sniffing
    add_header X-Content-Type-Options "nosniff" always;
    
    # Protección XSS (navegadores modernos)
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Content Security Policy (ajustar según necesidades)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' wss://tudominio.com;" always;
    
    # HTTP Strict Transport Security (HSTS)
    # Solo activar cuando SSL esté funcionando correctamente
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Política de referrer
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Permisos de APIs del navegador
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # ===== PROXY A REFLEX =====
    
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts para WebSocket
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Bloquear acceso a archivos sensibles
    location ~ /\. {
        deny all;
    }
    
    location ~ \.(env|git|gitignore)$ {
        deny all;
    }
}

# Redirigir HTTP a HTTPS
server {
    listen 80;
    server_name tudominio.com;
    return 301 https://$server_name$request_uri;
}
```

### Caddy (Alternativa más simple)

```caddyfile
tudominio.com {
    # SSL automático con Let's Encrypt
    
    # Headers de seguridad
    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' wss://tudominio.com;"
    }
    
    # Proxy a Reflex
    reverse_proxy localhost:3000 {
        # Soporte WebSocket
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

---

## 3. Configuración de Base de Datos

### Usuario de Base de Datos (Principio de Menor Privilegio)

```sql
-- Crear usuario específico para la aplicación
CREATE USER 'ventas_app'@'localhost' IDENTIFIED BY 'contraseña_segura';

-- Solo permisos necesarios (NO dar GRANT OPTION ni DROP)
GRANT SELECT, INSERT, UPDATE, DELETE ON ventas_db.* TO 'ventas_app'@'localhost';

-- Usuario separado para migraciones (uso ocasional)
CREATE USER 'ventas_migrate'@'localhost' IDENTIFIED BY 'otra_contraseña_segura';
GRANT ALL PRIVILEGES ON ventas_db.* TO 'ventas_migrate'@'localhost';

FLUSH PRIVILEGES;
```

### Pool de Conexiones (SQLAlchemy)

```python
# rxconfig.py - Configuración recomendada para producción
import reflex as rx

config = rx.Config(
    app_name="app",
    db_url="mysql+aiomysql://ventas_app:password@localhost:3306/ventas_db",
    # Pool de conexiones
    sqlalchemy_pool_size=5,          # Conexiones activas
    sqlalchemy_max_overflow=10,      # Conexiones adicionales bajo carga
    sqlalchemy_pool_timeout=30,      # Timeout para obtener conexión
    sqlalchemy_pool_recycle=1800,    # Reciclar conexiones cada 30 min
)
```

---

## 4. Rate Limiting

El sistema ya implementa rate limiting. En producción, usar Redis:

```python
# .env
REDIS_URL=redis://localhost:6379
ALLOW_MEMORY_RATE_LIMIT_FALLBACK=0  # En prod, deshabilitar fallback local

# El sistema detecta automáticamente y usa RedisRateLimitBackend
```

### Configuración Redis

```bash
# /etc/redis/redis.conf
maxmemory 100mb
maxmemory-policy allkeys-lru
```

### Parámetros Actuales (app/utils/rate_limit.py)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `max_attempts` | 5 | Intentos de login permitidos |
| `window_seconds` | 900 | Ventana de 15 minutos |
| `lockout_seconds` | 900 | Bloqueo de 15 minutos |

---

## 5. SSL/TLS

### Certificado Let's Encrypt (Certbot)

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d tudominio.com -d www.tudominio.com

# Renovación automática (cron)
0 0,12 * * * certbot renew --quiet
```

### Configuración SSL Nginx (A+ en SSL Labs)

```nginx
# /etc/nginx/snippets/ssl-params.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
```

---

## 6. Monitoreo y Logs

### Estructura de Logs

```
logs/
├── app.log           # Logs de aplicación
├── access.log        # Logs de acceso HTTP
├── error.log         # Errores de aplicación
└── security.log      # Eventos de seguridad (login, rate limit)
```

### Logrotate

```bash
# /etc/logrotate.d/ventas
/var/log/ventas/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
```

### Alertas Recomendadas

- Múltiples intentos fallidos de login (rate limiting)
- Errores de base de datos
- Uso de CPU/memoria alto
- Certificado SSL próximo a expirar

---

## 7. Checklist de Producción

### Antes del Deploy

- [ ] Variables de entorno configuradas
- [ ] AUTH_SECRET_KEY generada (mínimo 32 chars)
- [ ] ENV=prod
- [ ] Base de datos con usuario de privilegios mínimos
- [ ] Backups automatizados configurados

### Infraestructura

- [ ] Firewall configurado (solo puertos 80, 443, 22)
- [ ] SSL/TLS habilitado con Let's Encrypt
- [ ] Headers de seguridad configurados
- [ ] Rate limiting con Redis
- [ ] Logs configurados con rotación

### Verificación Post-Deploy

- [ ] Probar login y logout
- [ ] Verificar headers con: `curl -I https://tudominio.com`
- [ ] Probar rate limiting (5 intentos fallidos)
- [ ] Verificar SSL: https://www.ssllabs.com/ssltest/
- [ ] Verificar headers: https://securityheaders.com/
- [ ] Probar backup y restore

### Mantenimiento Continuo

- [ ] Actualizar dependencias mensualmente
- [ ] Rotar SECRET_KEY cada 6-12 meses
- [ ] Revisar logs de seguridad semanalmente
- [ ] Renovar certificado SSL (automático con certbot)
- [ ] Probar recuperación de backups trimestralmente

---

## Comandos Útiles

```bash
# Verificar configuración nginx
sudo nginx -t

# Recargar nginx
sudo systemctl reload nginx

# Ver logs en tiempo real
tail -f /var/log/ventas/app.log

# Verificar certificado SSL
openssl s_client -connect tudominio.com:443 -servername tudominio.com

# Test de headers de seguridad
curl -I -s https://tudominio.com | grep -E "^(X-|Content-Security|Strict|Referrer|Permissions)"

# Verificar conexiones a base de datos
mysql -u root -p -e "SHOW PROCESSLIST;"

# Estado de Redis
redis-cli INFO | grep connected_clients
```

---

## Contacto de Emergencia

En caso de incidente de seguridad:
1. Documentar el incidente
2. Rotar SECRET_KEY inmediatamente
3. Revisar logs de acceso
4. Invalidar sesiones activas (incrementar token_version de usuarios)
5. Notificar a usuarios afectados si aplica

---

*Última actualización: 2025*
