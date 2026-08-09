"""Render the health report for a person and for a script."""

import html
import json


def render_json(results):
    """The machine-readable form. Tests assert on this, not on the HTML."""
    return json.dumps(
        [
            {"id": r.id, "title": r.title, "ok": r.ok, "detail": r.detail, "hint": r.hint}
            for r in results
        ],
        ensure_ascii=False,
        indent=2,
    )


def render_html(results):
    """The form a non-technical reader opens."""
    red = [r for r in results if not r.ok]
    rows = []
    for r in results:
        mark = "綠" if r.ok else "紅"
        colour = "#2f7d32" if r.ok else "#c62828"
        extra = f"<br><small>{html.escape(r.hint)}</small>" if r.hint else ""
        rows.append(
            f'<tr><td style="color:{colour};font-weight:600">{mark}</td>'
            f"<td>{html.escape(r.title)}</td>"
            f"<td>{html.escape(r.detail)}{extra}</td></tr>"
        )
    headline = "全部都好了。" if not red else f"有 {len(red)} 項要處理。"
    return (
        '<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
        "<title>環境健檢</title></head><body>"
        f"<h1>環境健檢</h1><p>{headline}</p>"
        '<table border="1" cellpadding="6">'
        "<tr><th>狀態</th><th>檢查項目</th><th>結果</th></tr>"
        + "".join(rows)
        + "</table></body></html>"
    )
