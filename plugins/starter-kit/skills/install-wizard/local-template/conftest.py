"""Render the test run as a Chinese HTML report.

The report lists what the system promises to do, taken from each test's
docstring. Test function names stay in English; the docstring is the part a
non-technical reader sees.
"""

import html
from pathlib import Path

REPORT = Path("reports/test-report.html")

_docs = {}
_results = []


def pytest_itemcollected(item):
    _docs[item.nodeid] = (item.function.__doc__ or "").strip()


def pytest_runtest_logreport(report):
    if report.when != "call":
        return
    _results.append((report.nodeid, report.passed))


def pytest_sessionfinish(session, exitstatus):
    rows = []
    for nodeid, passed in _results:
        doc = _docs.get(nodeid, "")
        mark = "通過" if passed else "沒過"
        colour = "#2f7d32" if passed else "#c62828"
        rows.append(
            f'<tr><td style="color:{colour}">{mark}</td>'
            f"<td>{html.escape(doc) or html.escape(nodeid)}</td></tr>"
        )
    total = len(_results)
    failed = sum(1 for _, passed in _results if not passed)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "<!DOCTYPE html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\">"
        "<title>測試報告</title></head><body>"
        "<h1>這個系統保證會做的事</h1>"
        f"<p>共 {total} 項，沒過 {failed} 項。</p>"
        '<table border="1" cellpadding="6">' + "".join(rows) + "</table>"
        "</body></html>",
        encoding="utf-8",
    )
