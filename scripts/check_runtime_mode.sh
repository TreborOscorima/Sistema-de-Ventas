#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8101}"

echo "Checking runtime mode at: ${BASE_URL}"

home_html="$(curl -fsS "${BASE_URL}/" || true)"
vite_headers="$(curl -sSI "${BASE_URL}/@vite/client" || true)"
vite_status="$(printf "%s" "${vite_headers}" | awk 'NR==1 {print $2}')"
vite_content_type="$(printf "%s" "${vite_headers}" | tr -d '\r' | awk -F': ' 'tolower($1)=="content-type" {print tolower($2)}' | head -n1)"

# Reflex producción usa bundle hasheado: /assets/context-*.js
context_asset="$(printf "%s" "${home_html}" | grep -oE '/assets/context-[^"[:space:]]+\.js' | head -n1 || true)"
context_js=""
if [[ -n "${context_asset}" ]]; then
  context_js="$(curl -fsS "${BASE_URL}${context_asset}" || true)"
fi

dev_mode_line="$(printf "%s" "${context_js}" | grep -oE 'isDevMode[[:space:]]*=[[:space:]]*(true|false)' | head -n1 || true)"
hmr_present="no"
if printf "%s" "${home_html}" | grep -q "inject-hmr-runtime"; then
  hmr_present="yes"
fi

echo "context asset: ${context_asset:-not found}"
echo "isDevMode line: ${dev_mode_line:-not found}"
echo "@vite/client status: ${vite_status:-unknown}"
echo "@vite/client content-type: ${vite_content_type:-unknown}"
echo "inject-hmr-runtime in HTML: ${hmr_present}"

if printf "%s" "${dev_mode_line}" | grep -q "true"; then
  echo "RESULT: DEV runtime detected (isDevMode=true)."
  exit 2
fi

# Si @vite/client responde JS real, probablemente está en dev.
if [[ "${vite_status:-}" == "200" ]] && printf "%s" "${vite_content_type}" | grep -q "javascript"; then
  echo "RESULT: DEV runtime likely detected (@vite/client=200 javascript)."
  exit 2
fi

if [[ "${hmr_present}" == "yes" ]]; then
  echo "RESULT: DEV runtime likely detected (HMR runtime import found)."
  exit 2
fi

echo "RESULT: Production runtime looks OK."
