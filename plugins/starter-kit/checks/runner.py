"""Run every probe, in isolation.

A probe that raises becomes a red item carrying its own error. It must never
take the report down with it: a report that fails to render is exactly the
silent skip the spec forbids.
"""

import importlib
import traceback

from .model import CheckResult

PROBE_MODULE_NAMES = (
    "environment",
    "toolchain",
    "suite",
    "safety_net",
    "history",
    "github",
    "zeabur",
    "service",
    "data",
)


def _placeholder_probe(module_name, error):
    """A stand-in for a probe module that failed to import.

    Marked with `is_placeholder = True` on the returned callable so callers
    can tell a stand-in apart from a real probe by attribute, without
    string-matching the (translatable) report text.
    """

    def probe(facts):
        return CheckResult(
            id=module_name,
            title="這一項檢查沒有載入",
            ok=False,
            detail=f"{module_name} 探針匯入失敗：{error}",
            hint=(
                "這項檢查本身沒有成功載入，所以完全沒有執行——"
                "代表這個地方目前是「沒被檢查」，不是「沒問題」。"
                "請把這則錯誤回報給維護者，修好探針本身。"
            ),
        )

    probe.is_placeholder = True
    probe.__module__ = f"checks.probes.{module_name}"
    return probe


def default_probes():
    """The nine probes, in report order.

    Each of the nine probe modules is imported individually, inside this
    function, so this module stays importable while the probes are still
    being written, one task at a time. Each import is isolated in its own
    try/except: a module that fails to import does not take the rest of the
    run down with it. Its slot is instead filled by a placeholder probe
    (see `_placeholder_probe`) that reports a red `CheckResult` naming the
    module and the import error. `default_probes()` therefore always
    returns nine callables, in the order above, even if some of the probe
    modules do not exist yet.
    """
    probes = []
    for name in PROBE_MODULE_NAMES:
        try:
            module = importlib.import_module(f".probes.{name}", package=__package__)
            probes.append(module.probe)
        except Exception as exc:  # noqa: BLE001 - containment is the point
            probes.append(_placeholder_probe(name, exc))
    return probes


def run_all(facts, probes=None):
    """Every probe's result, in order, with failures contained."""
    results = []
    for probe in probes if probes is not None else default_probes():
        try:
            results.append(probe(facts))
        except Exception as exc:  # noqa: BLE001 - containment is the point
            results.append(
                CheckResult(
                    id=getattr(probe, "__module__", "unknown").rsplit(".", 1)[-1],
                    title="這一項檢查本身壞了",
                    ok=False,
                    detail=f"{exc}\n{traceback.format_exc(limit=3)}",
                    hint="這是環境包自己的問題，不是你的專案的問題。",
                )
            )
    return results
