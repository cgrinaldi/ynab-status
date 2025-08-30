from datetime import date
from decimal import Decimal
from pathlib import Path

from app.config import load_secrets
from app.ynab_client import YnabSDKClient
from app.domain import (
    select_categories,
    per_category_weekly_breakdown,
    days_and_weeks_remaining,
)
from app.report import render_email_per_category
from app.mailer import send_email

# ---- Quick config for a first working run ----
BUDGET_NAME = "Back in SF"
WATCHLIST = {"Household Expenses": ["Groceries", "Misc"]}  # ["*"] = all in group
SOFT_WARN_THRESHOLD = Decimal("10.00")
SENDER = "cgrinaldi@gmail.com"
RECIPIENTS = ["cgrinaldi@gmail.com"]
DRY_RUN_WRITE_HTML = True
# ------------------------------------------------


def main():
    secrets = load_secrets()
    with YnabSDKClient(secrets.YNAB_API_KEY) as ynab_client:
        budget = ynab_client.get_budget_by_name(BUDGET_NAME)
        all_cats = ynab_client.get_categories(budget.id)
        selected = select_categories(all_cats, WATCHLIST)

        today = date.today()
        rows = per_category_weekly_breakdown(
            selected, today, soft_warn=SOFT_WARN_THRESHOLD
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
