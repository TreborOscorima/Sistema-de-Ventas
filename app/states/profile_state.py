"""Estado de preferencias personales del usuario (autoservicio).

Aísla las preferencias que cada usuario configura para sí mismo —sin necesitar
permisos de administrador— del estado de configuración de empresa/sucursal
(``ConfigState``, gated por ``manage_config``).

Hoy contiene la **preferencia de impresión por cajero**: cada usuario elige el
tamaño de papel de SU impresora (58 / 80 / A4 / ancho custom en mm) o hereda el
de la sucursal. La resolución en runtime vive en ``MixinState`` (cascada
usuario → sucursal → default); acá solo se edita y persiste la preferencia.
"""
import reflex as rx
from sqlmodel import select

from app.models import User
from app.utils.receipt_format import normalize_paper
from .mixin_state import MixinState


class ProfileState(MixinState):
    """Preferencias autoservicio del usuario logueado."""

    # Modal de preferencias de impresión.
    profile_prefs_open: bool = False
    # Valor del selector: "" (hereda sucursal) | "58" | "80" | "A4" | "custom".
    profile_receipt_paper: str = ""
    # Ancho en mm cuando profile_receipt_paper == "custom".
    profile_receipt_paper_custom_mm: str = ""

    @rx.event
    def set_profile_receipt_paper(self, value: str):
        self.profile_receipt_paper = (value or "").strip()

    @rx.event
    def set_profile_receipt_paper_custom_mm(self, value: str):
        self.profile_receipt_paper_custom_mm = (value or "").strip()

    @rx.event
    def open_print_prefs(self):
        """Abre el modal precargando la preferencia actual del usuario."""
        if hasattr(self, "_resolve_current_user"):
            self._resolve_current_user()
        user = getattr(self, "_cached_user", None) or {}
        stored = (user.get("receipt_paper") or "").strip().lower()
        if not stored:
            self.profile_receipt_paper = ""
            self.profile_receipt_paper_custom_mm = ""
        elif stored in {"a4", "a-4"}:
            self.profile_receipt_paper = "A4"
            self.profile_receipt_paper_custom_mm = ""
        elif stored in {"58", "80"}:
            self.profile_receipt_paper = stored
            self.profile_receipt_paper_custom_mm = ""
        elif stored.isdigit():
            self.profile_receipt_paper = "custom"
            self.profile_receipt_paper_custom_mm = stored
        else:
            self.profile_receipt_paper = ""
            self.profile_receipt_paper_custom_mm = ""
        self.profile_prefs_open = True

    @rx.event
    def close_print_prefs(self):
        self.profile_prefs_open = False

    @rx.event
    def save_print_prefs(self):
        """Persiste la preferencia del cajero y la aplica de inmediato."""
        if hasattr(self, "_resolve_current_user"):
            self._resolve_current_user()
        user = getattr(self, "_cached_user", None) or {}
        user_id = user.get("id")
        if not user_id:
            return rx.toast(
                "Sesión no válida. Vuelve a iniciar sesión.", duration=3000
            )

        mode = (self.profile_receipt_paper or "").strip()
        if not mode:
            paper_value = None  # hereda la configuración de la sucursal
        elif mode == "custom":
            mm = (self.profile_receipt_paper_custom_mm or "").strip()
            if not mm.isdigit():
                return rx.toast(
                    "Ingresa un ancho válido en milímetros (40–120).",
                    duration=3500,
                )
            paper_value = normalize_paper(mm)
        elif mode.lower() in {"a4", "a-4"}:
            paper_value = "a4"
        elif mode in {"58", "80"}:
            paper_value = mode
        else:
            paper_value = normalize_paper(mode)

        with rx.session() as session:
            session.info["tenant_bypass"] = True
            db_user = session.exec(
                select(User).where(User.id == int(user_id))
            ).first()
            if db_user is None:
                return rx.toast("Usuario no encontrado.", duration=3000)
            db_user.receipt_paper = paper_value
            # El ancho se deriva del papel; no se expone en el autoservicio.
            db_user.receipt_width = None
            session.add(db_user)
            session.commit()

        # Refrescar _cached_user para que el nuevo papel aplique ya en esta
        # sesión (la cascada de impresión lee _cached_user, no el rx.var cacheado).
        try:
            self._cached_user_time = 0.0
        except AttributeError:
            pass
        if hasattr(self, "_resolve_current_user"):
            self._resolve_current_user()

        self.profile_prefs_open = False
        if paper_value is None:
            label = "la configuración de la sucursal"
        elif paper_value == "a4":
            label = "A4"
        else:
            label = f"{paper_value} mm"
        return rx.toast(
            f"Listo: tus tickets se imprimirán en {label}.", duration=3000
        )
