"""Tests para el módulo de internacionalización (i18n).

Valida integridad de las constantes de mensajes y su uso correcto
con .format() placeholders.
"""

import pytest
from app.i18n import MSG
from app.i18n.messages import _Messages


class TestMSGIntegrity:
    """Verifica que MSG expone todas las constantes esperadas."""

    def test_msg_is_singleton(self):
        """MSG es una instancia única de _Messages."""
        assert isinstance(MSG, _Messages)

    def test_permission_constants_exist(self):
        assert MSG.PERM_CASH
        assert MSG.PERM_CASH_MGMT
        assert MSG.PERM_SALES
        assert MSG.PERM_DELETE_SALE
        assert MSG.PERM_EXPORT

    def test_validation_constants_exist(self):
        assert MSG.VAL_COMPANY_UNDEFINED
        assert MSG.VAL_COMPANY_BRANCH_UNDEFINED
        assert MSG.VAL_USER_NOT_FOUND
        assert MSG.VAL_SESSION_REQUIRED
        assert MSG.VAL_INVALID_NUMERIC
        assert MSG.VAL_AMOUNT_GT_ZERO
        assert MSG.VAL_ENTER_REASON
        assert MSG.VAL_INVALID_SALE_ID

    def test_cash_constants_exist(self):
        assert MSG.CASH_OPEN_REQUIRED
        assert MSG.CASH_OPEN_REQUIRED_OP
        assert MSG.CASH_OPEN_REQUIRED_MGMT
        assert MSG.CASH_INVALID_INITIAL
        assert MSG.CASH_ALREADY_OPEN
        assert MSG.CASH_OPENED
        assert MSG.CASH_MOVEMENT_OK
        assert MSG.CASH_RECORD_NOT_FOUND

    def test_sale_constants_exist(self):
        assert MSG.SALE_CONFIRMED
        assert MSG.SALE_NOT_FOUND
        assert MSG.SALE_SELECT_DELETE
        assert MSG.SALE_ENTER_DELETE_REASON
        assert MSG.SALE_INVALID_DATA
        assert MSG.SALE_PROCESS_ERROR
        assert MSG.SALE_NO_EXPORT

    def test_fiscal_constants_exist(self):
        assert MSG.FISCAL_CONFIG_SAVED
        assert MSG.FISCAL_TOKEN_EMPTY
        assert MSG.FISCAL_TOKEN_SAVED
        assert MSG.FISCAL_CERT_EMPTY
        assert MSG.FISCAL_CERT_INVALID_PEM
        assert MSG.FISCAL_KEY_EMPTY
        assert MSG.FISCAL_KEY_INVALID_PEM
        assert MSG.FISCAL_KEY_SAVED
        assert MSG.FISCAL_DOC_NOT_FOUND
        assert MSG.FISCAL_NC_FAILED
        assert MSG.FISCAL_NC_ERROR

    def test_report_dicts_not_empty(self):
        assert len(MSG.REPORT_MOVEMENT_TYPES) >= 8
        assert len(MSG.REPORT_PAYMENT_METHODS) >= 10
        assert len(MSG.REPORT_AGING_LABELS) >= 5


class TestMSGFormatStrings:
    """Valida que los mensajes con placeholders funcionan con .format()."""

    def test_sale_invalid_data_format(self):
        result = MSG.SALE_INVALID_DATA.format(error_id="ABC123")
        assert "ABC123" in result

    def test_sale_process_error_format(self):
        result = MSG.SALE_PROCESS_ERROR.format(error_id="XYZ789")
        assert "XYZ789" in result

    def test_fiscal_doc_authorized_format(self):
        result = MSG.FISCAL_DOC_AUTHORIZED.format(full_number="F001-00001")
        assert "F001-00001" in result

    def test_fiscal_doc_errors_format(self):
        result = MSG.FISCAL_DOC_ERRORS.format(full_number="B001-00002")
        assert "B001-00002" in result

    def test_fiscal_doc_status_format(self):
        result = MSG.FISCAL_DOC_STATUS.format(
            full_number="F001-00003", status="pending"
        )
        assert "F001-00003" in result
        assert "pending" in result

    def test_fiscal_nc_exists_format(self):
        result = MSG.FISCAL_NC_EXISTS.format(full_number="NC01-00001")
        assert "NC01-00001" in result

    def test_fiscal_nc_authorized_format(self):
        result = MSG.FISCAL_NC_AUTHORIZED.format(full_number="NC01-00002")
        assert "NC01-00002" in result

    def test_fiscal_nc_status_format(self):
        result = MSG.FISCAL_NC_STATUS.format(
            full_number="NC01-00003", status="error"
        )
        assert "NC01-00003" in result
        assert "error" in result

    def test_lookup_ruc_bad_status_format(self):
        result = MSG.LOOKUP_RUC_BAD_STATUS.format(status="BAJA")
        assert "BAJA" in result

    def test_lookup_ruc_bad_condition_format(self):
        result = MSG.LOOKUP_RUC_BAD_CONDITION.format(condition="NO HABIDO")
        assert "NO HABIDO" in result

    def test_lookup_not_found_format(self):
        result = MSG.LOOKUP_NOT_FOUND.format(doc_number="20123456789")
        assert "20123456789" in result


class TestMSGReportLabels:
    """Valida las etiquetas de reportes."""

    def test_movement_types_keys(self):
        expected_keys = {
            "apertura", "cierre", "venta", "reserva",
            "adelanto", "cobranza", "inicial_credito", "gasto_caja_chica",
        }
        assert set(MSG.REPORT_MOVEMENT_TYPES.keys()) == expected_keys

    def test_payment_methods_keys(self):
        expected_keys = {
            "efectivo", "tarjeta_debito", "tarjeta_credito",
            "yape", "plin", "transferencia", "billetera_digital",
            "mixto", "otro", "credito", "cheque", "no_especificado",
        }
        assert set(MSG.REPORT_PAYMENT_METHODS.keys()) == expected_keys

    def test_aging_labels_keys(self):
        expected_keys = {"current", "1_30", "31_60", "61_90", "90_plus"}
        assert set(MSG.REPORT_AGING_LABELS.keys()) == expected_keys

    def test_report_sheet_titles_are_strings(self):
        for attr in [
            "REPORT_SUMMARY_SHEET", "REPORT_TITLE", "REPORT_KPI_HEADER",
            "REPORT_DAILY_SHEET", "REPORT_DAILY_TITLE",
            "REPORT_CATEGORY_SHEET", "REPORT_CATEGORY_TITLE",
            "REPORT_PORTFOLIO_SHEET", "REPORT_CASH_SHEET",
            "REPORT_BY_SELLER_SHEET", "REPORT_TX_DETAIL_SHEET",
            "REPORT_TOP_PRODUCTS_SHEET", "REPORT_HOURLY_SHEET",
            "REPORT_VALUATION_SHEET", "REPORT_INVENTORY_SHEET",
            "REPORT_BY_CLIENT_SHEET", "REPORT_INSTALLMENTS_SHEET",
            "REPORT_CASH_MOVES_SHEET", "REPORT_DAILY_SALES_SHEET",
            "REPORT_CLOSINGS_SHEET", "REPORT_CAT_SALES_SHEET",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str), f"{attr} should be str, got {type(val)}"
            assert len(val) > 0, f"{attr} should not be empty"


class TestMSGFallbacksAndActions:
    """Valida constantes de fallbacks y acciones."""

    def test_fallback_constants_exist(self):
        for attr in [
            "FALLBACK_UNKNOWN", "FALLBACK_UNIT", "FALLBACK_NO_ROLE",
            "FALLBACK_NO_NUMBER", "FALLBACK_NOT_SPECIFIED",
            "FALLBACK_NO_CLIENT", "FALLBACK_NO_CATEGORY",
            "FALLBACK_NO_DETAIL", "FALLBACK_NO_DESC", "FALLBACK_PRODUCT",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_action_constants_exist(self):
        for attr in [
            "ACTION_OPENING", "ACTION_CLOSING", "ACTION_SALE",
            "ACTION_INITIAL_CREDIT", "ACTION_INSTALLMENT_PAYMENT",
            "ACTION_INCOME",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_alert_constants_exist(self):
        for attr in [
            "ALERT_CRITICAL_STOCK", "ALERT_LOW_STOCK", "ALERT_NO_STOCK",
            "ALERT_OVERDUE_INSTALLMENTS", "ALERT_OPEN_CASHBOX",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"


class TestMSGAuthAndRoles:
    """Valida constantes de autenticación, roles y suscripción."""

    def test_role_constants_exist(self):
        for attr in [
            "ROLE_SUPERADMIN", "ROLE_ADMIN", "ROLE_USER",
            "ROLE_CASHIER", "ROLE_GUEST",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_status_constants_exist(self):
        for attr in [
            "STATUS_ACTIVE", "STATUS_EXPIRED", "STATUS_ABOUT_TO_EXPIRE",
            "STATUS_PAST_DUE", "STATUS_SUSPENDED", "STATUS_UNLIMITED",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_auth_message_constants_exist(self):
        for attr in [
            "AUTH_USER_NOT_FOUND", "AUTH_BRANCH_INVALID",
            "AUTH_BRANCH_NO_ACCESS", "AUTH_BRANCH_UPDATED",
            "AUTH_PASSWORD_UPDATED", "AUTH_PERM_CONFIG",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_branch_message_constants_exist(self):
        for attr in [
            "BRANCH_NAME_REQUIRED", "BRANCH_CREATED",
            "BRANCH_UPDATED", "BRANCH_DELETED",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"


class TestMSGSaleValidations:
    """Valida constantes de validación del servicio de ventas."""

    def test_sale_validation_constants_exist(self):
        for attr in [
            "SALE_VAL_PAYMENT_METHOD", "SALE_VAL_COMPANY", "SALE_VAL_BRANCH",
            "SALE_VAL_CANCELLED_RESERVATION", "SALE_VAL_ALREADY_PAID",
            "SALE_VAL_NO_PRODUCTS", "SALE_VAL_NO_DESCRIPTION",
            "SALE_VAL_NO_AMOUNT", "SALE_VAL_INVALID_INITIAL",
            "SALE_VAL_CASH_AMOUNT", "SALE_VAL_MIXED_AMOUNTS",
            "SALE_VAL_CLIENT_REQUIRED", "SALE_VAL_CLIENT_NOT_FOUND",
            "SALE_VAL_CREDIT_LIMIT", "SALE_VAL_INVALID_INSTALLMENTS",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_sale_validation_format_strings(self):
        assert "{description}" in MSG.SALE_VAL_INVALID_QTY
        assert "{description}" in MSG.SALE_VAL_MULTI_MATCH
        assert "{identifier}" in MSG.SALE_VAL_NOT_FOUND
        assert "{description}" in MSG.SALE_VAL_INVALID_PRICE
        assert "{description}" in MSG.SALE_VAL_INSUFFICIENT_STOCK

    def test_sale_action_constants(self):
        assert MSG.SALE_ACTION_CREDIT_INITIAL
        assert MSG.SALE_ACTION_CREDIT


class TestMSGCreditsAndAccounts:
    """Valida constantes de créditos y cuentas por cobrar."""

    def test_credit_status_constants(self):
        for attr in ["CREDIT_STATUS_PAID", "CREDIT_STATUS_PARTIAL", "CREDIT_STATUS_PENDING"]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_accounts_headers(self):
        for attr in [
            "ACCOUNTS_INSTALLMENTS_REGISTERED", "ACCOUNTS_INSTALLMENTS_PAID",
            "ACCOUNTS_INSTALLMENTS_PENDING", "ACCOUNTS_INSTALLMENTS_OVERDUE",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_extended_fallbacks(self):
        for attr in [
            "FALLBACK_CLIENT", "FALLBACK_CLIENT_NOT_REGISTERED",
            "FALLBACK_NO_DATE", "FALLBACK_SYSTEM", "FALLBACK_NO_OBS",
            "FALLBACK_NO_REFERENCE", "FALLBACK_NO_PRODUCTS",
            "FALLBACK_GENERAL", "FALLBACK_SERVICES",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"


class TestMSGDefaultPaymentMethods:
    """Valida constantes de métodos de pago por defecto."""

    def test_default_pm_constants(self):
        for attr in [
            "DEFAULT_PM_CASH", "DEFAULT_PM_CASH_DESC",
            "DEFAULT_PM_DEBIT", "DEFAULT_PM_DEBIT_DESC",
            "DEFAULT_PM_CREDIT", "DEFAULT_PM_CREDIT_DESC",
            "DEFAULT_PM_YAPE", "DEFAULT_PM_YAPE_DESC",
            "DEFAULT_PM_PLIN", "DEFAULT_PM_PLIN_DESC",
            "DEFAULT_PM_TRANSFER", "DEFAULT_PM_MIXED", "DEFAULT_PM_MIXED_DESC",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_hist_pay_abbr_dict(self):
        assert len(MSG.HIST_PAY_ABBR) >= 8
        assert "efectivo" in MSG.HIST_PAY_ABBR
        assert "yape" in MSG.HIST_PAY_ABBR

    def test_hist_display_labels(self):
        for attr in [
            "HIST_FILTER_ALL", "HIST_FILTER_ALL_F",
            "HIST_SOURCE_SALE", "HIST_SOURCE_COLLECTION",
            "HIST_CREDIT_SALE", "HIST_CREDIT_COMPLETED",
            "HIST_CREDIT_PENDING", "HIST_PAYMENT_REGISTERED",
            "HIST_CASH_SALE",
        ]:
            val = getattr(MSG, attr)
            assert isinstance(val, str) and len(val) > 0, f"{attr} missing"

    def test_hist_payment_in_format(self):
        result = MSG.HIST_PAYMENT_IN.format(method="Yape")
        assert "Yape" in result
