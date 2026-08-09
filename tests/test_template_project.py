import os
import re
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


# --- Behavior Tests / B5：部署後資料不會消失（結構部分） -------------------
#
# 執行期的「重新部署後資料還在」需要真的部署一次，列在人工清單。這裡驗的是
# 能自動檢查的部分：資料庫檔案的路徑，跟 zeabur.yaml 實際掛載的 volume 目錄，
# 是不是同一個路徑。三個環節（Dockerfile 的 ENV、settings 讀的環境變數、
# zeabur.yaml 掛載的目錄）只要有一個對不上，容器重開後 SQLite 檔案就會消失。


def _declared_volumes(zeabur_text):
    """從 zeabur.yaml 抓出所有 volume 宣告的 (id, 掛載目錄)。

    只認「id: 後面緊接著 dir:」這個形狀——那是 volume 項目的樣子；port 項目
    的 id 後面接的是 port:，不會被誤抓進來（zeabur.yaml 的 ports 區塊也有
    `id: web`，用「找所有 id:」的寫法會把它跟 volume 的 id 混在一起）。
    """
    lines = zeabur_text.splitlines()
    volumes = []
    for i, line in enumerate(lines):
        id_match = re.match(r"\s*-\s*id:\s*(\S+)", line)
        if not id_match or i + 1 >= len(lines):
            continue
        dir_match = re.match(r"\s*dir:\s*(\S+)", lines[i + 1])
        if dir_match:
            volumes.append((id_match.group(1), dir_match.group(1)))
    return volumes


def test_database_file_lives_under_a_mounted_volume():
    """正式環境的 SQLite 檔案位置,跟 zeabur.yaml 掛載的 volume 是同一個目錄。

    期望值來源：docs/superpowers/plans/2026-08-09-starter-kit.md 的
    B5（「資料庫檔案路徑落在有掛載的 volume 底下」）與
    probes/volume-check 的實測結果（無 volume 的目錄，資料活不過下次部署）。
    """
    dockerfile = (TEMPLATE / "Dockerfile").read_text("utf-8")
    base_settings = (TEMPLATE / "project" / "settings" / "base.py").read_text("utf-8")
    zeabur = (TEMPLATE / "zeabur.yaml").read_text("utf-8")

    # 環扣一：Dockerfile 用 ENV 把 DATA_DIR 設成一個具體路徑。
    env_match = re.search(r"DATA_DIR=(\S+)", dockerfile)
    assert env_match, "Dockerfile 沒有用 ENV 設定 DATA_DIR"
    container_data_dir = env_match.group(1)

    # 環扣二：Django settings 從同一個環境變數名稱讀 DATA_DIR,而且拿去組
    # 資料庫檔案的實際路徑,不是讀了卻沒用上。
    assert re.search(r'os\.environ\.get\(\s*["\']DATA_DIR["\']', base_settings), (
        "settings 沒有從 DATA_DIR 環境變數讀取資料目錄"
    )
    assert re.search(r'["\']NAME["\']\s*:\s*DATA_DIR\s*/', base_settings), (
        "資料庫檔案路徑沒有掛在 DATA_DIR 底下"
    )

    # 環扣三:zeabur.yaml 掛載的 volume 目錄,要跟 Dockerfile 設定的
    # DATA_DIR 是同一個路徑。兩個服務都要對得上,任何一個掛到別的路徑,
    # 該服務容器重開後資料就會不見。
    declared_dirs = {dir_ for _id, dir_ in _declared_volumes(zeabur)}
    assert declared_dirs, "zeabur.yaml 沒有宣告任何 volume"
    assert declared_dirs == {container_data_dir}, (
        f"zeabur.yaml 宣告的掛載目錄 {declared_dirs} 跟 Dockerfile 的 "
        f"DATA_DIR={container_data_dir} 對不上,資料活不過下一次部署"
    )


def test_the_two_environments_do_not_share_a_volume():
    """staging 與 prod 各自宣告獨立的 volume id,不會共用同一份資料。

    期望值來源：docs/superpowers/plans/2026-08-09-starter-kit.md 的
    B8（「兩個環境的資料庫檔案路徑與 volume 各自獨立」）。
    """
    zeabur = (TEMPLATE / "zeabur.yaml").read_text("utf-8")
    ids = [vol_id for vol_id, _dir in _declared_volumes(zeabur)]

    assert len(ids) == 2, f"預期兩個服務各宣告一個 volume,實際抓到:{ids}"
    assert len(ids) == len(set(ids)), f"volume id 重複:{ids}"
