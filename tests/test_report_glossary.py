import sys

from conftest import TEMPLATE

sys.path.insert(0, str(TEMPLATE / "scripts"))
from check_glossary import defined_terms, undefined_terms, used_terms

REPORT = """<html><body>
<li>「員工」填了「可排班時段」之後，「主管」在後台看得到</li>
<li>「班表」被改過之後，查得到是誰改的</li>
</body></html>"""

CONTEXT = """# 排班

## 語言

**員工**：
需要被排班的人。
_避免_：同事、人員

**可排班時段**：
員工自己填的、他能上班的時間區間。

**主管**：
負責確認班表的人。

**班表**：
一段期間內每個員工的上班時間安排。
"""


def test_every_term_in_the_report_has_a_definition():
    """報告裡標記的領域名詞，每一個都在詞彙表找得到定義。"""
    assert undefined_terms(REPORT, CONTEXT) == []


def test_a_term_with_no_definition_is_named():
    """報告出現詞彙表沒有的詞，檢查失敗並指名是哪個詞。"""
    report = REPORT.replace("「班表」", "「排班結果」")

    assert undefined_terms(report, CONTEXT) == ["排班結果"]


def test_terms_are_read_only_from_the_language_section():
    """詞彙表的其他段落不算數，只有語言那一段裡的詞才是定義。"""
    context = CONTEXT + "\n## 其他\n\n**離職**：\n不算在詞彙表裡。\n"

    assert "離職" not in defined_terms(context)


def test_plain_prose_is_not_mistaken_for_a_term():
    """沒有用引號標記的文字不會被當成領域名詞。"""
    report = "<li>系統啟動時會寫一筆紀錄</li>"

    assert used_terms(report) == set()
