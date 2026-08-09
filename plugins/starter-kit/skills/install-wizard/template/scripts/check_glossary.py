"""Check that every domain term used in the test report has a definition.

Terms are marked with corner brackets in test docstrings, so extracting them
is exact rather than a guess at Chinese word boundaries. Marking a term is
also the moment the author is forced to decide what the word means.
"""

import re
import sys
from pathlib import Path

TERM = re.compile(r"「([^「」]+)」")
DEFINITION = re.compile(r"^\*\*(.+?)\*\*\s*[:：]", re.MULTILINE)
LANGUAGE_SECTION = re.compile(r"^##\s*語言\s*$", re.MULTILINE)


def used_terms(html):
    """Every term marked with corner brackets in the report."""
    return set(TERM.findall(html))


def defined_terms(context_md):
    """Every term defined under the 語言 section of CONTEXT.md."""
    match = LANGUAGE_SECTION.search(context_md)
    if not match:
        return set()
    body = context_md[match.end():]
    next_section = re.search(r"^##\s", body, re.MULTILINE)
    if next_section:
        body = body[: next_section.start()]
    return {name.strip() for name in DEFINITION.findall(body)}


def undefined_terms(html, context_md):
    """Terms the report uses that CONTEXT.md does not define, sorted."""
    return sorted(used_terms(html) - defined_terms(context_md))


def main():
    report = Path("reports/test-report.html")
    context = Path("CONTEXT.md")
    if not report.exists():
        print("找不到測試報告，請先跑一次測試。")
        return 1
    missing = undefined_terms(
        report.read_text("utf-8"), context.read_text("utf-8") if context.exists() else ""
    )
    if missing:
        print("這些詞出現在測試報告上，但詞彙表裡沒有定義：")
        for term in missing:
            print(f"  - {term}")
        print("\n請在 CONTEXT.md 的「語言」段落補上定義，或改用已經定義過的詞。")
        return 1
    print("測試報告上的名詞都在詞彙表裡查得到。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
