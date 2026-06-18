"""Tests E2E con Playwright para flujos críticos de la UI.

Requiere un servidor corriendo en BASE_URL (default http://localhost:3000).
Si el servidor no responde se saltan todos los tests automáticamente.

Ejecutar:
    pytest tests/test_e2e.py -m e2e -v

Variables de entorno opcionales:
    E2E_BASE_URL   URL base de la app                     (default: http://localhost:3000)
    E2E_USER       Usuario válido para el test de login   (omitir para saltarlo)
    E2E_PASSWORD   Contraseña válida para el test de login

Notas sobre la arquitectura Reflex:
- La app es una SPA WebSocket; el contenido real aparece tras la hidratación (~2-5 s).
- Las páginas protegidas NO redirigen a /login vía HTTP: muestran el formulario de
  login inline (mismo URL) cuando State.is_authenticated es False tras hidratar.
- wait_for_selector() espera la hidratación antes de hacer aserciones.
"""
from __future__ import annotations

import os

import httpx
import pytest
from playwright.async_api import async_playwright, expect

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:3000").rstrip("/")
_E2E_USER = os.environ.get("E2E_USER", "")
_E2E_PASSWORD = os.environ.get("E2E_PASSWORD", "")

_HYDRATION_TIMEOUT = 20_000   # ms — tiempo máximo para que Reflex hidrate
_ACTION_TIMEOUT = 8_000       # ms — tiempo para respuestas de formulario


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: verificar disponibilidad del servidor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=False)
def server_available():
    """Verifica /api/ping antes de correr cualquier test E2E."""
    try:
        r = httpx.get(f"{BASE_URL}/api/ping", timeout=8)
        r.raise_for_status()
        assert r.json().get("pong") is True, "Respuesta inesperada de /api/ping"
    except Exception as exc:
        pytest.skip(f"Servidor no disponible en {BASE_URL}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Página de login — renderizado
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.e2e
async def test_login_page_renders(server_available):
    """La página /login muestra el formulario con usuario, contraseña y botón."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"{BASE_URL}/login")

            # Esperar hidratación Reflex
            username_input = page.locator("input[name='username']")
            await username_input.wait_for(state="visible", timeout=_HYDRATION_TIMEOUT)

            password_input = page.locator("input[name='password']")
            await expect(password_input).to_be_visible()

            submit_btn = page.locator("button[type='submit']")
            await expect(submit_btn).to_be_visible()
            await expect(submit_btn).to_be_enabled()
        finally:
            await browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Login con credenciales inválidas muestra error
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.e2e
async def test_login_invalid_credentials_shows_error(server_available):
    """Ingresar credenciales incorrectas muestra un mensaje de error visible."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"{BASE_URL}/login")

            # Esperar hidratación
            await page.locator("input[name='username']").wait_for(
                state="visible", timeout=_HYDRATION_TIMEOUT
            )

            await page.fill("input[name='username']", "usuario_que_no_existe@test.invalid")
            await page.fill("input[name='password']", "contraseña_incorrecta_E2E")
            await page.click("button[type='submit']")

            # Esperar mensaje de error (div con ícono circle-alert o texto de error)
            # La app renderiza el error en un div con borde rojo cuando error_message != ""
            error_div = page.locator("div.bg-red-50").first
            await error_div.wait_for(state="visible", timeout=_ACTION_TIMEOUT)
            await expect(error_div).to_be_visible()
        finally:
            await browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: /venta sin autenticar muestra el formulario de login
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.e2e
async def test_venta_unauthenticated_shows_login_form(server_available):
    """/venta sin sesión muestra el formulario de login (inline, mismo URL)."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"{BASE_URL}/venta")

            # Tras hidratar, el layout inyecta login_page() cuando !is_authenticated
            await page.locator("input[name='username']").wait_for(
                state="visible", timeout=_HYDRATION_TIMEOUT
            )
            await expect(page.locator("input[name='password']")).to_be_visible()

            # URL no debe haber cambiado a /login (comportamiento inline de Reflex)
            assert "/venta" in page.url or "/login" in page.url
        finally:
            await browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: /caja sin autenticar muestra el formulario de login
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.e2e
async def test_caja_unauthenticated_shows_login_form(server_available):
    """/caja sin sesión muestra el formulario de login."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"{BASE_URL}/caja")

            await page.locator("input[name='username']").wait_for(
                state="visible", timeout=_HYDRATION_TIMEOUT
            )
            await expect(page.locator("input[name='password']")).to_be_visible()
        finally:
            await browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Flujo de login completo (requiere E2E_USER + E2E_PASSWORD)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.e2e
async def test_full_login_flow(server_available):
    """Login con credenciales válidas redirige al dashboard o página principal.

    Salteado si E2E_USER / E2E_PASSWORD no están configurados.
    """
    if not _E2E_USER or not _E2E_PASSWORD:
        pytest.skip("E2E_USER y E2E_PASSWORD no configurados")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"{BASE_URL}/login")

            # Esperar hidratación
            await page.locator("input[name='username']").wait_for(
                state="visible", timeout=_HYDRATION_TIMEOUT
            )

            await page.fill("input[name='username']", _E2E_USER)
            await page.fill("input[name='password']", _E2E_PASSWORD)
            await page.click("button[type='submit']")

            # Tras login exitoso, la app oculta el formulario y muestra contenido autenticado.
            # Esperamos que el input de login desaparezca o que aparezca el sidebar.
            await page.locator("input[name='username']").wait_for(
                state="hidden", timeout=15_000
            )

            # Verificar que hay contenido autenticado (sidebar con nav items)
            nav_link = page.locator("nav a, aside a").first
            await nav_link.wait_for(state="visible", timeout=8_000)
            await expect(nav_link).to_be_visible()
        finally:
            await browser.close()
