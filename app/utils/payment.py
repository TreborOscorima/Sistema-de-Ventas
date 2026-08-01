from tuwayki_core.utils.payment import *  # noqa: F401, F403
from tuwayki_core.enums import PaymentMethodType


def wallet_method_type_scoped(provider: str) -> PaymentMethodType:
    """Variante país-agnóstica de ``wallet_method_type``.

    ``tuwayki_core.wallet_method_type`` mapea CUALQUIER billetera que no sea
    Plin a ``yape`` (heredado de una etapa Perú-céntrica). Eso hace que MODO,
    Cuenta DNI, Mercado Pago (Argentina) —y a futuro Nequi/Daviplata en
    Colombia, QR Simple en Bolivia, etc.— se registren erróneamente como Yape.

    Acá solo yape/plin van al enum específico; cualquier otra billetera
    devuelve ``other`` para que el ``payment_method_id`` se resuelva por
    nombre/ID contra la tabla ``paymentmethod`` (igual que ya hace Mercado
    Pago) y quede atribuida al método real.

    No toca ``tuwayki_core`` (librería compartida con TUWAYKIFOOD): es un
    override local de Ventas.
    """
    value = (provider or "").strip().lower()
    if "yape" in value:
        return PaymentMethodType.yape
    if "plin" in value:
        return PaymentMethodType.plin
    return PaymentMethodType.other
