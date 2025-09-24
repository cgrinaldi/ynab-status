# ynab-status

Daily email status report for [YNAB categories](https://www.ynab.com/features). It pulls your YNAB budget data, computes per-category pacing and weekly allowance, renders a clean HTML/text email, and sends it via Gmail.

This repo uses uv + pyproject.toml for dependency management and includes a GitHub Actions workflow for automated runs.

## Features

- Per-category weekly allowance based on remaining days in month
- Pacing vs. target spend (slow down / on track / could spend more)
- Clear status icons and color coding for negative balances and pacing
- HTML and plain text email output (also written to `out/` for inspection)
- Gmail API integration (OAuth) for sending mail
  - Alternatively: SMTP with Gmail App Password (no OAuth token refresh)

## Requirements

- Python `>= 3.11`
- A YNAB Personal Access Token (API key)
- Gmail OAuth credentials (`credentials.json` and a generated `token.json`)
  - Or enable SMTP with a Gmail App Password (no OAuth files needed)
- Recommended: `uv` for managing and running the project

## Quick Start

1) Install `uv` (recommended)

   - macOS / Linux:
     - `curl -LsSf https://astral.sh/uv/install.sh | sh`

2) Sync dependencies

   - `uv sync`

3) Configure environment

   - Create a `.env` file at the repo root with at least:

     ```env
     YNAB_API_KEY=your_ynab_api_key
     GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id
     ```

   - Place your Gmail OAuth client file as `credentials.json` in the repo root. The first run will perform a browser OAuth flow and write `token.json` next to it.
   - Alternate: if you set `GMAIL_APP_PASSWORD` in your environment, the app will send via Gmail SMTP and skip OAuth entirely.

4) Run locally

   - `uv run -m app.main`

   On first send, Gmail OAuth will open a browser for consent. After that, `token.json` will be reused.

## Configuration

Most knobs live in `app/main.py`.

- `app/main.py:1` — Set your budget name in `BUDGET_NAME`.
- `app/main.py:10` — Customize the `WATCHLIST` mapping of category groups → categories. You can:
  - Use exact names: `"Groceries"`
  - Use wildcards per group: `"*"` to include all categories in that group
  - Provide objects to toggle monitoring per item: `{ "name": "Gifts", "monitor": false }`
- `SOFT_WARN_THRESHOLD` — Amount below which balance shows an amber warning
- Pacing controls:
  - `PACING_ENABLED` — Toggle pacing display and status influence
  - `PACING_UPPER_OVER_PCT` — Threshold over target spend to show slow down (🐢)
  - `PACING_LOWER_UNDER_PCT` — Threshold under target spend to show could spend more (🐇)
- Email settings:
  - `SENDER` and `RECIPIENTS`
  - `DRY_RUN_WRITE_HTML` — When `True`, also writes `out/email.html` and `out/email.txt`

Environment variables are loaded via Pydantic Settings from `.env` (see `app/config.py`). Required keys:

- `YNAB_API_KEY` — Your YNAB API key
- `GOOGLE_OAUTH_CLIENT_ID` — Your OAuth client ID (used by Google libs)

Optional for SMTP (alternate transport):

- `GMAIL_APP_PASSWORD` — App Password for the sender Gmail account (2FA required)

Gmail credentials are provided via files expected by `app/mailer.py`:

- `credentials.json` — OAuth client credentials
- `token.json` — Generated automatically on the first successful auth flow

## What It Sends

`app/report.py` renders both HTML and plain text with:

- Days/weeks remaining and percent of month complete
- Budget last updated timestamp (converted to Pacific Time) and days ago
- Two sections: Monitoring and Not Monitoring, grouped by YNAB category group
- For monitored categories: budgeted, spent, balance, target-by-now, pacing, weekly allowance

## Running in GitHub Actions

A workflow is provided at `.github/workflows/ynab-uv-cron.yml`.

- Secrets you need to set in your repository settings:
  - `YNAB_API_KEY`
  - `GOOGLE_OAUTH_CLIENT_ID`
  - If using Gmail API (OAuth):
    - `GMAIL_CREDENTIALS_JSON` — Contents of your `credentials.json`
    - `GMAIL_TOKEN_JSON` — Contents of a working `token.json`
  - If using SMTP (App Password):
    - `GMAIL_APP_PASSWORD` — App Password for the `SENDER` account (see below)
- The schedule section is currently commented out. You can re-enable and adjust it for your timezone.
- The job uses `uv sync --frozen` and runs `uv run -m app.main`.

## Development Notes

Project layout:

- `app/main.py` — Orchestration and configuration
- `app/ynab_client.py` — Thin wrapper around the `ynab` SDK
- `app/domain.py` — Selection, pacing, weekly allowance, and status logic
- `app/report.py` — Jinja templating for HTML/text
- `app/mailer.py` — Gmail API send using OAuth
- `app/helpers.py` — Utility helpers

Dependencies are declared in `pyproject.toml`; a `uv.lock` is present for reproducibility.

## Troubleshooting

- Gmail auth keeps prompting: delete `token.json` and re-run to regenerate it.
- Want to avoid token refresh? Enable SMTP by creating a Gmail App Password (Google Account → Security → App passwords), set it as `GMAIL_APP_PASSWORD` secret, and remove the OAuth-secret steps in the workflow.
- No categories found: check `BUDGET_NAME` and ensure group/category names in `WATCHLIST` match your YNAB exactly.
- Timeouts with YNAB: ensure `YNAB_API_KEY` is correct and network access is available.
- Emails not received: check the Gmail account’s Sent folder and spam; verify `SENDER` and `RECIPIENTS`.

## Security

- Do not commit `.env`, `credentials.json`, or `token.json`.
- Use GitHub Secrets for CI. Rotate keys if you suspect exposure.
