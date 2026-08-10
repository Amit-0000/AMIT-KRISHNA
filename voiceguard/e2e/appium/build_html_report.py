"""Builds e2e/results/execution-report.html from e2e/results/appium_summary.json
(parse_results.py's output). Pure stdlib string templating, no Jinja/pandas —
same "no heavy deps" convention as parse_results.py, and the same navy/accent
palette used across this repo's other reports (performance/build_excel.py,
reports/build_master_test_report.py) so the QA suite's reports read as one
family regardless of format.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS_DIR = ROOT.parent / "results"  # e2e/results/, shared with parse_results.py and conftest.py's screenshots
SUMMARY_JSON = RESULTS_DIR / "appium_summary.json"
OUT_HTML = RESULTS_DIR / "execution-report.html"

NAVY = "#1F2937"
ACCENT = "#2563EB"
GREEN = "#1E7B34"
GREEN_BG = "#C6EFCE"
RED = "#9C0006"
RED_BG = "#FFC7CE"
GREY = "#6B7280"
GREY_BG = "#E5E7EB"
LIGHT_BAND = "#F3F4F6"


def esc(value) -> str:
    return html.escape(str(value))


def render_no_report(summary: dict) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>VoiceGuard — Appium Mobile-Web Report</title>
<style>body{{font-family:system-ui,sans-serif;background:{NAVY};color:#fff;padding:3rem;}}
.card{{background:{GREY_BG};color:{NAVY};border-radius:12px;padding:2rem;max-width:640px;margin:0 auto;}}</style>
</head><body>
<div class="card">
<h1>No report available</h1>
<p>{esc(summary.get("note", "No pytest-json-report was produced for this run."))}</p>
<p style="color:{GREY}">Generated: {esc(summary.get("generated_at", ""))}</p>
</div>
</body></html>"""


def module_rows(modules: list[dict]) -> str:
    rows = []
    for i, m in enumerate(modules):
        band = f"background:{LIGHT_BAND};" if i % 2 else ""
        color = GREEN if m["pass_pct"] == 100 else (RED if m["pass_pct"] < 95 else "#9C6500")
        rows.append(
            f'<tr style="{band}"><td>{esc(m["module"])}</td><td>{m["total"]}</td>'
            f'<td style="color:{GREEN}">{m["passed"]}</td>'
            f'<td style="color:{RED}">{m["failed"]}</td>'
            f'<td>{m["skipped"]}</td>'
            f'<td style="color:{color};font-weight:600">{m["pass_pct"]}%</td></tr>'
        )
    return "\n".join(rows)


def failed_rows(failed_tests: list[dict]) -> str:
    if not failed_tests:
        return f'<p style="color:{GREEN}">No failed tests.</p>'
    parts = []
    for t in failed_tests:
        safe_name = t["nodeid"].replace("/", "_").replace("::", "__").replace(" ", "_")
        shot = f"screenshots/{safe_name}.png"
        shot_link = (
            f'<a href="{esc(shot)}">screenshot</a>'
            if (RESULTS_DIR / "screenshots" / f"{safe_name}.png").exists()
            else '<span style="color:#9C6500">no screenshot captured</span>'
        )
        reason = esc(t.get("reason") or "(no failure detail captured)")
        parts.append(
            f'<div class="failure">'
            f'<div class="failure-head"><strong>{esc(t["nodeid"])}</strong> '
            f'<span style="color:{GREY}">({t["duration_s"]}s) · {shot_link}</span></div>'
            f'<pre>{reason}</pre></div>'
        )
    return "\n".join(parts)


def render(summary: dict) -> str:
    totals = summary["totals"]
    env = summary["environment"]
    pass_pct = totals["pass_pct"]
    verdict = "PASS" if pass_pct >= 95 else "WARN"
    verdict_color = GREEN if verdict == "PASS" else RED
    verdict_bg = GREEN_BG if verdict == "PASS" else RED_BG

    env_rows = "\n".join(
        f'<tr><td>{esc(k.replace("_", " ").title())}</td><td>{esc(v)}</td></tr>' for k, v in env.items()
    )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VoiceGuard — Appium Mobile-Web Execution Report</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background:{NAVY}; color:#1a1a1a; margin:0; padding:2rem 1rem; }}
  .wrap {{ max-width: 980px; margin: 0 auto; }}
  h1 {{ color:#fff; font-size:1.5rem; margin-bottom:0.25rem; }}
  .subtitle {{ color:#c7cbe0; font-size:0.85rem; margin-bottom:1.5rem; }}
  .card {{ background:#fff; border-radius:12px; padding:1.5rem; margin-bottom:1.25rem; box-shadow:0 1px 3px rgba(0,0,0,.2); }}
  .stat-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(120px,1fr)); gap:1rem; }}
  .stat {{ text-align:center; padding:0.75rem; border-radius:8px; background:{LIGHT_BAND}; }}
  .stat .n {{ font-size:1.6rem; font-weight:700; color:{NAVY}; }}
  .stat .l {{ font-size:0.75rem; color:{GREY}; text-transform:uppercase; letter-spacing:0.03em; }}
  .verdict {{ display:inline-block; padding:0.35rem 0.9rem; border-radius:999px; font-weight:700;
              background:{verdict_bg}; color:{verdict_color}; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
  th {{ background:{NAVY}; color:#fff; text-align:left; padding:0.5rem 0.75rem; }}
  td {{ padding:0.5rem 0.75rem; border-bottom:1px solid #e5e7eb; }}
  h2 {{ color:{NAVY}; font-size:1.05rem; margin-top:0; }}
  .failure {{ border:1px solid {RED_BG}; border-left:4px solid {RED}; border-radius:6px; padding:0.75rem 1rem; margin-bottom:0.75rem; }}
  .failure-head {{ margin-bottom:0.4rem; font-size:0.85rem; }}
  .failure pre {{ white-space:pre-wrap; font-size:0.75rem; color:#4b5563; margin:0; max-height:220px; overflow:auto; }}
  a {{ color:{ACCENT}; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>VoiceGuard — Appium Mobile-Web Execution Report</h1>
  <div class="subtitle">Generated {esc(summary["generated_at"])} · Android {esc(env.get("ANDROID_API_LEVEL",""))}
    ({esc(env.get("ANDROID_TARGET",""))}/{esc(env.get("ANDROID_ARCH",""))}, {esc(env.get("ANDROID_PROFILE",""))}) ·
    Appium {esc(env.get("APPIUM_VERSION",""))} · Chrome {esc(env.get("EMULATOR_CHROME_VERSION",""))}</div>

  <div class="card">
    <span class="verdict">{verdict} — {pass_pct}% pass rate</span>
    <div class="stat-grid" style="margin-top:1.25rem">
      <div class="stat"><div class="n">{totals["total"]}</div><div class="l">Total</div></div>
      <div class="stat"><div class="n">{totals["executed"]}</div><div class="l">Executed</div></div>
      <div class="stat"><div class="n" style="color:{GREEN}">{totals["passed"]}</div><div class="l">Passed</div></div>
      <div class="stat"><div class="n" style="color:{RED}">{totals["failed"]}</div><div class="l">Failed</div></div>
      <div class="stat"><div class="n">{totals["skipped"]}</div><div class="l">Skipped</div></div>
      <div class="stat"><div class="n">{summary["duration_s"]}s</div><div class="l">Duration</div></div>
    </div>
  </div>

  <div class="card">
    <h2>Module breakdown</h2>
    <table>
      <tr><th>Module</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Pass %</th></tr>
      {module_rows(summary["module_breakdown"])}
    </table>
  </div>

  <div class="card">
    <h2>Failed tests</h2>
    {failed_rows(summary["failed_tests"])}
  </div>

  <div class="card">
    <h2>Environment</h2>
    <table>{env_rows}</table>
  </div>
</div>
</body></html>"""


def main() -> None:
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    html_out = render_no_report(summary) if summary.get("status") == "NO_REPORT" else render(summary)
    OUT_HTML.write_text(html_out, encoding="utf-8")
    print("Wrote", OUT_HTML)


if __name__ == "__main__":
    main()
