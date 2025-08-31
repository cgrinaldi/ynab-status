from __future__ import annotations
from decimal import Decimal
from datetime import date
from jinja2 import Environment, BaseLoader, select_autoescape
from app.domain import elapsed_fraction

HTML_TMPL = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>YNAB Status · {{ date_str }}</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; line-height: 1.45; }
      .wrap { max-width: 900px; margin: 0 auto; padding: 16px; }
      .header { padding: 12px 16px; border-radius: 12px; background: #f5f7ff; margin-bottom: 16px; }
      .kpi { font-size: 16px; margin: 4px 0; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 8px 10px; border-bottom: 1px solid #eee; font-variant-numeric: tabular-nums; }
      th { text-align: left; font-size: 13px; color: #666; }
      .amt { text-align: right; }
      .red { color: #b00020; font-weight: 600; }
      .amber { color: #a36b00; font-weight: 600; }
      .green { color: #006400; font-weight: 600; }
      .tag { font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid #ddd; }
      .tag.red { border-color: #b00020; }
      .tag.amber { border-color: #a36b00; }
      .tag.green { border-color: #006400; }
      .foot { color: #666; font-size: 12px; margin-top: 12px; }
      /* Grouping visuals */
      .group-row th { font-size: 16px; color: #2b59c3; text-transform: none; font-weight: 700; }
      .group-row { background: #fafbff; position: sticky; top: 0; }
      .group-spacer { height: 6px; }
      /* Section bars */
      .section-bar { background: #1e3a8a; color: #ffffff; padding: 10px 14px; border-radius: 10px; font-weight: 700; margin: 20px 0 10px; }
      /* Category name emphasis */
      /* intentionally plain; group headers are emphasized */
      /* Status column: keep on one line and set width */
      .status-col { white-space: nowrap; min-width: 75px; }
      /* Category column: slightly wider for long names */
      .cat-col { min-width: 100px; }
      /* Pacing column: keep on one line and widen */
      .pacing-col { white-space: nowrap; min-width: 100px; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="header" role="region" aria-label="Summary">
        <div class="kpi"><strong>Days left:</strong> {{ days_left }} · <strong>Weeks left:</strong> {{ weeks_left }}</div>
        <div class="kpi"><em>Rationale:</em> For each category: Weekly = Remaining ÷ weeks remaining (floored to cents).</div>
        <div class="kpi"><strong>Month complete:</strong> {{ month_complete }}</div>
        <div class="kpi"><em>Pacing:</em> Target = Budget × elapsed. 🐢 if >10% over target; 🐇 if >10% under target; 🎯 otherwise.</div>
      </div>

      <div class="section-bar">Monitoring</div>
      <table role="table" aria-label="Monitoring categories status">
        <thead>
          <tr>
            <th class="cat-col">Category</th>
            <th class="status-col">Status</th>
            <th class="amt">Budgeted</th>
            <th class="amt">Amt Spent</th>
            <th class="amt">Remaining</th>
            <th class="amt">Target Spent by Now</th>
            <th class="pacing-col">Pacing</th>
            <th class="amt">Weekly Spend Remaining</th>
          </tr>
        </thead>
        <tbody>
          {% for g in groups_monitored %}
          <tr class="group-row">
            <th colspan="8">{{ g.name }}</th>
          </tr>
          {% for r in g.rows %}
          <tr>
            <td class="cat-col"><strong>{{ r.name }}</strong></td>
            <td class="status-col"><span class="tag {{ r.status_class }}">{{ r.status_icon }}</span></td>
            <td class="amt">${{ r.budgeted }}</td>
            <td class="amt">${{ r.activity }}</td>
            <td class="amt {{ r.status }}">${{ r.available }}</td>
            <td class="amt">{% if r.target_spent %}${{ r.target_spent }}{% else %}—{% endif %}</td>
            <td class="pacing-col {{ r.pacing_class }}">{{ r.pacing }}</td>
            <td class="amt">{% if r.weekly %}${{ r.weekly }}{% endif %}</td>
          </tr>
          {% endfor %}
          <tr class="group-spacer"><td colspan="8"></td></tr>
          {% endfor %}
        </tbody>
      </table>

      <div class="section-bar">Not Monitoring</div>
      <table role="table" aria-label="Not monitoring categories status">
        <thead>
          <tr>
            <th class="cat-col">Category</th>
            <th class="status-col">Status</th>
            <th class="amt">Budgeted</th>
            <th class="amt">Amt Spent</th>
            <th class="amt">Remaining</th>
            <th class="amt">Target Spent by Now</th>
            <th class="pacing-col">Pacing</th>
            <th class="amt">Weekly Spend Remaining</th>
          </tr>
        </thead>
        <tbody>
          {% for g in groups_unmonitored %}
          <tr class="group-row">
            <th colspan="8">{{ g.name }}</th>
          </tr>
          {% for r in g.rows %}
          <tr>
            <td class="cat-col"><strong>{{ r.name }}</strong></td>
            <td class="status-col"><span class="tag {{ r.status_class }}">{{ r.status_icon }}</span></td>
            <td class="amt">${{ r.budgeted }}</td>
            <td class="amt">${{ r.activity }}</td>
            <td class="amt {{ r.status }}">${{ r.available }}</td>
            <td class="amt">{% if r.target_spent %}${{ r.target_spent }}{% else %}—{% endif %}</td>
            <td class="pacing-col {{ r.pacing_class }}">{{ r.pacing }}</td>
            <td class="amt">{% if r.weekly %}${{ r.weekly }}{% endif %}</td>
          </tr>
          {% endfor %}
          <tr class="group-spacer"><td colspan="8"></td></tr>
          {% endfor %}
        </tbody>
      </table>

      {% if red_count > 0 %}
        <p class="foot">Heads up: you have {{ red_count }} category(-ies) below $0. Address these first.</p>
      {% endif %}
    </div>
  </body>
</html>"""

TEXT_TMPL = """YNAB Status · {{ date_str }}
Days left: {{ days_left }} | Weeks left: {{ weeks_left }}
Rationale: For each category: Weekly = Remaining ÷ weeks remaining (floored to cents).
Month complete: {{ month_complete }}
Pacing: Target = Budget × elapsed. 🐢 if >10% over target; 🐇 if >10% under target; 🎯 otherwise.

== Monitoring ==
{% for g in groups_monitored -%}
== {{ g.name }} ==
{% for r in g.rows %}
- {{ r.status_icon }} {{ r.name }} — Budgeted ${{ r.budgeted }} | Amt Spent ${{ r.activity }} | Remaining ${{ r.available }} | Target {{ r.target_spent if r.target_spent else "—" }} | Pacing {{ r.pacing }}{% if r.weekly %} | Weekly ${{ r.weekly }}{% endif %}
{% endfor %}

{%- endfor %}

== Not Monitoring ==
{% for g in groups_unmonitored -%}
== {{ g.name }} ==
{% for r in g.rows %}
- {{ r.status_icon }} {{ r.name }} — Budgeted ${{ r.budgeted }} | Amt Spent ${{ r.activity }} | Remaining ${{ r.available }} | Target {{ r.target_spent if r.target_spent else "—" }} | Pacing {{ r.pacing }}{% if r.weekly %} | Weekly ${{ r.weekly }}{% endif %}
{% endfor %}

{%- endfor %}
"""


def render_email_per_category(
    rows_in: list[dict], days_left: int, weeks_left: Decimal, today: date
) -> tuple[str, str]:
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape())

    red_count = sum(1 for r in rows_in if r["status"] == "red")

    # Group rows by their category group and monitor flag, preserving input order
    grouped_mon: dict[str, list[dict]] = {}
    grouped_unmon: dict[str, list[dict]] = {}
    for r in rows_in:
        is_mon = bool(r.get("monitor", True))
        if is_mon:
            grouped_mon.setdefault(r["group"], []).append(r)
        else:
            grouped_unmon.setdefault(r["group"], []).append(r)

    groups_monitored = []
    for group_name, items in grouped_mon.items():
        vm_items = []
        for r in items:
            # Hide weekly when < 7 days left or when remaining is negative
            hide_weekly = days_left < 7 or r["available"] < Decimal("0.00")
            weekly_str = "" if hide_weekly else f"{r['weekly']:.2f}"
            # Prepare display with quantization/formatting
            target_str = ""
            pacing_str = "—"
            if r.get("target_spent") is not None and r["target_spent"] > Decimal(
                "0.00"
            ):
                target_str = f"{r['target_spent']:.2f}"

            # Build pacing string if we have a status (not 'none')
            status = r.get("pacing_status", "none")
            icon = r.get("pacing_icon", "—")
            pacing_class = ""
            if status != "none":
                # $ delta for display is target - spent (inverse of stored delta)
                delta_amt = r.get("pacing_delta_amount")
                if isinstance(delta_amt, Decimal):
                    display_delta = -delta_amt
                    sign = "+" if display_delta >= Decimal("0.00") else "-"
                    delta_amt_str = f"{sign}${abs(display_delta):.2f}"
                else:
                    delta_amt_str = ""
                # Show only emoji and amount, color coded via class
                pacing_str = f"{icon} {delta_amt_str}"
                if status == "slow_down":
                    pacing_class = "red"
                elif status == "could_spend_more":
                    pacing_class = "green"

            vm_items.append(
                {
                    "name": r["name"],
                    "status": r["status"],
                    "icon": r["icon"],
                    "status_class": r.get("status_class", r["status"]),
                    "status_icon": r.get("status_icon", r["icon"]),
                    "available": f"{r['available']:.2f}",
                    "weekly": weekly_str,
                    "budgeted": f"{r['budgeted']:.2f}",
                    "activity": f"{r['activity']:.2f}",
                    "target_spent": target_str,
                    "pacing": pacing_str,
                    "pacing_class": pacing_class,
                }
            )
        groups_monitored.append({"name": group_name, "rows": vm_items})

    groups_unmonitored = []
    for group_name, items in grouped_unmon.items():
        vm_items = []
        for r in items:
            # For unmonitored, explicitly hide target/pacing/weekly regardless of thresholds
            vm_items.append(
                {
                    "name": r["name"],
                    "status": r["status"],
                    "icon": r["icon"],
                    "status_class": r.get("status_class", r["status"]),
                    "status_icon": r.get("status_icon", r["icon"]),
                    "available": f"{r['available']:.2f}",
                    "weekly": "",
                    "budgeted": f"{r['budgeted']:.2f}",
                    "activity": f"{r['activity']:.2f}",
                    "target_spent": "",
                    "pacing": "—",
                    "pacing_class": "",
                }
            )
        groups_unmonitored.append({"name": group_name, "rows": vm_items})

    month_elapsed = elapsed_fraction(today)
    ctx = {
        "date_str": today.isoformat(),
        "days_left": days_left,
        "weeks_left": f"{weeks_left:.2f}",
        "groups_monitored": groups_monitored,
        "groups_unmonitored": groups_unmonitored,
        "red_count": red_count,
        "month_complete": f"{(month_elapsed * Decimal(100)):.1f}%",
    }

    html = env.from_string(HTML_TMPL).render(**ctx)
    text = env.from_string(TEXT_TMPL).render(**ctx)
    return text, html
