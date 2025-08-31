from datetime import date
from decimal import Decimal
from pathlib import Path

from app.config import load_secrets
from app.ynab_client import YnabSDKClient
from app.domain import (
    select_categories,
    per_category_weekly_breakdown,
    days_and_weeks_remaining,
    build_monitor_map,
)
from app.report import render_email_per_category
from app.mailer import send_email

# ---- Quick config for a first working run ----
BUDGET_NAME = "Back in SF"
WATCHLIST = {
    "Household Expenses": [
        "Groceries",
        {"name": "Gifts", "monitor": False},
        "Misc",
    ],
    "Quality of Life": ["Eating Out", "Vacation"],
    "A's Expenses": [
        {"name": "Amount - A", "monitor": False},
    ],
    "C's Expenses": [
        {"name": "Amount - C", "monitor": False},
    ],
    "Baby": ["Baby Misc"],
}  # ["*"] = all in group; dict entries can set monitor flags

SOFT_WARN_THRESHOLD = Decimal("10.00")
SENDER = "cgrinaldi@gmail.com"
RECIPIENTS = ["cgrinaldi@gmail.com"]
DRY_RUN_WRITE_HTML = True
# Pacing config (to be moved to config.yaml later)
PACING_ENABLED = True
PACING_UPPER_OVER_PCT = Decimal("0.10")  # 10% over target -> Slow down 🐢
PACING_LOWER_UNDER_PCT = Decimal("0.10")  # 10% under target -> Could spend more 🐇
# ------------------------------------------------


def main():
    secrets = load_secrets()
    with YnabSDKClient(secrets.YNAB_API_KEY) as ynab_client:
        budget = ynab_client.get_budget_by_name(BUDGET_NAME)
        all_cats = ynab_client.get_categories(budget.id)
        selected = select_categories(all_cats, WATCHLIST)
        monitor_map = build_monitor_map(all_cats, WATCHLIST)

        today = date.today()
        rows = per_category_weekly_breakdown(
            selected,
            today,
            soft_warn=SOFT_WARN_THRESHOLD,
            pacing_enabled=PACING_ENABLED,
            pacing_upper_over_pct=PACING_UPPER_OVER_PCT,
            pacing_lower_under_pct=PACING_LOWER_UNDER_PCT,
            monitor_map=monitor_map,
        )
        days_left, weeks_left = days_and_weeks_remaining(today)
        text, html = render_email_per_category(rows, days_left, weeks_left, today)

        subject = f"YNAB Daily · {today.isoformat()} · Per-category weekly allowances"
        if DRY_RUN_WRITE_HTML:
            out = Path("out")
            out.mkdir(exist_ok=True)
            (out / "email.html").write_text(html, encoding="utf-8")
            (out / "email.txt").write_text(text, encoding="utf-8")
            print(f"Wrote {out / 'email.html'} and {out / 'email.txt'}")

        send_email(SENDER, RECIPIENTS, subject, text, html)
        print(f"Sent email to {', '.join(RECIPIENTS)}")


if __name__ == "__main__":
    main()
