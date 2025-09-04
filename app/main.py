from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from pathlib import Path
import json
from typing import Optional

from app.config import load_secrets
from app.ynab_client import YnabSDKClient, Budget
from app.domain import (
    select_categories,
    per_category_weekly_breakdown,
    days_and_weeks_remaining,
    build_monitor_map,
)
from app.report import render_email_per_category
from app.mailer import send_email

# ---- Quick config for a first working run ----
BUDGET_NAME = "2025 Restart"
WATCHLIST = {
    "Everyday Expenses": [
        "Groceries",
        "Eating Out",
        {"name": "Gifts", "monitor": False},
        "Transportation",
        "Misc",
    ],
    "A's Expenses": [
        {"name": "Amount - A", "monitor": False},
    ],
    "C's Expenses": [
        {"name": "Amount - C", "monitor": False},
    ],
    "Savings": [
        {"name": "Inheritance", "monitor": False},
        {"name": "General", "monitor": False},
        {"name": "Vacation", "monitor": False},
    ],
    "Kids": ["Babysitting", "Fun", "Kids Misc"],
}  # ["*"] = all in group; dict entries can set monitor flags

SOFT_WARN_THRESHOLD = Decimal("10.00")
SENDER = "cgrinaldi@gmail.com"
RECIPIENTS = ["cgrinaldi@gmail.com", "allison.s.rinaldi@gmail.com"]
DRY_RUN_WRITE_HTML = True
STATE_DIR = Path(".state")
STATE_FILE = STATE_DIR / "email_state.json"
# Pacing config (to be moved to config.yaml later)
PACING_ENABLED = True
PACING_UPPER_OVER_PCT = Decimal("0.10")  # 10% over target -> Slow down 🐢
PACING_LOWER_UNDER_PCT = Decimal("0.10")  # 10% under target -> Could spend more 🐇
# ------------------------------------------------


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _load_last_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(data: dict) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def decide_should_send(budget: Budget, budget_name: str, state: dict) -> tuple[bool, str]:
    """Return whether we should send an email for this budget and a reason.

    Logic:
    - If the budget (id/name) differs from the last run → send (initialize state).
    - If YNAB has no last_modified_on → send only if never sent before.
    - Otherwise, send only if YNAB's last_modified_on is newer than stored.
    """
    state_budget_id = state.get("budget_id")
    state_budget_name = state.get("budget_name")
    state_last_mod = _parse_dt(state.get("last_budget_modified_on"))

    budget_changed = (
        state_budget_id is not None and state_budget_id != budget.id
    ) or (
        state_budget_name is not None and state_budget_name != budget_name
    )

    if budget_changed:
        return True, "Different budget than last run; initializing state and sending."

    if budget.last_modified_on is None:
        if state_last_mod is None:
            return True, "No previous state and YNAB has no modified time; sending once."
        return False, "YNAB last-modified unknown and already sent before; skipping."

    if state_last_mod is None:
        return True, "First run for this budget; sending."

    if budget.last_modified_on > state_last_mod:
        return True, "Budget updated since last notification; sending."

    return False, "No budget updates since last notification; skipping."


def build_notification_state(budget: Budget, budget_name: str) -> dict:
    now_utc = datetime.now(timezone.utc)
    return {
        "budget_id": budget.id,
        "budget_name": budget_name,
        "last_budget_modified_on": (
            budget.last_modified_on.isoformat() if budget.last_modified_on else None
        ),
        "last_notified_at": now_utc.isoformat(),
    }


def main():
    secrets = load_secrets()
    with YnabSDKClient(secrets.YNAB_API_KEY) as ynab_client:
        budget = ynab_client.get_budget_by_name(BUDGET_NAME)

        # Decide early if we should send based on prior state and budget timestamp
        state = _load_last_state()
        should_send, reason = decide_should_send(budget, BUDGET_NAME, state)
        if not should_send:
            print(reason)
            return

        # Proceed to compute the report only when we intend to send
        all_cats = ynab_client.get_categories(budget.id)
        selected = select_categories(all_cats, WATCHLIST)
        monitor_map = build_monitor_map(all_cats, WATCHLIST)

        # Use Pacific Time for all date-based logic and display
        pt = ZoneInfo("America/Los_Angeles")
        today = datetime.now(pt).date()
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
        text, html = render_email_per_category(
            rows, days_left, weeks_left, today, budget.last_modified_on
        )

        subject = f"YNAB Daily · {today.isoformat()} · Per-category weekly allowances"
        if DRY_RUN_WRITE_HTML:
            out = Path("out")
            out.mkdir(exist_ok=True)
            (out / "email.html").write_text(html, encoding="utf-8")
            (out / "email.txt").write_text(text, encoding="utf-8")
            print(f"Wrote {out / 'email.html'} and {out / 'email.txt'}")

        send_email(SENDER, RECIPIENTS, subject, text, html)
        print(f"Sent email to {', '.join(RECIPIENTS)}")

        # Persist new state after sending
        _save_state(build_notification_state(budget, BUDGET_NAME))


if __name__ == "__main__":
    main()
