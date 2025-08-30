from __future__ import annotations
from decimal import Decimal
from datetime import date
from jinja2 import Environment, BaseLoader, select_autoescape

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
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="header" role="region" aria-label="Summary">
        <div class="kpi"><strong>Days left:</strong> {{ days_left }} · <strong>Weeks left:</strong> {{ weeks_left }}</div>
        <div class="kpi"><em>Rationale:</em> For each category: Weekly = Available ÷ weeks remaining (floored to cents).</div>
      </div>

      <table role="table" aria-label="Category status">
        <thead>
          <tr>
            <th>Group / Category</th>
            <th>Status</th>
            <th class="amt">Available</th>
            <th class="amt">Weekly</th>
            <th class="amt">Budgeted</th>
            <th class="amt">Activity</th>
          </tr>
        </thead>
        <tbody>
          {% for r in rows %}
          <tr>
            <td>{{ r.group }} / <strong>{{ r.name }}</strong></td>
            <td><span class="tag {{ r.status }}">{{ r.icon }} {{ r.status }}</span></td>
            <td class="amt {{ r.status }}">${{ r.available }}</td>
            <td class="amt">${{ r.weekly }}</td>
            <td class="amt">${{ r.budgeted }}</td>
            <td class="amt">${{ r.activity }}</td>
          </tr>
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
Rationale: For each category: Weekly = Available ÷ weeks remaining (floored to cents).

{% for r in rows -%}
- {{ r.icon }} {{ r.group }} / {{ r.name }} — Avail ${{ r.available }} | Weekly ${{ r.weekly }} [{{ r.status }}]
{%- endfor %}
"""


def render_email_per_category(
    rows_in: list[dict], days_left: int, weeks_left: Decimal, today: date
) -> tuple[str, str]:
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape())

    red_count = sum(1 for r in rows_in if r["status"] == "red")
    rows = [
        {
            "group": r["group"],
            "name": r["name"],
            "status": r["status"],
            "icon": r["icon"],
            "available": f"{r['available']:.2f}",
            "weekly": f"{r['weekly']:.2f}",
            "budgeted": f"{r['budgeted']:.2f}",
            "activity": f"{r['activity']:.2f}",
        }
        for r in rows_in
    ]

    ctx = {
        "date_str": today.isoformat(),
        "days_left": days_left,
        "weeks_left": f"{weeks_left:.2f}",
        "rows": rows,
        "red_count": red_count,
    }

    html = env.from_string(HTML_TMPL).render(**ctx)
    text = env.from_string(TEXT_TMPL).render(**ctx)
    return text, html
