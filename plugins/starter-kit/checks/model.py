from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """One line of the health report."""

    id: str
    title: str
    ok: bool
    detail: str
    hint: str = ""
