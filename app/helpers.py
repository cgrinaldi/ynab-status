from decimal import Decimal, ROUND_FLOOR


def mu_to_decimal(mu: int) -> Decimal:
    # Milliunits -> currency (keep Decimal; round only for display)
    return (Decimal(mu) / Decimal(1000)).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
