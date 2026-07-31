"""Tests de la cascada de tamaño de papel POR USUARIO (preferencia del cajero).

Verifica la resolución del papel/ancho de impresión implementada en
``MixinState`` con la precedencia:

    override por ticket (POS) → preferencia del cajero → sucursal → default (80)

Objetivo del feature: en una misma sucursal, cada cajero (con su propio usuario)
puede imprimir en el tamaño de SU impresora (58 / 80 / A4 / ancho custom en mm)
sin afectar la configuración de la sucursal ni a los demás cajeros. ``NULL``/""
en la preferencia = hereda de la sucursal.

Los tests no tocan la BD: se stubbea ``_company_settings_snapshot`` (config de
sucursal) y ``_cached_user`` (usuario logueado), que son las únicas dependencias
de la cascada.
"""

import pytest

from app.constants import DEFAULT_RECEIPT_WIDTH, DEFAULT_PAPER_WIDTH_MM
from app.states.mixin_state import MixinState


# --------------------------------------------------------------------------- #
# Stub liviano de estado                                                       #
# --------------------------------------------------------------------------- #

class _StateStub(MixinState):
    """Instancia mínima para ejercitar la cascada sin Reflex ni BD."""

    def __init__(
        self,
        *,
        user_paper: str | None = "",
        user_width=None,
        branch_paper: str = "80",
        branch_width=None,
        pos_override: str = "",
    ):
        # Usuario logueado (lo que arma auth_state en _cached_user).
        self._cached_user = {
            "receipt_paper": user_paper,
            "receipt_width": user_width,
        }
        # Config de la sucursal activa.
        self._branch_paper = branch_paper
        self._branch_width = branch_width
        # Override del selector del POS ("" = no override).
        self.receipt_print_paper_override = pos_override

    def _company_settings_snapshot(self, branch_id=None):  # noqa: D401
        return {
            "receipt_paper": self._branch_paper,
            "receipt_width": self._branch_width,
        }


def make_state(**kwargs) -> _StateStub:
    return _StateStub(**kwargs)


# --------------------------------------------------------------------------- #
# Helpers de lectura de la preferencia del usuario                            #
# --------------------------------------------------------------------------- #

class TestUserPreferenceReaders:
    def test_user_paper_present(self):
        st = make_state(user_paper="58")
        assert st._user_receipt_paper() == "58"

    def test_user_paper_empty_inherits(self):
        st = make_state(user_paper="")
        assert st._user_receipt_paper() == ""

    def test_user_paper_none_is_empty(self):
        st = make_state(user_paper=None)
        assert st._user_receipt_paper() == ""

    def test_user_paper_strips_whitespace(self):
        st = make_state(user_paper="  a4  ")
        assert st._user_receipt_paper() == "a4"

    def test_user_width_int(self):
        st = make_state(user_width=30)
        assert st._user_receipt_width() == 30

    def test_user_width_numeric_string(self):
        st = make_state(user_width="30")
        assert st._user_receipt_width() == 30

    def test_user_width_none(self):
        st = make_state(user_width=None)
        assert st._user_receipt_width() is None

    def test_user_width_garbage_is_none(self):
        st = make_state(user_width="abc")
        assert st._user_receipt_width() is None

    def test_readers_tolerate_missing_cached_user(self):
        st = make_state()
        st._cached_user = None
        assert st._user_receipt_paper() == ""
        assert st._user_receipt_width() is None


# --------------------------------------------------------------------------- #
# _receipt_paper_value: papel normalizado ('58' | '80' | 'a4' | '<mm>')       #
# --------------------------------------------------------------------------- #

class TestReceiptPaperValueCascade:
    def test_no_pref_inherits_branch(self):
        st = make_state(user_paper="", branch_paper="80")
        assert st._receipt_paper_value() == "80"

    def test_user_58_beats_branch_80(self):
        """Cajero 1: impresora 58 mm en una sucursal configurada a 80."""
        st = make_state(user_paper="58", branch_paper="80")
        assert st._receipt_paper_value() == "58"

    def test_user_80_beats_branch_58(self):
        """Cajero 2: impresora 80 mm aunque la sucursal esté en 58."""
        st = make_state(user_paper="80", branch_paper="58")
        assert st._receipt_paper_value() == "80"

    def test_user_a4_beats_branch(self):
        """Cajero 3: impresora A4."""
        st = make_state(user_paper="a4", branch_paper="58")
        assert st._receipt_paper_value() == "a4"

    def test_user_custom_mm(self):
        st = make_state(user_paper="76", branch_paper="80")
        assert st._receipt_paper_value() == "76"

    def test_branch_used_when_user_empty(self):
        st = make_state(user_paper="", branch_paper="58")
        assert st._receipt_paper_value() == "58"

    def test_default_80_when_nothing_set(self, monkeypatch):
        monkeypatch.delenv("RECEIPT_PAPER", raising=False)
        st = make_state(user_paper="", branch_paper="")
        assert st._receipt_paper_value() == "80"

    def test_pos_override_beats_user_pref(self):
        """El override del ticket (POS) es lo más específico y gana a todo."""
        st = make_state(user_paper="58", branch_paper="80", pos_override="a4")
        assert st._receipt_paper_value(use_override=True) == "a4"

    def test_pos_override_ignored_without_flag(self):
        """Sin use_override, el override del POS no aplica; manda el usuario."""
        st = make_state(user_paper="58", branch_paper="80", pos_override="a4")
        assert st._receipt_paper_value(use_override=False) == "58"

    def test_pos_override_empty_falls_through_to_user(self):
        st = make_state(user_paper="58", branch_paper="80", pos_override="")
        assert st._receipt_paper_value(use_override=True) == "58"


# --------------------------------------------------------------------------- #
# _receipt_width: ancho en caracteres derivado de la cascada                   #
# --------------------------------------------------------------------------- #

class TestReceiptWidthCascade:
    def test_user_58_narrow_width(self):
        st = make_state(user_paper="58", branch_paper="80")
        assert st._receipt_width() == 32

    def test_user_80_default_width(self):
        st = make_state(user_paper="80", branch_paper="58")
        assert st._receipt_width() == DEFAULT_RECEIPT_WIDTH

    def test_user_a4_default_width(self):
        st = make_state(user_paper="a4", branch_paper="58")
        assert st._receipt_width() == DEFAULT_RECEIPT_WIDTH

    def test_user_custom_mm_derives_width(self):
        # 76 mm * 0.53 ≈ 40 caracteres
        st = make_state(user_paper="76", branch_paper="80")
        assert st._receipt_width() == round(76 * 0.53)

    def test_user_explicit_width_wins(self):
        """Un ancho explícito del usuario manda sobre el derivado del papel."""
        st = make_state(user_paper="80", user_width=28, branch_paper="80")
        assert st._receipt_width() == 28

    def test_no_pref_inherits_branch_width_derived(self):
        st = make_state(user_paper="", branch_paper="58")
        assert st._receipt_width() == 32

    def test_no_pref_inherits_branch_explicit_width(self):
        st = make_state(user_paper="", branch_paper="80", branch_width=40)
        assert st._receipt_width() == 40


# --------------------------------------------------------------------------- #
# _receipt_paper_mm: ancho físico en mm                                        #
# --------------------------------------------------------------------------- #

class TestReceiptPaperMmCascade:
    def test_user_58_mm(self):
        st = make_state(user_paper="58", branch_paper="80")
        assert st._receipt_paper_mm() == 58

    def test_user_80_mm(self):
        st = make_state(user_paper="80", branch_paper="58")
        assert st._receipt_paper_mm() == DEFAULT_PAPER_WIDTH_MM

    def test_no_pref_inherits_branch_mm(self):
        st = make_state(user_paper="", branch_paper="58")
        assert st._receipt_paper_mm() == 58


# --------------------------------------------------------------------------- #
# Aislamiento entre cajeros de la MISMA sucursal                               #
# --------------------------------------------------------------------------- #

class TestPerUserIsolation:
    def test_three_cashiers_same_branch_distinct_sizes(self):
        """El caso del cliente: 3 cajeros, misma sucursal, papeles distintos.

        La config de la sucursal es común (80 mm), pero cada cajero resuelve su
        propio tamaño sin pisar el de los demás.
        """
        branch = "80"
        cajero1 = make_state(user_paper="58", branch_paper=branch)
        cajero2 = make_state(user_paper="80", branch_paper=branch)
        cajero3 = make_state(user_paper="a4", branch_paper=branch)

        assert cajero1._receipt_paper_value() == "58"
        assert cajero2._receipt_paper_value() == "80"
        assert cajero3._receipt_paper_value() == "a4"

        # Anchos coherentes con cada papel.
        assert cajero1._receipt_width() == 32
        assert cajero2._receipt_width() == DEFAULT_RECEIPT_WIDTH
        assert cajero3._receipt_width() == DEFAULT_RECEIPT_WIDTH

    def test_cashier_without_pref_uses_branch_others_unchanged(self):
        branch = "58"
        con_pref = make_state(user_paper="a4", branch_paper=branch)
        sin_pref = make_state(user_paper="", branch_paper=branch)

        assert con_pref._receipt_paper_value() == "a4"
        # El que no configuró nada sigue la sucursal.
        assert sin_pref._receipt_paper_value() == "58"
