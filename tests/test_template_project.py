import os
import shutil
import subprocess
import sys
import time

from conftest import TEMPLATE


def test_fresh_project_suite_is_green_within_30_seconds(tmp_path):
    """剛從樣板建立的專案，第一次跑測試就全綠，且 30 秒內跑完。"""
    project = tmp_path / "proj"
    shutil.copytree(TEMPLATE, project)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r",
         str(project / "requirements.lock.txt")],
        check=True,
    )

    # Force run_tests.sh to use the same interpreter the dependencies were
    # just installed into, instead of whatever "python3" happens to be
    # first on PATH (which may be an unrelated, dependency-less install).
    env = dict(os.environ, PYTHON=sys.executable)

    started = time.monotonic()
    proc = subprocess.run(
        ["sh", "scripts/run_tests.sh"], cwd=project,
        capture_output=True, text=True, env=env,
    )
    elapsed = time.monotonic() - started

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert elapsed < 30, f"跑了 {elapsed:.1f} 秒"
