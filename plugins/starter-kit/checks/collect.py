"""Turn a facts file into the health report.

The skill gathers what the shell cannot see — whether this is local mode,
whether MCP answers, whether the browser extension is there — and writes it
into the facts file. Everything else the probes find for themselves.
"""

import json
import sys
from pathlib import Path

from .render import render_html, render_json
from .runner import run_all

USAGE = "用法：python3 -m checks.collect <facts.json 路徑> <報告輸出資料夾>"


def collect(facts_path, out_dir):
    """Read `facts_path`, run every probe, write both report forms to `out_dir`.

    Returns 0 if every probe is green, 1 if any is red — the exit code a
    caller (or a wrapper skill) can check without parsing the report.
    """
    try:
        facts = json.loads(Path(facts_path).read_text("utf-8"))
    except json.JSONDecodeError as exc:
        print(
            f"facts 檔案 {facts_path} 不是合法的 JSON，"
            f"第 {exc.lineno} 行、第 {exc.colno} 欄：{exc.msg}。"
            "請檢查這個檔案的格式，不是專案本身的問題。"
        )
        return 1
    results = run_all(facts)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "health-check.html").write_text(render_html(results), encoding="utf-8")
    (out / "health-check.json").write_text(render_json(results), encoding="utf-8")
    red = [r for r in results if not r.ok]
    for item in red:
        print(f"紅：{item.title} —— {item.detail}")
    print(f"\n{len(results)} 項裡有 {len(results) - len(red)} 項是綠的。")
    return 1 if red else 0


def main():
    """Read facts/out-dir from argv, with a usage message instead of a raw
    traceback when they are missing or the facts file does not exist —
    the same shape as `backup_snapshot.py`'s `main()`.
    """
    if len(sys.argv) < 3:
        print(USAGE)
        return 1
    facts_path = Path(sys.argv[1])
    if not facts_path.exists():
        print(f"找不到 facts 檔案：{facts_path}")
        return 1
    return collect(facts_path, sys.argv[2])


if __name__ == "__main__":
    sys.exit(main())
