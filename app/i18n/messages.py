"""
Constantes de mensajes user-facing.

Convención de nombres:
- PERM_*   → Permisos denegados
- VAL_*    → Validación de datos
- OK_*     → Operaciones exitosas
- ERR_*    → Errores inesperados
- FISCAL_* → Módulo de facturación electrónica
- CASH_*   → Gestión de caja
- SALE_*   → Ventas / POS
- HIST_*   → Historial / exportación
- REPORT_* → Etiquetas de reportes
"""

from __future__ import annotations


class _Messages:
    """Namespace de mensajes. Acceso via MSG.NOMBRE."""

    __slots__ = ()

    # ── Permisos ──────────────────────────────────────────────
    PERM_CASH = "No tiene permisos para gestionar la caja."
    PERM_CASH_MGMT = "No tiene permisos para Gestion de Caja."
    PERM_SALES = "No tiene permisos para crear ventas."
    PERM_DELETE_SALE = "No tiene permisos para eliminar ventas."
    PERM_EXPORT = "No tiene permisos para exportar datos."

    # ── Validaciones genéricas ────────────────────────────────
    VAL_COMPANY_UNDEFINED = "Empresa no definida."
    VAL_COMPANY_BRANCH_UNDEFINED = "Empresa o sucursal no definida."
    VAL_USER_NOT_FOUND = "Usuario no encontrado."
    VAL_SESSION_REQUIRED = "Inicie sesión para abrir caja."
    VAL_INVALID_NUMERIC = "Valores numéricos inválidos."
    VAL_AMOUNT_GT_ZERO = "El monto total debe ser mayor a 0."
    VAL_ENTER_REASON = "Ingrese un motivo."
    VAL_INVALID_SALE_ID = "ID de venta inválido."

    # ── Caja ──────────────────────────────────────────────────
    CASH_OPEN_REQUIRED = "Debe aperturar la caja para registrar movimientos."
    CASH_OPEN_REQUIRED_OP = "Debe aperturar la caja para operar."
    CASH_OPEN_REQUIRED_MGMT = (
        "Debe aperturar la caja para operar la gestion de caja."
    )
    CASH_INVALID_INITIAL = "Ingrese un monto válido para la caja inicial."
    CASH_ALREADY_OPEN = "Ya existe una caja abierta."
    CASH_OPENED = "Caja abierta. Jornada iniciada."
    CASH_MOVEMENT_OK = "Movimiento registrado correctamente."
    CASH_RECORD_NOT_FOUND = "Registro de caja no encontrado."
    CASH_CLOSE_INVALID = "Registro de cierre no valido."
    CASH_CLOSE_NOT_CLOSE = "El registro seleccionado no es un cierre."
    CASH_NO_MOVEMENTS_TODAY = "No hay movimientos de caja hoy."
    CASH_NO_MOVEMENTS_EXPORT = "No hay movimientos de caja para exportar."
    CASH_NO_MOVEMENTS_PRINT = "No hay movimientos de caja para imprimir."
    CASH_NO_OPENCLOSE_EXPORT = "No hay aperturas o cierres para exportar."
    CASH_NO_MOVEMENTS_GENERIC = "No hay movimientos para exportar."

    # ── Ventas / POS ──────────────────────────────────────────
    SALE_CONFIRMED = "Venta confirmada."
    SALE_NOT_FOUND = "Venta no encontrada."
    SALE_SELECT_DELETE = "Seleccione una venta a eliminar."
    SALE_ENTER_DELETE_REASON = (
        "Ingrese el motivo de la eliminación de la venta."
    )
    SALE_INVALID_DATA = "Datos de venta inválidos. Código: {error_id}"
    SALE_PROCESS_ERROR = "Error al procesar la venta. Código: {error_id}"
    SALE_NO_EXPORT = "No hay ventas para exportar."

    # ── Historial / Exportación ───────────────────────────────
    HIST_NO_CLOSINGS_EXPORT = "No hay cierres para exportar."
    HIST_NO_INCOMES_EXPORT = "No hay ingresos para exportar."

    # ── Facturación Electrónica ───────────────────────────────
    FISCAL_CONFIG_SAVED = "Configuración de facturación guardada."
    FISCAL_CONFIG_SAVED_SHORT = "Configuración guardada"
    FISCAL_SAVE_FIRST = "Guarde la configuración primero."
    FISCAL_SAVE_FIRST_FISCAL = "Guarde la configuración fiscal primero."
    FISCAL_TOKEN_EMPTY = "El token no puede estar vacío."
    FISCAL_TOKEN_SAVED = "Token de Nubefact guardado de forma segura."
    FISCAL_LOOKUP_TOKEN_SAVED = "Token de consulta guardado de forma segura."
    FISCAL_CERT_EMPTY = "El certificado no puede estar vacío."
    FISCAL_CERT_INVALID_PEM = (
        "Formato inválido. Pegue el contenido PEM completo "
        "(incluyendo -----BEGIN CERTIFICATE-----)."
    )
    FISCAL_CERT_SAVED = "Certificado AFIP guardado de forma segura."
    FISCAL_KEY_EMPTY = "La clave privada no puede estar vacía."
    FISCAL_KEY_INVALID_PEM = (
        "Formato inválido. Pegue el contenido PEM completo "
        "(incluyendo -----BEGIN RSA PRIVATE KEY-----)."
    )
    FISCAL_KEY_SAVED = "Clave privada AFIP guardada de forma segura."
    FISCAL_COMPANY_UNDEFINED = "No se pudo determinar la empresa."
    FISCAL_BRANCH_UNDEFINED = "No se pudo determinar empresa/sucursal."
    FISCAL_RETRY_FAILED = "No se pudo reintentar el documento."
    FISCAL_DOC_AUTHORIZED = (
        "Documento {full_number} autorizado correctamente."
    )
    FISCAL_DOC_ERRORS = (
        "Documento {full_number} sigue con errores. "
        "Verifique la configuración e intente de nuevo."
    )
    FISCAL_DOC_ERRORS_SHORT = (
        "Documento {full_number} sigue con errores. "
        "Verifique la configuración."
    )
    FISCAL_DOC_STATUS = "Documento {full_number} en estado: {status}."
    FISCAL_RETRY_ERROR = "Error al reintentar el documento fiscal."
    FISCAL_DOC_NOT_FOUND = "Documento fiscal no encontrado."
    FISCAL_ANNUL_AUTHORIZED_ONLY = (
        "Solo se puede anular un documento autorizado por SUNAT/AFIP."
    )
    FISCAL_NC_EXISTS = (
        "Ya existe una Nota de Crédito para este documento: {full_number}."
    )
    FISCAL_READ_ERROR = "Error leyendo datos del documento."
    FISCAL_NC_AUTHORIZED = (
        "Nota de Crédito {full_number} emitida y autorizada."
    )
    FISCAL_NC_STATUS = (
        "Nota de Crédito {full_number} en estado: {status}. "
        "Revise los documentos fiscales."
    )
    FISCAL_NC_FAILED = "No se pudo emitir la Nota de Crédito."
    FISCAL_NC_ERROR = "Error al emitir la Nota de Crédito."

    # ── Lookup fiscal (consulta RUC/CUIT) ─────────────────────
    LOOKUP_RUC_BAD_STATUS = (
        "RUC con estado {status}. No se puede emitir factura."
    )
    LOOKUP_RUC_BAD_CONDITION = (
        "RUC con condicion {condition}. Verifique con el cliente."
    )
    LOOKUP_NOT_FOUND = "No se encontró el documento {doc_number}."
    LOOKUP_ERROR = "Error al consultar documento fiscal."

    # ── Reportes — etiquetas ──────────────────────────────────
    REPORT_UNKNOWN = "Desconocido"

    REPORT_MOVEMENT_TYPES: dict[str, str] = {
        "apertura": "Apertura de Caja",
        "cierre": "Cierre de Caja",
        "venta": "Venta",
        "reserva": "Reserva",
        "adelanto": "Adelanto",
        "cobranza": "Cobranza",
        "inicial_credito": "Inicial Crédito",
        "gasto_caja_chica": "Gasto Caja Chica",
    }

    REPORT_PAYMENT_METHODS: dict[str, str] = {
        "efectivo": "Efectivo",
        "tarjeta_debito": "Tarjeta de Débito",
        "tarjeta_credito": "Tarjeta de Crédito",
        "yape": "Yape",
        "plin": "Plin",
        "transferencia": "Transferencia Bancaria",
        "billetera_digital": "Billetera Digital",
        "mixto": "Pago Mixto",
        "otro": "Otro",
        "credito": "Venta a Crédito/Fiado",
        "cheque": "Cheque",
        "no_especificado": "No Especificado",
    }

    REPORT_AGING_LABELS: dict[str, str] = {
        "current": "Vigente (no vencido)",
        "1_30": "1-30 días",
        "31_60": "31-60 días",
        "61_90": "61-90 días",
        "90_plus": "Más de 90 días",
    }

    # ── Reportes — títulos de secciones ───────────────────────
    REPORT_SUMMARY_SHEET = "Resumen Ejecutivo"
    REPORT_TITLE = "REPORTE DE VENTAS CONSOLIDADO"
    REPORT_KPI_HEADER = "INDICADORES PRINCIPALES"
    REPORT_DAILY_SHEET = "Ventas por Día"
    REPORT_DAILY_TITLE = "VENTAS DIARIAS DETALLADAS"
    REPORT_CATEGORY_SHEET = "Por Categoría"
    REPORT_CATEGORY_TITLE = "ANÁLISIS DE VENTAS POR CATEGORÍA"
    REPORT_PORTFOLIO_SHEET = "Resumen Cartera"
    REPORT_CASH_SHEET = "Resumen Caja"

    # KPI labels
    REPORT_KPI_GROSS_SALES = "Total Ventas Brutas:"
    REPORT_KPI_MARGIN = "Margen Bruto:"
    REPORT_KPI_TRANSACTIONS = "Número de Transacciones:"
    REPORT_KPI_AVG_TICKET = "Ticket Promedio:"
    REPORT_KPI_CASH_SALES = "Ventas al Contado:"
    REPORT_KPI_CREDIT_SALES = "Ventas a Crédito:"

    # Column headers
    REPORT_COL_DATE = "Fecha"
    REPORT_COL_NUM_TX = "Nº Transacciones"
    REPORT_COL_GROSS = "Venta Bruta ({currency})"
    REPORT_COL_COST = "Costo ({currency})"
    REPORT_COL_PROFIT = "Utilidad ({currency})"
    REPORT_COL_MARGIN = "Margen (%)"

    # Notes
    REPORT_NOTE_GROSS = (
        "Ventas Brutas: Importe total facturado en el período"
    )
    REPORT_NOTE_COST = "Costo de Ventas: Costo de adquisición"
    REPORT_NOTE_UNITS = "Unidades Vendidas: Cantidad total"
    REPORT_NOTE_PROFIT = "Utilidad = Venta Bruta"
    REPORT_NOTE_MARGIN = "Margen = Utilidad"

    # ── Fallbacks de display (usados en múltiples módulos) ────
    FALLBACK_UNKNOWN = "Desconocido"
    FALLBACK_UNIT = "Unidad"
    FALLBACK_NO_ROLE = "Sin rol"
    FALLBACK_NO_NUMBER = "Sin número"
    FALLBACK_NOT_SPECIFIED = "No especificado"
    FALLBACK_NO_CLIENT = "Sin cliente"
    FALLBACK_NO_CATEGORY = "Sin categoría"
    FALLBACK_NO_DETAIL = "Sin detalle"
    FALLBACK_NO_DESC = "Sin descripción"
    FALLBACK_PRODUCT = "Producto"

    # ── Acciones de caja / movimientos ────────────────────────
    ACTION_OPENING = "Apertura de caja"
    ACTION_CLOSING = "Cierre de caja"
    ACTION_SALE = "Venta"
    ACTION_INITIAL_CREDIT = "Inicial Credito"
    ACTION_INSTALLMENT_PAYMENT = "Cobro de Cuota"
    ACTION_INCOME = "Ingreso"

    # ── Alertas de stock ──────────────────────────────────────
    ALERT_CRITICAL_STOCK = "Stock Crítico"
    ALERT_LOW_STOCK = "Stock Bajo"
    ALERT_NO_STOCK = "Sin Stock"
    ALERT_OVERDUE_INSTALLMENTS = "Cuotas Vencidas"
    ALERT_OPEN_CASHBOX = "Caja Abierta"

    # ── Reportes — hojas adicionales ──────────────────────────
    REPORT_BY_SELLER_SHEET = "Por Vendedor"
    REPORT_TX_DETAIL_SHEET = "Detalle Transacciones"
    REPORT_TOP_PRODUCTS_SHEET = "Top Productos"
    REPORT_HOURLY_SHEET = "Análisis Horario"
    REPORT_VALUATION_SHEET = "Resumen Valorización"
    REPORT_INVENTORY_SHEET = "Detalle Inventario"
    REPORT_BY_CLIENT_SHEET = "Por Cliente"
    REPORT_INSTALLMENTS_SHEET = "Detalle Cuotas"
    REPORT_CASH_MOVES_SHEET = "Movimientos Caja"
    REPORT_DAILY_SALES_SHEET = "Ventas Diarias"
    REPORT_CLOSINGS_SHEET = "Cierres de Caja"
    REPORT_CAT_SALES_SHEET = "Ventas por Categoría"
    REPORT_GENERAL_CLIENT = "Cliente General"
    REPORT_PAYMENTS_SHEET = "Detalle de Cobros"
    REPORT_PAYMENTS_TITLE = "DETALLE DE COBROS E INGRESOS"
    REPORT_TOTAL_INCOME = "TOTAL INGRESOS"

    # ── Auth / Roles / Suscripción ────────────────────────────
    ROLE_SUPERADMIN = "Superadmin"
    ROLE_ADMIN = "Administrador"
    ROLE_USER = "Usuario"
    ROLE_CASHIER = "Cajero"
    ROLE_GUEST = "Invitado"

    STATUS_ACTIVE = "Activo"
    STATUS_EXPIRED = "Vencido"
    STATUS_ABOUT_TO_EXPIRE = "Por vencer"
    STATUS_PAST_DUE = "Pago vencido"
    STATUS_SUSPENDED = "Suspendido"
    STATUS_UNLIMITED = "Ilimitado"

    # ── Auth — mensajes ───────────────────────────────────────
    AUTH_USER_NOT_FOUND = "Usuario no encontrado."
    AUTH_BRANCH_INVALID = "Sucursal invalida."
    AUTH_BRANCH_NO_ACCESS = "No tiene acceso a esta sucursal."
    AUTH_BRANCH_UPDATED = "Sucursal actualizada."
    AUTH_PASSWORD_UPDATED = "Contraseña actualizada."
    AUTH_PERM_CONFIG = "No tiene permisos para configurar el sistema."

    # ── Branches — mensajes ───────────────────────────────────
    BRANCH_NAME_REQUIRED = "Ingrese el nombre de la sucursal."
    BRANCH_CREATED = "Sucursal creada."
    BRANCH_UPDATED = "Sucursal actualizada."
    BRANCH_DELETED = "Sucursal eliminada."

    # ── Cuentas / Créditos ────────────────────────────────────
    CREDIT_STATUS_PAID = "Pagado"
    CREDIT_STATUS_PARTIAL = "Parcial"
    CREDIT_STATUS_PENDING = "Pendiente"
    CREDIT_PAYMENT_REGISTERED = "Pago registrado."

    FALLBACK_CLIENT = "Cliente"
    FALLBACK_CLIENT_NOT_REGISTERED = "Cliente no registrado"
    FALLBACK_NO_DATE = "Sin fecha"
    FALLBACK_SYSTEM = "Sistema"
    FALLBACK_NO_OBS = "Sin observaciones"
    FALLBACK_NO_REFERENCE = "Sin referencia"
    FALLBACK_NO_PRODUCTS = "Sin productos"
    FALLBACK_GENERAL = "General"
    FALLBACK_SERVICES = "Servicios"

    # ── Cuentas — headers Excel ───────────────────────────────
    ACCOUNTS_INSTALLMENTS_REGISTERED = "Cuotas registradas:"
    ACCOUNTS_INSTALLMENTS_PAID = "Cuotas pagadas:"
    ACCOUNTS_INSTALLMENTS_PENDING = "Cuotas pendientes:"
    ACCOUNTS_INSTALLMENTS_OVERDUE = "Cuotas vencidas:"

    # ── Sale Service — validaciones ───────────────────────────
    SALE_VAL_PAYMENT_METHOD = "Seleccione un metodo de pago."
    SALE_VAL_COMPANY = "Empresa no definida para procesar la venta."
    SALE_VAL_BRANCH = "Sucursal no definida para procesar la venta."
    SALE_VAL_CANCELLED_RESERVATION = (
        "No se puede cobrar una reserva cancelada o eliminada."
    )
    SALE_VAL_ALREADY_PAID = "La reserva ya esta pagada."
    SALE_VAL_NO_PRODUCTS = "No hay productos en la venta."
    SALE_VAL_NO_DESCRIPTION = "Producto sin descripcion."
    SALE_VAL_INVALID_QTY = "Cantidad invalida para {description}."
    SALE_VAL_MULTI_MATCH = (
        "Producto '{description}' tiene multiples coincidencias "
        "en inventario. Use codigo de barras."
    )
    SALE_VAL_NOT_FOUND = "Producto {identifier} no encontrado en inventario."
    SALE_VAL_INVALID_PRICE = "Precio invalido para {description}."
    SALE_VAL_INSUFFICIENT_STOCK = "Stock insuficiente para {description}."
    SALE_VAL_NO_AMOUNT = "No hay importe para cobrar."
    SALE_VAL_INVALID_INITIAL = "Monto inicial invalido."
    SALE_VAL_CASH_AMOUNT = "Ingrese un monto valido en efectivo."
    SALE_VAL_MIXED_AMOUNTS = "Complete los montos del pago mixto."
    SALE_VAL_CLIENT_REQUIRED = "Cliente requerido para venta a credito."
    SALE_VAL_CLIENT_NOT_FOUND = "Cliente no encontrado."
    SALE_VAL_CREDIT_LIMIT = "Limite de credito excedido."
    SALE_VAL_INVALID_INSTALLMENTS = "Cantidad de cuotas invalida."

    SALE_ACTION_CREDIT_INITIAL = "Crédito c/ Inicial"
    SALE_ACTION_CREDIT = "Crédito"

    # ── Historial — labels de display ─────────────────────────
    HIST_FILTER_ALL = "Todos"
    HIST_FILTER_ALL_F = "Todas"  # femenino (categorías)
    HIST_SOURCE_SALE = "Venta"
    HIST_SOURCE_COLLECTION = "Cobranza"
    HIST_CREDIT_SALE = "Venta a Crédito / Fiado"
    HIST_CREDIT_COMPLETED = "Crédito (Completado)"
    HIST_CREDIT_PENDING = "Crédito (Pendiente Total)"
    HIST_PAYMENT_IN = "Pago en {method}"
    HIST_PAYMENT_REGISTERED = "Pago registrado"
    HIST_CASH_SALE = "Venta al contado"

    # Abreviaturas de métodos de pago (para tablas compactas)
    HIST_PAY_ABBR: dict[str, str] = {
        "efectivo": "Efe",
        "tarjeta_debito": "Deb",
        "tarjeta_credito": "Cre",
        "yape": "Yap",
        "plin": "Plin",
        "transferencia": "Transf",
        "mixto": "Mixto",
        "otro": "Otro",
    }

    # ── Config — defaults de métodos de pago ──────────────────
    DEFAULT_PM_CASH = "Efectivo"
    DEFAULT_PM_CASH_DESC = "Billetes, Monedas"
    DEFAULT_PM_DEBIT = "Tarjeta de Debito"
    DEFAULT_PM_DEBIT_DESC = "Pago con tarjeta debito"
    DEFAULT_PM_CREDIT = "Tarjeta de Credito"
    DEFAULT_PM_CREDIT_DESC = "Pago con tarjeta credito"
    DEFAULT_PM_YAPE = "Yape"
    DEFAULT_PM_YAPE_DESC = "Pago con Yape"
    DEFAULT_PM_PLIN = "Plin"
    DEFAULT_PM_PLIN_DESC = "Pago con Plin"
    DEFAULT_PM_TRANSFER = "Transferencia"
    DEFAULT_PM_MIXED = "Pago Mixto"
    DEFAULT_PM_MIXED_DESC = "Combinacion"

    # ── Ingreso (stock) ───────────────────────────────────────
    INGRESO_DUPLICATE_DOC = "Documento ya registrado para este proveedor."


MSG = _Messages()
