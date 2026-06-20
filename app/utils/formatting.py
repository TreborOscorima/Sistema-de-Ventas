from tuwayki_core.utils.formatting import *  # noqa: F401, F403


def fmt_price(v) -> str:
    """Format a monetary value for display: always 2 decimal places.
    3.2->'3.20', 10.0->'10.00', 21.3->'21.30', 9.33->'9.33'
    """
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def fmt_input_num(v) -> str:
    """Format a numeric value for form inputs: strip trailing zeros.
    10.0->'10', 9.5->'9.5', 3.14->'3.14'
    """
    try:
        f = float(v)
        if f == int(f):
            return str(int(f))
        return f"{f:g}"
    except (TypeError, ValueError):
        return "0"
