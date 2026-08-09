r"""Compare a batch of questions against the forbidden list.

The list is deliberately narrow. A rule that flags an ordinary business
question is worse than no rule, because it trains everyone to ignore the
output.

forbidden-questions.md is a markdown table meant to be read by humans, so its
"判定樣式" column holds a plain keyword list separated by the ideographic
comma `、` rather than a regex. A markdown table cell cannot contain a literal
`|` without escaping it to `\|`, but `\|` inside a regex means "a literal pipe
character", not "or" -- so a pipe-joined alternation cannot live inside a
table cell without silently breaking. Keeping the column as a keyword list
sidesteps the clash entirely: load_rules() below does the escaping and joins
the keywords into a real alternation for re.search.
"""

import re
from dataclasses import dataclass
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parent.parent / "behavior" / "forbidden-questions.md"
ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", re.M)
KEYWORD_SEP = "、"


@dataclass(frozen=True)
class Rule:
    category: str
    pattern: str
    why: str
    ask_instead: str


def load_rules(path=RULES_FILE):
    """Read the forbidden list from its markdown table.

    Each row's keyword list is escaped keyword-by-keyword and joined with a
    real `|`, so the resulting `Rule.pattern` is ready to hand straight to
    `re.search` -- the table itself never has to contain a raw regex.
    """
    text = Path(path).read_text("utf-8")
    rules = []
    for category, keywords_cell, why, ask_instead in ROW.findall(text):
        keywords = [k.strip() for k in keywords_cell.split(KEYWORD_SEP) if k.strip()]
        pattern = "|".join(re.escape(k) for k in keywords)
        rules.append(Rule(category=category, pattern=pattern, why=why, ask_instead=ask_instead))
    return rules


def forbidden_hits(text, rules):
    """Rules this text trips, in list order."""
    return [rule for rule in rules if re.search(rule.pattern, text, re.IGNORECASE)]
