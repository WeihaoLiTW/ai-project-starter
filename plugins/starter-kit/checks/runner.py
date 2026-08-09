"""Run every probe, in isolation.

A probe that raises becomes a red item carrying its own error. It must never
take the report down with it: a report that fails to render is exactly the
silent skip the spec forbids.
"""

import traceback

from .model import CheckResult


def default_probes():
    """The nine probes, in report order.

    Imported inside the function so this module stays importable while the
    probes are still being written, one task at a time.
    """
    from .probes import (
        data, environment, github, history, safety_net, service, suite, toolchain, zeabur,
    )

    return [
        environment.probe,
        toolchain.probe,
        suite.probe,
        safety_net.probe,
        history.probe,
        github.probe,
        zeabur.probe,
        service.probe,
        data.probe,
    ]


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
