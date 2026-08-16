import shutil, subprocess, sys, time
from pathlib import Path
def test_local_scaffold_is_green_within_30_seconds(tmp_path):
    src = Path(__file__).resolve().parent.parent / "plugins/starter-kit/skills/install-wizard/local-template"
    proj = tmp_path / "proj"; shutil.copytree(src, proj)
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-local.txt"], cwd=proj, check=True)
    start = time.monotonic()
    r = subprocess.run(["sh", "scripts/run_tests.sh"], cwd=proj)
    assert r.returncode == 0
    assert time.monotonic() - start < 30
