#!/usr/bin/env bash
# =============================================================================
# scripts/smoke_deploy.sh — Smoke test post-deploy para TUWAYKI
#
# Uso:
#   bash scripts/smoke_deploy.sh                                    # Local
#   bash scripts/smoke_deploy.sh http://3.19.234.12:8000            # Test server
#   bash scripts/smoke_deploy.sh https://tuwayki.app                # Producción
#   bash scripts/smoke_deploy.sh --domain-split                     # 3 superficies
#   bash scripts/smoke_deploy.sh http://3.19.234.12:8000 --backend-only  # Solo API
#
# Notas:
#   - Reflex sin nginx: backend en :8000, frontend en :3000
#   - Con nginx: todo pasa por :80/:443 (proxy a ambos puertos)
#   - El script auto-detecta la URL del frontend a partir de la del backend
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0
DOMAIN_SPLIT=false
BACKEND_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --domain-split)  DOMAIN_SPLIT=true ;;
        --backend-only)  BACKEND_ONLY=true ;;
        http*)           BASE_URL="$arg" ;;
    esac
done

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

# Auto-detectar URL del frontend (Reflex: backend=8000, frontend=3000)
# Con nginx (puertos 80/443) el frontend y backend comparten URL
if [[ "$BASE_URL" =~ :8000$ ]]; then
    FRONTEND_URL="${BASE_URL/:8000/:3000}"
else
    FRONTEND_URL="$BASE_URL"
fi

info()  { echo -e "${CYAN}[TEST]${NC}  $*"; }
pass()  { echo -e "${GREEN}[PASS]${NC}  $*"; PASS=$((PASS + 1)); }
fail_t(){ echo -e "${RED}[FAIL]${NC}  $*"; FAIL=$((FAIL + 1)); }
warn_t(){ echo -e "${YELLOW}[WARN]${NC}  $*"; WARN=$((WARN + 1)); }

check_url() {
    local url="$1"
    local expected_code="${2:-200}"
    local description="${3:-$url}"

    local code
    # No usar -f: curl -f falla con 4xx/5xx y corrompe la captura de %{http_code}
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null)"

    if [[ "$code" == "$expected_code" ]]; then
        pass "$description -> $code"
    elif [[ "$code" == "000" ]]; then
        fail_t "$description -> TIMEOUT/CONNECTION_REFUSED"
    else
        fail_t "$description -> $code (esperado: $expected_code)"
    fi
}

check_health() {
    local url="$1/api/health"
    local description="${2:-Health check}"

    local response
    response="$(curl -sf --max-time 10 "$url" 2>/dev/null || echo '')"

    if [[ -z "$response" ]]; then
        fail_t "$description -> sin respuesta"
        return
    fi

    local status
    status="$(echo "$response" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status",""))' 2>/dev/null || echo '')"

    if [[ "$status" == "ok" ]]; then
        pass "$description -> ok"
        echo "       $response"
    else
        fail_t "$description -> status='$status'"
    fi
}

check_redirect() {
    local url="$1"
    local expected_location="$2"
    local description="${3:-Redirect}"

    local headers
    headers="$(curl -sI --max-time 10 "$url" 2>/dev/null || echo '')"
    local code
    code="$(echo "$headers" | head -1 | awk '{print $2}')"
    local location
    location="$(echo "$headers" | grep -i '^location:' | awk '{print $2}' | tr -d '\r\n')"

    if [[ "$code" =~ ^30[12]$ ]] && [[ "$location" == *"$expected_location"* ]]; then
        pass "$description -> $code -> $location"
    else
        fail_t "$description -> code=$code location=$location (esperado: 30x -> $expected_location)"
    fi
}

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  TUWAYKI Smoke Test — $(date +%Y-%m-%d\ %H:%M:%S)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

if $DOMAIN_SPLIT; then
    # ─── Prueba de las 3 superficies separadas ───────────────────────────
    info "=== LANDING (tuwayki.app) ==="
    check_url "https://tuwayki.app/" 200 "Landing home"
    check_health "https://tuwayki.app" "Landing health"

    info "=== Páginas legales y SEO ==="
    check_url "https://tuwayki.app/terminos" 200 "Legal: Términos"
    check_url "https://tuwayki.app/privacidad" 200 "Legal: Privacidad"
    check_url "https://tuwayki.app/cookies" 200 "Legal: Cookies"
    check_url "https://tuwayki.app/robots.txt" 200 "SEO: robots.txt"
    check_url "https://tuwayki.app/sitemap.xml" 200 "SEO: sitemap.xml"

    info "=== Redirects WWW ==="
    check_redirect "https://www.tuwayki.app/" "tuwayki.app" "www -> apex"

    info "=== APP (sys.tuwayki.app) ==="
    check_url "https://sys.tuwayki.app/" 200 "App root"
    check_health "https://sys.tuwayki.app" "App health"

    info "=== OWNER (admin.tuwayki.app) ==="
    check_url "https://admin.tuwayki.app/login" 200 "Owner login"
    check_health "https://admin.tuwayki.app" "Owner health"

    info "=== Compatibilidad (redirects heredados) ==="
    check_redirect "https://tuwayki.app/home" "tuwayki.app" "/home -> landing"
    check_redirect "https://tuwayki.app/owner/login" "admin.tuwayki.app" "/owner/login -> admin"
    check_redirect "https://tuwayki.app/dashboard" "sys.tuwayki.app" "/dashboard -> sys"
    check_redirect "https://tuwayki.app/venta" "sys.tuwayki.app" "/venta -> sys"

    info "=== Cabeceras de seguridad ==="
    HEADERS="$(curl -sI --max-time 10 "https://sys.tuwayki.app/" 2>/dev/null || echo '')"
    if echo "$HEADERS" | grep -qi "x-robots-tag.*noindex"; then
        pass "sys.tuwayki.app tiene X-Robots-Tag: noindex"
    else
        fail_t "sys.tuwayki.app falta X-Robots-Tag: noindex"
    fi

    HEADERS="$(curl -sI --max-time 10 "https://admin.tuwayki.app/login" 2>/dev/null || echo '')"
    if echo "$HEADERS" | grep -qi "x-robots-tag.*noindex"; then
        pass "admin.tuwayki.app tiene X-Robots-Tag: noindex"
    else
        fail_t "admin.tuwayki.app falta X-Robots-Tag: noindex"
    fi

else
    # ─── Prueba de superficie única / servidor de prueba ─────────────────
    info "=== Backend: $BASE_URL ==="
    check_health "$BASE_URL" "Health check (backend)"
    check_url "$BASE_URL/api/ping" 200 "Ping (backend)"
    check_url "$BASE_URL/api/health" 200 "Health endpoint (backend)"

    info "=== Frontend: $FRONTEND_URL ==="
    if $BACKEND_ONLY; then
        # En modo --backend-only el frontend no se sirve
        warn_t "Modo --backend-only: saltando pruebas de frontend"
    else
        check_url "$FRONTEND_URL/" 200 "Raíz / (frontend)"
        # Verificar que el frontend devuelve HTML
        content_type="$(curl -s -o /dev/null -w '%{content_type}' --max-time 10 "$FRONTEND_URL/" 2>/dev/null)"
        if [[ "$content_type" == *"text/html"* ]]; then
            pass "Content-Type de / es text/html"
        else
            warn_t "Content-Type de / es '$content_type' (esperado: text/html)"
        fi
    fi
fi

# ─── Resumen de resultados ───────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
TOTAL=$((PASS + FAIL + WARN))
echo -e "  Total: $TOTAL | ${GREEN}Pass: $PASS${NC} | ${RED}Fail: $FAIL${NC} | ${YELLOW}Warn: $WARN${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}  HAY FALLOS \u2014 revisar antes de confirmar el deploy${NC}"
    exit 1
else
    echo -e "${GREEN}  TODAS LAS PRUEBAS PASARON${NC}"
    exit 0
fi
