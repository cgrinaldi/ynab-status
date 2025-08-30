from loguru import logger
from datetime import date
from decimal import Decimal, ROUND_FLOOR
from typing import TypedDict, Optional
from app.ynab_client import Category
from app.helpers import mu_to_decimal


def select_categories(
    all_categories: list[Category],
    categories_to_select: dict[str, list[str]],
) -> list[Category]:
    if not categories_to_select:
        return []

    groups: dict[str, list[Category]] = {}
    for c in all_categories:
        groups.setdefault(c.group_name, []).append(c)

    selected: dict[str, Category] = {}

    for group_name, cat_names in categories_to_select.items():
        group_cats = groups.get(group_name, [])
        if not group_cats:
            logger.warning(f"No matching category group for '{group_name}'")
            continue

        if not cat_names or (len(cat_names) == 1 and cat_names[0] == "*"):
            for c in group_cats:
                selected[c.id] = c
            continue

        for cat_name in cat_names:
            matches = [c for c in group_cats if c.name == cat_name]
            if not matches:
                logger.warning(
                    f"No matching category '{cat_name}' in group '{group_name}'"
                )
                continue
            for c in matches:
                selected[c.id] = c

    return list(selected.values())


def status_for_available(
    amount_dec: Decimal, soft_warn: Decimal = Decimal("10.00")
) -> tuple[str, str]:
    """Return (status, symbol) given the available balance.

    - Red ❗ if < 0
    - Amber ⚠️ if < soft_warn
    - Green ✅ otherwise
    """
    if amount_dec < Decimal("0.00"):
        return "red", "❗"
    if amount_dec < soft_warn:
        return "amber", "⚠️"
    return "green", "✅"


def days_and_weeks_remaining(today: date) -> tuple[int, Decimal]:
    """Inclusive of today: days_remaining = (last_day_of_month - today + 1); weeks = days/7."""
    from calendar import monthrange

    last_day = monthrange(today.year, today.month)[1]
    days_remaining = (date(today.year, today.month, last_day) - today).days + 1
    # guard against divide-by-zero
    weeks_remaining = (Decimal(days_remaining) / Decimal(7)).max(Decimal("0.0001"))
    return days_remaining, weeks_remaining


def elapsed_fraction(today: date) -> Decimal:
    from calendar import monthrange
    days_in_month = monthrange(today.year, today.month)[1]
    # Inclusive of today
    return (Decimal(today.day) / Decimal(days_in_month)).quantize(Decimal("0.0001"))


class PacingResult(TypedDict):
    target_spent: Decimal
    delta_amount: Decimal  # spent - target
    delta_pct: Optional[Decimal]  # (spent - target) / target; None if target == 0
    status: str  # "slow_down" | "could_spend_more" | "on_track" | "none"
    icon: str  # "🐢" | "🐇" | "🎯" | "—"


def compute_pacing(
    budgeted: Decimal,
    activity: Decimal,  # YNAB activity, typically negative for outflows
    elapsed: Decimal,
    upper_over_pct: Decimal,  # e.g., Decimal("0.10")
    lower_under_pct: Decimal,  # e.g., Decimal("0.10")
) -> PacingResult:
    if budgeted <= Decimal("0.00"):
        return {
            "target_spent": Decimal("0.00"),
            "delta_amount": Decimal("0.00"),
            "delta_pct": None,
            "status": "none",
            "icon": "—",
        }

    spent = (-activity)  # activity is negative for spend
    target = (budgeted * elapsed)
    delta = (spent - target)
    delta_pct: Optional[Decimal] = None
    if target > Decimal("0.00"):
        delta_pct = (delta / target)

    # Threshold checks
    # Overspending relative to target => slow down
    if target > Decimal("0.00") and spent > (target * (Decimal("1.0") + upper_over_pct)):
        status, icon = "slow_down", "🐢"
    # Underspending relative to target => could spend more
    elif target > Decimal("0.00") and spent < (target * (Decimal("1.0") - lower_under_pct)):
        status, icon = "could_spend_more", "🐇"
    else:
        status, icon = "on_track", "🎯"

    return {
        "target_spent": target,
        "delta_amount": delta,
        "delta_pct": delta_pct,
        "status": status,
        "icon": icon,
    }


def per_category_weekly_breakdown(
    categories: list[Category],
    today: date,
    soft_warn: Decimal = Decimal("10.00"),
    pacing_enabled: bool = True,
    pacing_upper_over_pct: Decimal = Decimal("0.10"),
    pacing_lower_under_pct: Decimal = Decimal("0.10"),
) -> list[dict[str, str | Decimal]]:
    """
    For each category:
      weekly = floor((available / weeks_remaining), 2)
    Returns list of dicts for reporting.
    """
    _, weeks_rem = days_and_weeks_remaining(today)

    out: list[dict[str, str | Decimal]] = []
    for c in categories:
        av_dec = mu_to_decimal(c.available_mu)
        weekly = (av_dec / weeks_rem).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
        status, icon = status_for_available(av_dec, soft_warn=soft_warn)
        budgeted_dec = mu_to_decimal(c.budgeted_mu)
        activity_dec = mu_to_decimal(c.activity_mu)
        if pacing_enabled:
            elapsed = elapsed_fraction(today)
            pacing = compute_pacing(
                budgeted=budgeted_dec,
                activity=activity_dec,
                elapsed=elapsed,
                upper_over_pct=pacing_upper_over_pct,
                lower_under_pct=pacing_lower_under_pct,
            )
        else:
            pacing = {
                "target_spent": Decimal("0.00"),
                "delta_amount": Decimal("0.00"),
                "delta_pct": None,
                "status": "none",
                "icon": "—",
            }

        out.append(
            {
                "id": c.id,
                "group": c.group_name,
                "name": c.name,
                "available": av_dec,
                "budgeted": budgeted_dec,
                "activity": activity_dec,
                "weekly": weekly,
                "status": status,
                "icon": icon,
                # pacing fields
                "target_spent": pacing["target_spent"],
                "pacing_status": pacing["status"],
                "pacing_icon": pacing["icon"],
                "pacing_delta_amount": pacing["delta_amount"],
                "pacing_delta_pct": pacing["delta_pct"],
            }
        )
    return out
