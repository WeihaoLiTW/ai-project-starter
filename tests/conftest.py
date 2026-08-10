import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parent.parent
PLUGIN = KIT_ROOT / "plugins" / "starter-kit"
TEMPLATE = PLUGIN / "skills" / "install-wizard" / "template"

sys.path.insert(0, str(PLUGIN))


def git(*args, cwd):
    """跑一個 git 指令，失敗就丟例外。"""
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True,
        capture_output=True, text=True,
    ).stdout


@pytest.fixture
def repo(tmp_path):
    """一個乾淨的 git repo，帶一個綠的測試與一個初始 commit。"""
    root = tmp_path / "work"
    root.mkdir()
    (root / "tests").mkdir()
    (root / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這個永遠是綠的。\"\"\"\n    assert True\n",
        encoding="utf-8",
    )
    (root / "scripts").mkdir()
    (root / "scripts" / "run_tests.sh").write_text(
        "#!/bin/sh\nexec python3 -m pytest tests/ -q \"$@\"\n", encoding="utf-8"
    )
    os.chmod(root / "scripts" / "run_tests.sh", 0o755)
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "kit@example.com", cwd=root)
    git("config", "user.name", "kit", cwd=root)
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "initial", cwd=root)
    return root


def run_hook(script_name, payload, cwd, env=None):
    """用 hook 的實際介面呼叫它：payload 走 stdin，結果走 stdout。

    `env`, if given, is merged on top of the current environment — used by
    tests that need the subprocess to see a different `PATH` or `PYTHON`
    than this test process itself has.
    """
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    proc = subprocess.run(
        [sys.executable, str(PLUGIN / "scripts" / script_name)],
        input=json.dumps(payload), cwd=cwd,
        capture_output=True, text=True, timeout=120,
        env=run_env,
    )
    out = proc.stdout.strip()
    return proc.returncode, (json.loads(out) if out else {}), proc.stderr


@pytest.fixture(scope="session")
def venv_without_pytest(tmp_path_factory):
    """A real virtualenv that has a working `python3` but no `pytest`.

    Session-scoped and built once with `--without-pip` (nothing installs
    into it, so there is nothing to speed up by recreating it per test):
    this is the actual, most common half-finished install this project's
    audience hits — a virtualenv was created, but the install step that
    puts `pytest` in it never ran or failed silently.

    Built by shelling out to the system `python3`, not by using the
    `venv` module against `sys.executable`: this test process itself runs
    inside this repo's own `.venv`, and a venv created *from* a venv can
    end up with a broken `libpython` reference — a dylib-loading crash,
    not the "No module named" text this fixture exists to produce.
    """
    venv_dir = tmp_path_factory.mktemp("no-pytest-venv") / "venv"
    subprocess.run(
        ["python3", "-m", "venv", str(venv_dir), "--without-pip"],
        check=True, capture_output=True, text=True,
    )
    return venv_dir / "bin"


@pytest.fixture
def installed_project(tmp_path):
    """把樣板複製出來、裝好依賴的一份專案。"""
    import shutil

    project = tmp_path / "proj"
    shutil.copytree(TEMPLATE, project)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r",
         str(project / "requirements.lock.txt")],
        check=True,
    )
    return project


@pytest.fixture
def prod_env():
    """一組設定正確的正式環境變數。"""
    env = dict(os.environ)
    env.update(
        DJANGO_SETTINGS_MODULE="project.settings.prod",
        DJANGO_DEBUG="0",
        DJANGO_SECRET_KEY="a-real-secret-key-generated-at-install-time-0123456789",
        DJANGO_ALLOWED_HOSTS="example.zeabur.app",
        DATA_DIR="/tmp",
    )
    return env
