# 非技術新手 Claude 環境包 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做出一個 Cowork plugin 加一份 Django 樣板，讓非技術者把一段話貼進 Claude 之後，得到一個行為對、環境備妥、能開始做真服務的工作環境。

**Architecture:** 這個 repo 同時是 plugin marketplace 與 plugin 本體。plugin 帶三個 hook（開場注入、密鑰擋門、綠才 commit）、四個 skill（安裝嚮導、環境健檢、想清楚再做、部署），以及一份 Django 樣板。樣板被安裝嚮導複製到使用者的工作資料夾，推上 GitHub，由 Zeabur 部署成 staging 與 prod 兩個環境。健檢的九項探針各自獨立、互不影響，任一項壞掉其餘照常出結果。

**Tech Stack:** Python 3.10（Cowork VM 實測版本）、Django 5.2 LTS、SQLite、gunicorn、Docker、Zeabur、GitHub Actions。plugin 的 hook 與 check 腳本一律純標準庫。

## Global Constraints

每個 task 的要求都隱含包含這一段。

- **Python 下限 3.10。** Cowork 本機 VM 實測為 Python 3.10.12，樣板必須在 3.10 上跑得起來。
- **kit 自己的測試一律用 repo 根目錄的 `.venv/bin/python` 跑，不要用系統的 `python3`。**
  開發機的系統 Python 可能舊到裝不了 Django 5.2（實際遇到 3.9.6），那會讓樣板的測試
  以一個跟真正原因無關的錯誤失敗。建立方式：`uv venv --python 3.10 .venv`。
- **Django 版本為 5.2 LTS**，安全支援至 2028-04，支援 Python 3.10–3.14。`requirements.txt` 寫 `Django>=5.2,<6.0`。
- **hook 與 check 腳本只准用 Python 標準庫。** 這些東西在 pip 裝壞掉、網路不通、venv 沒啟動的情況下都必須能跑。一個依賴都不能加。
- **樣板的測試套件執行時間 < 30 秒**（spec 成功定義 #2）。
- **檔名一律 ASCII，內容用繁中。** 沙箱是 Linux、主機可能是 Windows，中文檔名在跨檔案系統掛載上是已知的故障來源。
- **樣板必須帶 `.gitattributes` 強制 LF**（spec 已知限制 7）。
- **第三方元件鎖版本，不用 `latest`**（spec 寫死的預設）。Docker base image 鎖到 minor，Python 依賴鎖進 `requirements.lock.txt`。
- **volume 必須在第一次啟動前掛好**（spec 寫死的預設，探針實測）。
- **備份用 `VACUUM INTO`，不得直接複製檔案**（spec 寫死的預設、ADR-5）。`VACUUM INTO` 需要 SQLite ≥ 3.27.0，且目標檔必須不存在或為空檔，否則報錯。備份後必須跑 `PRAGMA integrity_check`，因為官方明講中斷會產出損毀但看似正常的檔案。
- **`DEBUG` 與 `SECRET_KEY` 一律從環境變數讀**（spec 寫死的預設）。
- **skill 的 frontmatter 只用 `name` 與 `description`。** Cowork 只保證支援 Agent Skills 開放 spec 的欄位；`disable-model-invocation` 這類 Claude Code 專屬欄位在 Cowork 不保證生效，不得依賴。
- **plugin 目錄規則**：`.claude-plugin/` 底下只放 `plugin.json`，`hooks/`、`skills/`、`agents/`、`.mcp.json` 一律放 plugin 根目錄。放錯會被靜默忽略。
- **語言**：程式碼識別字、註解、commit message、workflow 檔用英文；使用者看得到的文字（skill 內文、報告、錯誤訊息、CONTEXT.md）用繁中白話。
- **測試函式名用英文，docstring 用繁中。** 報告渲染的是 docstring，所以兩邊都滿足。
- **公開 repo 不得存放任何 secret。** 公開換來的是無限 CI 分鐘數，代價是任何密鑰外洩即為公開。

## 三個沒有官方答案、必須靠實測的假設

Cowork 官方文件在 hooks schema、marketplace schema、plugin.json 欄位三處都寫「格式與 Claude Code 共用」，自己沒有獨立完整的規格頁。以下三件事查不到 Cowork 官方確認：

| 假設 | 壞掉會怎樣 | 本計畫的處置 |
|---|---|---|
| hook 事件在 Cowork VM 內全部會觸發 | 三道保命繩全部靜默失效，使用者以為有保護 | 健檢第 4 項「保命繩通電」用 canary 實際驗證三個 hook 有跑，不是驗它有沒有安裝 |
| `${CLAUDE_PLUGIN_ROOT}` 在 VM 內能正確展開 | hook 找不到腳本 | hooks.json 用該變數，腳本開頭自檢並印出明確錯誤；健檢第 4 項會抓到 |
| skill 能讀取自己目錄底下的附帶檔案 | 安裝嚮導複製不到樣板 | 樣板放在 `skills/install-wizard/template/`，以 SKILL.md 的相對路徑引用，不靠環境變數 |

**這三項不是「之後再說」，是第一個 task 就要在真的 Cowork 上驗掉的東西。** 驗不過就要改設計，而不是繼續往上疊。

## Traceability（spec 成功條件 → 行為分段 → 測試）

| spec 條件 | 行為分段 | 測試檔 | 測試數 | 自動化程度 |
|---|---|---|---|---|
| 1 健檢 9 項全綠 | B11 健檢每項獨立紅燈 | `test_health_check.py` | 3 | 邏輯自動；真的全綠需人工 |
| 2 pytest 全綠 < 30 秒 | B1 新專案一建立就有綠的基準 | `test_template_project.py` | 1 | 自動 |
| 3 GitHub repo + Actions 成功 | B16 GitHub 那邊真的有東西 | — | 0 | **人工** |
| 4 staging/prod 皆 200 | B8 兩個環境各自活著 | `test_template_project.py` | 1 | 設定隔離自動；連線需人工 |
| 5 寫入 → 重新部署 → 資料仍在 | B5 部署後資料不會消失 | `test_template_project.py` | 1 | 掛載結構自動；重新部署需人工 |
| 6 prod DEBUG/SECRET_KEY/ALLOWED_HOSTS | B7 正式環境不帶開發設定上線 | `test_prod_settings.py` | 4 | 自動 |
| 7 備份 Release 中的 SQLite 可開且含該筆 | B6 備份拿得回來 | `test_backup.py` | 5 | 快照與清理自動；取出與上傳需人工 |
| 8 任意 commit checkout 後 pytest 綠 | B2 紅的時候不 commit、B3 歷史任一點都能跑 | `test_safety_net.py`（5）、`test_health_check.py`（3） | 8 | 自動 |
| 9 禁問清單命中 0、業務問題 ≥ 1 | B12 模糊需求換來業務問題 | `test_question_audit.py` | 4 | 比對器自動；輸入需人工 |
| 10 報告名詞 100% 有定義 | B13 測試報告上的詞都查得到 | `test_report_glossary.py` | 4 | 自動 |
| 11 清空記憶後不重問已記錄決策 | B14 換一個 session 也接得上 | — | 0 | **人工** |
| 12 走查記錄動用文件外知識 = 0 | B15 文件自己走得完 | — | 0 | **人工** |
| 13 健檢指名 Zeabur 路徑並實測一次 | B10 健檢說得出走哪條路 | `test_health_check.py` | 5 | 判定邏輯自動；實際操作需人工 |
| （保命繩，非編號條件） | B4 密鑰擋在 commit 之外 | `test_safety_net.py` | 3 | 自動 |
| （測試設計，非編號條件） | B9 CI 跑的是 local 的超集 | `test_ci_superset.py` | 3 | 自動 |
| （Global Constraint，非編號條件） | B17 hook 不會中斷使用者的操作 | `test_hook_payload.py` | 8 | 自動 |

合計 50 個測試函式；其中密鑰那個是參數化的，實際跑出 55 個案例。

**Gate A 覆蓋**：13 條成功條件，每條都對到至少一個行為分段；11 條有自動測試，另 2 條（#3、#11）純人工，已列在人工清單。
**Gate B 溯源**：每組測試底下都附一行「期望值來源」，指出數字或字串取自 spec 哪一段、或哪一份實測紀錄。

## 功能行為分段

每一段是一個可觀察的能力單元，刻意不跟 task 一對一 —— B2 橫跨 task 10 與 task 2，B5 橫跨 task 4 與 task 2，那正是它存在的理由。

**B1 新專案一建立就有綠的基準**（條件 2）
從樣板建立的專案，第一次跑測試就全綠，且 30 秒內跑完。不會出現「還沒有測試所以無法判斷」的空窗。

**B2 測試紅的時候不會產生 commit**（條件 8）
改動讓測試變紅 → 對話結束後 git 歷史沒有新 commit，改動仍留在工作區，且 Claude 收到「先修好」的回饋。測試綠 → 對話結束後多一個 commit。

**B3 歷史上任一點都是能跑的版本**（條件 8）
從 git 歷史任取一個 commit checkout 出來，測試皆為綠。

**B4 密鑰擋在 commit 之外**（保命繩）
嘗試寫入 `.env` 或私鑰檔 → 被擋下並說明原因。工作區有未追蹤的 `.env` → 自動 commit 不會納入它。

**B5 部署後資料不會消失**（條件 5）
資料庫檔案落在有掛載的 volume 路徑底下，且 volume 在第一次啟動前就宣告好。在正式環境寫入一筆資料、觸發重新部署，該筆資料仍讀得到。

**B6 備份拿得回來**（條件 7）
備份產出的檔案能被 `sqlite3` 開啟、通過完整性檢查、且含備份當下的那筆資料。備份存放在不是任何人都下載得到的地方。超過 3 個月的備份會被清掉。

**B7 正式環境不會帶著開發設定上線**（條件 6）
正式環境的 `DEBUG` 為 `False`、`SECRET_KEY` 不等於樣板預設值、`ALLOWED_HOSTS` 不含 `*`。樣板預設值原封不動就要部署 → 被擋下並指名是哪一項。

**B8 兩個環境各自活著且互不干擾**（條件 4）
staging 與 prod 各自的網址皆回 200。兩個環境的資料庫檔案路徑與 volume 各自獨立，在一邊寫入不會出現在另一邊。

**B9 CI 跑的是 local 的超集**（測試設計）
CI 執行的測試指令與本機是同一個入口，多出來的部分只能是非得真實部署才驗得了的東西。不會出現「我這邊都綠的，為什麼 CI 紅了」。

**B10 健檢說得出 Zeabur 走哪條路**（條件 13）
三條路徑（CLI／MCP／瀏覽器）任一可用 → 報告指名該條。多條可用 → 依 CLI > MCP > 瀏覽器排序取用。三條皆不可用 → 紅燈並說明原因，不靜默略過。

**B11 健檢每一項都會獨立紅燈**（條件 1）
任一項條件不滿足 → 該項紅燈、其餘項不受影響、報告仍完整產出。某一項的探針拋例外 → 該項紅燈並帶出例外訊息，不會讓整份報告掛掉。

**B12 模糊需求換來的是業務問題**（條件 9）
給一句模糊需求 → 提出的問題裡落在禁問清單上的數量為 0，且至少一個是業務規則問題。技術決策底下沒有業務取捨 → 直接決定並留下 ADR，不問使用者。

**B13 測試報告上的詞都查得到定義**（條件 10）
測試報告裡標記為領域名詞的詞，100% 在 `CONTEXT.md` 找得到定義。出現沒有定義的詞 → 檢查失敗並指名是哪個詞。

**B14 換一個 session 也接得上**（條件 11）
清空記憶後開新 session，已記錄於 `CONTEXT.md` 或 `docs/adr/` 的決策，重問次數為 0。

**B15 文件自己走得完**（條件 12）
照文件從零走完安裝，動用文件外知識的次數為 0。

**B16 GitHub 那邊真的有東西**（條件 3）
安裝完成後 GitHub 有對應 repo，且 Actions 至少一次結論為 success。

**B17 hook 不會中斷使用者的操作**（Global Constraint）
不管 stdin 送進來什麼——空的、壞掉的 JSON、不是 UTF-8 的位元組、合法但不是物件的
JSON——hook 都要正常結束，寫 stderr 可以，拋例外不行。密鑰擋門掛在 `Write|Edit` 上，
它一崩潰，使用者這一次的檔案編輯就跟著死。

## 檔案結構

```
.claude-plugin/
  marketplace.json                    # 讓這個 repo 變成 marketplace

plugins/starter-kit/
  .claude-plugin/plugin.json          # 只有這個檔案能放在 .claude-plugin 底下
  hooks/hooks.json                    # 三個 hook 的註冊
  scripts/
    _shared.py                        # hook 共用：讀 payload、輸出、跑指令、找 repo 根
    session_start.py                  # 開場注入三支柱
    guard_secrets.py                  # 密鑰擋門
    commit_if_green.py                # 綠才 commit
  behavior/
    pillars.md                        # 三支柱文字，session_start.py 讀它
    forbidden-questions.md            # 禁問清單，機器可讀
  checks/
    __init__.py
    model.py                          # CheckResult 與 Probe 型別
    runner.py                         # 跑九項、隔離例外、組報告
    render.py                         # 產 HTML 與 JSON
    collect.py                        # 讀 facts、跑一輪、寫報告
    _shim.py                          # 借用 hook 的 run/repo_root，一份實作兩邊用
    question_audit.py                 # 比對問題與禁問清單
    probes/
      __init__.py
      environment.py                  # 1 執行環境
      toolchain.py                    # 2 工具鏈
      suite.py                        # 3 測試綠且 < 30 秒
      safety_net.py                   # 4 保命繩通電
      history.py                      # 5 git 歷史抽驗
      github.py                       # 6 GitHub repo 與 Actions
      zeabur.py                       # 7 Zeabur 三層路徑
      service.py                      # 8 兩環境存活與 prod 設定
      data.py                         # 9 資料持久性與備份可還原
  skills/
    install-wizard/
      SKILL.md
      template/                       # 複製到使用者工作資料夾的 Django 樣板
      backup-repo/                    # 放進私有備份庫的東西
        backup.yml
        README.md
    health-check/SKILL.md
    think-first/
      SKILL.md
      CONTEXT-FORMAT.md
      ADR-FORMAT.md
    deploy/SKILL.md

docs/onboarding/
  kickoff-prompt.md                   # 要傳給對方的那段話
  walkthrough.md                      # 從零到完成的走查文件

tests/                                # kit 自己的測試
  conftest.py
  test_safety_net.py
  test_template_project.py
  test_prod_settings.py
  test_backup.py
  test_report_glossary.py
  test_health_check.py
  test_ci_superset.py
  test_question_audit.py
```

樣板內部：

```
skills/install-wizard/template/
  .gitattributes                      # * text=auto eol=lf
  .gitignore                          # .env、reports/、db.sqlite3
  README.md
  CLAUDE.md                           # 專案規則，進 git 所以 Claude 改了會留痕跡
  CONTEXT.md                          # 詞彙表，使用者唯一看得懂也唯一有資格審的技術產物
  docs/adr/.gitkeep
  requirements.txt
  requirements.lock.txt               # pip freeze 的產物
  pytest.ini
  conftest.py                         # 中文 HTML 報告 reporter
  manage.py
  Dockerfile
  entrypoint.sh                       # migrate 後才起 gunicorn
  zeabur.yaml                         # volume 宣告
  scripts/
    run_tests.sh                      # 本機與 CI 的唯一測試入口
    backup_snapshot.py                # VACUUM INTO + integrity_check
    check_deploy.py                   # prod 設定守門
    check_glossary.py                 # 報告名詞對照 CONTEXT.md
    check_ci_superset.py              # CI 與本機同一入口
  project/
    __init__.py
    settings/__init__.py base.py dev.py prod.py
    urls.py
    wsgi.py
  core/
    __init__.py apps.py models.py admin.py views.py urls.py
    migrations/__init__.py
  tests/test_starter.py
  .github/workflows/tests.yml
```

## Behavior Tests

測試放在 kit repo 的 `tests/`，跑法是 `python3 -m pytest tests/ -v`。每個測試附一行**期望值來源**，說明那個數字或字串是從 spec 哪裡來的。

共用 fixture（`tests/conftest.py`）：

```python
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


def run_hook(script_name, payload, cwd):
    """用 hook 的實際介面呼叫它：payload 走 stdin，結果走 stdout。"""
    proc = subprocess.run(
        [sys.executable, str(PLUGIN / "scripts" / script_name)],
        input=json.dumps(payload), cwd=cwd,
        capture_output=True, text=True, timeout=120,
    )
    out = proc.stdout.strip()
    return proc.returncode, (json.loads(out) if out else {}), proc.stderr
```

### B1 新專案一建立就有綠的基準

```python
# tests/test_template_project.py
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

    started = time.monotonic()
    proc = subprocess.run(
        ["sh", "scripts/run_tests.sh"], cwd=project,
        capture_output=True, text=True,
    )
    elapsed = time.monotonic() - started

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert elapsed < 30, f"跑了 {elapsed:.1f} 秒"
```

> **期望值來源**：`returncode == 0` 與 `elapsed < 30` 逐字取自 spec 成功定義 #2「`pytest` 全綠且執行時間 < 30 秒」。

### B2 測試紅的時候不會產生 commit

```python
# tests/test_safety_net.py
from conftest import git, run_hook


def test_red_suite_leaves_history_untouched(repo):
    """改動讓測試變紅，對話結束後 git 歷史沒有新 commit。"""
    before = git("rev-parse", "HEAD", cwd=repo).strip()
    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這個現在是紅的。\"\"\"\n    assert False\n",
        encoding="utf-8",
    )

    code, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert git("rev-parse", "HEAD", cwd=repo).strip() == before
    assert out["decision"] == "block"
    assert git("status", "--porcelain", cwd=repo).strip() != ""


def test_red_suite_tells_claude_to_fix_it(repo):
    """測試紅的時候，回饋訊息說得出是哪個測試壞了。"""
    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這個現在是紅的。\"\"\"\n    assert False\n",
        encoding="utf-8",
    )

    _, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert "test_ok" in out["reason"]


def test_green_suite_produces_exactly_one_commit(repo):
    """測試綠的時候，對話結束後多一個 commit，而且只多一個。"""
    before = int(git("rev-list", "--count", "HEAD", cwd=repo).strip())
    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"另一個綠的。\"\"\"\n    assert True\n",
        encoding="utf-8",
    )

    code, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    after = int(git("rev-list", "--count", "HEAD", cwd=repo).strip())
    assert after == before + 1
    assert out.get("decision") != "block"


def test_nothing_changed_means_no_commit(repo):
    """這一輪沒動到任何檔案，不會產生空的 commit。"""
    before = int(git("rev-list", "--count", "HEAD", cwd=repo).strip())

    run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert int(git("rev-list", "--count", "HEAD", cwd=repo).strip()) == before


def test_second_consecutive_failure_does_not_block_again(repo):
    """已經擋過一次還是紅的，就不再擋，避免對話卡死在同一個迴圈。"""
    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"還是紅的。\"\"\"\n    assert False\n",
        encoding="utf-8",
    )

    _, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": True}, repo)

    assert out.get("decision") != "block"
```

> **期望值來源**：「紅了不 commit、綠了才 commit」取自 spec「三道保命繩」的流程圖。`stop_hook_active` 的存在與語意取自 Claude Code hooks 文件（Cowork 明講共用同一份 schema）；不再重複阻擋是為了避免 spec 未提及但實務上會卡死使用者的無限迴圈。

### B3 歷史上任一點都是能跑的版本

這兩個測試放在 `tests/test_health_check.py`，因為它們測的是健檢的歷史抽驗探針。

```python
# tests/test_health_check.py
def test_history_probe_reports_green_when_every_commit_passes(repo):
    """歷史上每個 commit 都是綠的，抽驗結果為通過。"""
    from checks.probes.history import probe

    result = probe({"repo": str(repo), "sample": 3})

    assert result.ok is True


def test_history_probe_names_the_commit_that_fails(repo):
    """歷史上有一個 commit 是紅的，抽驗要指名是哪一個。"""
    from conftest import git
    from checks.probes.history import probe

    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這一版是紅的。\"\"\"\n    assert False\n",
        encoding="utf-8",
    )
    git("add", "-A", cwd=repo)
    git("commit", "-q", "-m", "broken", cwd=repo)
    bad = git("rev-parse", "HEAD", cwd=repo).strip()

    result = probe({"repo": str(repo), "sample": 99})

    assert result.ok is False
    assert bad[:7] in result.detail


def test_checking_history_leaves_the_working_folder_exactly_as_it_was(repo):
    """抽驗歷史版本的時候，使用者正在改的東西一個字都不會變。"""
    from conftest import git
    from checks.probes.history import probe

    (repo / "tests" / "test_wip.py").write_text(
        "def test_wip():\n    \"\"\"還在寫。\"\"\"\n    assert True\n", encoding="utf-8"
    )
    before_branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo).strip()
    before_status = git("status", "--porcelain", cwd=repo)

    probe({"repo": str(repo), "sample": 99})

    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo).strip() == before_branch
    assert git("status", "--porcelain", cwd=repo) == before_status
    assert (repo / "tests" / "test_wip.py").exists()
```

> **期望值來源**：spec 成功定義 #8「git 歷史上任意一個 commit checkout 出來，`pytest` 皆為綠」。`sample` 讓健檢抽驗、讓測試全驗，是為了滿足 spec 驗證方式的「全部條件可在單一 session 內完成」。

### B4 密鑰擋在 commit 之外

```python
import pytest

from conftest import git, run_hook


@pytest.mark.parametrize(
    "path",
    [".env", ".env.local", "config/id_rsa", "certs/server.pem",
     "gcp-credentials.json", "secrets/api.key"],
)
def test_writing_a_secret_file_is_refused(repo, path):
    """想寫入密鑰類的檔案，會被擋下來並說明原因。"""
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(repo / path), "content": "TOKEN=abc"},
    }

    _, out, _ = run_hook("guard_secrets.py", payload, repo)

    decision = out["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert path.split("/")[-1] in decision["permissionDecisionReason"]


def test_writing_an_ordinary_file_is_allowed(repo):
    """一般的程式碼檔案不受影響。"""
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(repo / "core" / "views.py"), "content": "x = 1"},
    }

    _, out, _ = run_hook("guard_secrets.py", payload, repo)

    assert out == {}


def test_an_untracked_env_file_never_gets_committed(repo):
    """工作區裡有沒被追蹤的 .env，自動 commit 不會把它納進去。"""
    (repo / ".env").write_text("SECRET_KEY=real-one\n", encoding="utf-8")
    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    tracked = git("ls-files", cwd=repo).splitlines()
    assert ".env" not in tracked
```

> **期望值來源**：spec Kit 組成「hook 密鑰擋門 —— 阻止 `.env` 之類被 commit」，以及已知限制 14「公開 repo 換來無限 CI，代價是任何密鑰外洩即為公開」。`deny` 的輸出形狀取自 Claude Code hooks 文件的 `PreToolUse` 段。

### B7 正式環境不會帶著開發設定上線

```python
# tests/test_prod_settings.py
import subprocess
import sys

from conftest import TEMPLATE


def run_check(env, cwd):
    return subprocess.run(
        [sys.executable, "scripts/check_deploy.py"],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


def test_correctly_configured_production_passes(installed_project, prod_env):
    """三項設定都對的正式環境，守門放行。"""
    result = run_check(prod_env, installed_project)

    assert result.returncode == 0


def test_debug_left_on_is_refused(installed_project, prod_env):
    """DEBUG 忘了關就要部署，被擋下並指名是 DEBUG。"""
    prod_env["DJANGO_DEBUG"] = "1"

    result = run_check(prod_env, installed_project)

    assert result.returncode != 0
    assert "DEBUG" in result.stdout


def test_untouched_template_secret_key_is_refused(installed_project, prod_env):
    """SECRET_KEY 還是樣板的預設值就要部署，被擋下並指名是 SECRET_KEY。"""
    prod_env["DJANGO_SECRET_KEY"] = "django-insecure-CHANGE-ME"

    result = run_check(prod_env, installed_project)

    assert result.returncode != 0
    assert "SECRET_KEY" in result.stdout


def test_wildcard_allowed_hosts_is_refused(installed_project, prod_env):
    """ALLOWED_HOSTS 放了萬用字元，被擋下並指名是 ALLOWED_HOSTS。"""
    prod_env["DJANGO_ALLOWED_HOSTS"] = "example.zeabur.app,*"

    result = run_check(prod_env, installed_project)

    assert result.returncode != 0
    assert "ALLOWED_HOSTS" in result.stdout
```

> **期望值來源**：spec 成功定義 #6 三項逐字對應。萬用字元那條是 Django 自己的 `check --deploy` 不會抓的（W020 只檢查 `ALLOWED_HOSTS` 為空），所以必須自己寫。

### B5 部署後資料不會消失（結構部分）

執行期的「重新部署後資料還在」需要真的部署，列在人工清單。可自動測的是**資料庫檔案有沒有落在掛載點底下** —— 這正是探針實測出來的失效原因：沒掛 volume 期間寫入的東西活不過下一次部署。

```python
# tests/test_template_project.py（續）
import re

from conftest import TEMPLATE


def test_database_file_lives_under_a_mounted_volume():
    """正式環境的資料庫檔案路徑，落在 zeabur.yaml 宣告的掛載目錄底下。"""
    declared = re.findall(r"dir:\s*(\S+)", (TEMPLATE / "zeabur.yaml").read_text("utf-8"))
    prod = (TEMPLATE / "project" / "settings" / "prod.py").read_text("utf-8")
    db_dir = re.search(r'DATA_DIR\s*=\s*Path\(os\.environ\[.*?\]\)', prod)

    assert declared, "zeabur.yaml 沒有宣告任何 volume"
    assert db_dir, "prod.py 沒有從環境變數讀資料目錄"
    assert "/data" in declared


def test_the_two_environments_do_not_share_a_volume():
    """staging 與 prod 各自宣告獨立的 volume id。"""
    text = (TEMPLATE / "zeabur.yaml").read_text("utf-8")
    ids = re.findall(r"id:\s*(\S+)", text)

    assert len(ids) == len(set(ids)), f"volume id 重複：{ids}"
```

> **期望值來源**：spec「寫死的預設 —— volume 必須在第一次啟動前掛好」，以及 `probes/volume-check/README.md` 實測的對照組（無 volume → marker GONE）／實驗組（有 volume → marker PRESENT）。`/data` 取自實驗組模板 `zeabur-with-volume.yaml` 的 `dir: /data`。

### B6 備份拿得回來

```python
# tests/test_backup.py
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from conftest import TEMPLATE


def make_db(path, marker):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE note (body TEXT)")
    conn.execute("INSERT INTO note VALUES (?)", (marker,))
    conn.commit()
    conn.close()


def test_the_snapshot_opens_and_contains_what_was_written(tmp_path):
    """備份產出的檔案能被 sqlite3 開啟，而且含備份當下寫入的那筆資料。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import snapshot

    src = tmp_path / "db.sqlite3"
    make_db(src, "健檢寫入的測試資料")

    out = snapshot(src, tmp_path / "backup.sqlite3")

    rows = sqlite3.connect(out).execute("SELECT body FROM note").fetchall()
    assert rows == [("健檢寫入的測試資料",)]


def test_a_corrupt_snapshot_is_reported_not_returned(tmp_path):
    """快照壞掉的時候會報錯，不會交出一個看起來正常的壞備份。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import SnapshotCorrupt, verify

    broken = tmp_path / "backup.sqlite3"
    broken.write_bytes(b"not a database")

    import pytest
    with pytest.raises(SnapshotCorrupt):
        verify(broken)
    assert not broken.exists()


def test_a_healthy_snapshot_passes_verification(tmp_path):
    """完整的快照通過檢查，而且檔案留著。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import verify

    good = tmp_path / "backup.sqlite3"
    make_db(good, "x")

    assert verify(good) == good
    assert good.exists()


def test_an_existing_target_does_not_silently_overwrite(tmp_path):
    """目標檔已經存在時會報錯，不會把舊備份蓋掉。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import snapshot

    src = tmp_path / "db.sqlite3"
    make_db(src, "x")
    out = tmp_path / "backup.sqlite3"
    out.write_bytes(b"previous backup")

    import pytest
    with pytest.raises(FileExistsError):
        snapshot(src, out)
    assert out.read_bytes() == b"previous backup"


def test_backups_older_than_three_months_are_removed(tmp_path):
    """超過三個月的備份會被清掉，三個月內的留著。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import expired_tags

    now = datetime(2026, 8, 9, tzinfo=timezone.utc)
    releases = [
        {"tagName": "backup-2026-08-08", "createdAt": (now - timedelta(days=1)).isoformat()},
        {"tagName": "backup-2026-06-01", "createdAt": (now - timedelta(days=69)).isoformat()},
        {"tagName": "backup-2026-05-01", "createdAt": (now - timedelta(days=100)).isoformat()},
    ]

    assert expired_tags(releases, now=now, keep_days=90) == ["backup-2026-05-01"]
```

> **期望值來源**：spec 成功定義 #7「該檔可被 `sqlite3` 開啟，且包含第 5 條寫入的那筆測試資料」。`keep_days=90` 來自 spec 部署與備份段「保留 3 個月」。「目標檔已存在會報錯」與「中斷會產出損毀檔」是 SQLite 官方對 `VACUUM INTO` 的明文行為，備份腳本必須照它設計而不是繞過它。

### B9 CI 跑的是 local 的超集

```python
# tests/test_ci_superset.py
import sys

from conftest import TEMPLATE

sys.path.insert(0, str(TEMPLATE / "scripts"))
from check_ci_superset import stray_test_commands, uses_shared_entrypoint


def test_ci_runs_the_same_entrypoint_as_local():
    """CI 的測試步驟走的是本機那支同一個入口腳本。"""
    workflow = (TEMPLATE / ".github" / "workflows" / "tests.yml").read_text("utf-8")

    assert uses_shared_entrypoint(workflow)


def test_ci_does_not_run_tests_a_second_way():
    """CI 不會用另一套指令再跑一次測試，否則本機重現不了 CI 的紅。"""
    workflow = (TEMPLATE / ".github" / "workflows" / "tests.yml").read_text("utf-8")

    assert stray_test_commands(workflow) == []


def test_a_workflow_with_its_own_pytest_call_is_rejected():
    """自己另外呼叫 pytest 的 workflow，檢查要抓得出來。"""
    bad = "jobs:\n  t:\n    steps:\n      - run: pytest tests/ -k slow\n"

    assert stray_test_commands(bad) == ["pytest tests/ -k slow"]
```

> **期望值來源**：spec 測試設計「CI 跑的測試必須是 local 測試的超集，破了這條就會出現『我這邊都綠的，為什麼 CI 紅了』」。做法是把「超集」收斂成「同一個入口 + 不得有第二條測試路徑」，因為這樣才驗得動。

### B11 健檢每一項都會獨立紅燈

```python
# tests/test_health_check.py
from checks.model import CheckResult
from checks.runner import run_all


def ok_probe(facts):
    return CheckResult(id="ok", title="一切正常", ok=True, detail="")


def failing_probe(facts):
    return CheckResult(id="bad", title="這項不通", ok=False, detail="缺了東西")


def exploding_probe(facts):
    raise RuntimeError("探針自己爆了")


def test_one_red_item_does_not_affect_the_others():
    """有一項不通，其餘各項照常給出自己的結果。"""
    results = run_all({}, [ok_probe, failing_probe, ok_probe])

    assert [r.ok for r in results] == [True, False, True]


def test_a_probe_that_crashes_becomes_a_red_item_not_a_dead_report():
    """探針自己壞掉，變成那一項紅燈，整份報告還是產得出來。"""
    results = run_all({}, [ok_probe, exploding_probe, ok_probe])

    assert len(results) == 3
    assert results[1].ok is False
    assert "探針自己爆了" in results[1].detail


def test_the_report_covers_all_nine_items():
    """正式的九項探針，一項不多一項不少。"""
    from checks.runner import default_probes

    assert len(default_probes()) == 9
```

> **期望值來源**：spec 成功定義 #1「環境健檢報告 9 項全綠」，九項的清單定義在 Task 12 與 Task 13。探針爆掉要變紅燈而不是讓報告掛掉，是為了滿足 spec 條件 13 的「不得靜默略過」——一份產不出來的報告等於靜默略過。

### B10 健檢說得出 Zeabur 走哪條路

```python
from checks.probes.zeabur import probe


def test_the_cli_is_named_when_it_is_reachable():
    """CLI 這條路通的時候，報告指名走 CLI。"""
    result = probe({"zeabur": {"cli": True, "mcp": True, "browser": True}})

    assert result.ok is True
    assert result.detail.startswith("CLI")


def test_mcp_is_named_when_the_cli_is_blocked():
    """CLI 不通、MCP 通，報告指名走 MCP。"""
    result = probe({"zeabur": {"cli": False, "mcp": True, "browser": True}})

    assert result.ok is True
    assert result.detail.startswith("MCP")


def test_the_browser_is_named_when_it_is_the_only_one_left():
    """只剩瀏覽器可用，報告指名走瀏覽器。"""
    result = probe({"zeabur": {"cli": False, "mcp": False, "browser": True}})

    assert result.ok is True
    assert result.detail.startswith("瀏覽器")


def test_all_three_blocked_turns_the_item_red_with_a_reason():
    """三條路都不通，這一項紅燈，而且說得出三條各自為什麼不通。"""
    result = probe({"zeabur": {"cli": False, "mcp": False, "browser": False}})

    assert result.ok is False
    for name in ("CLI", "MCP", "瀏覽器"):
        assert name in result.detail


def test_a_named_path_without_a_proven_operation_is_red():
    """指名了一條路，但沒有實際跑成功一次操作，這一項不算過。"""
    result = probe({"zeabur": {"cli": True, "mcp": False, "browser": False,
                               "proven": False}})

    assert result.ok is False
```

> **期望值來源**：spec 成功定義 #13「明確指出 Zeabur 操作走的是哪一條路徑，且以該路徑實際執行一次操作成功。三層皆不可用時健檢必須紅燈並說明原因」。優先序 CLI > MCP > 瀏覽器取自 ADR-4 的能力比較：CLI 涵蓋全部操作、MCP 缺租主機與重新部署、瀏覽器對日常操作脆弱。

### B13 測試報告上的詞都查得到定義

```python
# tests/test_report_glossary.py
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
```

> **期望值來源**：spec 成功定義 #10「測試報告 HTML 中出現的領域名詞，能在 `CONTEXT.md` 找到定義的比例 = 100%」。用 `「」` 標記領域名詞，是把「從中文散文裡抽名詞」這個做不準的問題，換成一個做得準的問題 —— 而且寫測試的時候就被迫把詞講定。`## 語言` 段落與 `**詞**：` 的格式沿用 grill-with-docs 的 `CONTEXT-FORMAT.md`，所以 think-first skill 產出的檔案直接對得上。

### B12 模糊需求換來的是業務問題（比對器部分）

輸入要由人給（跟 Claude 對話），但比對是機器做的。

```python
# tests/test_question_audit.py
from checks.question_audit import forbidden_hits, load_rules

RULES = load_rules()


def test_asking_which_database_is_a_forbidden_question():
    """問使用者要用哪個資料庫，判定為禁問。"""
    hits = forbidden_hits("你想用 SQLite 還是 PostgreSQL？", RULES)

    assert [h.category for h in hits] == ["資料庫選型"]


def test_asking_about_a_business_rule_is_not_forbidden():
    """問排班的業務規則，不算禁問。"""
    assert forbidden_hits("員工離職後，他填過的班表要保留還是消失？", RULES) == []


def test_the_word_data_alone_does_not_trigger_a_hit():
    """只是提到「資料」不會被誤判成問資料庫選型。"""
    assert forbidden_hits("這些資料要保留多久？", RULES) == []


def test_every_category_the_spec_requires_is_covered():
    """spec 點名的五個類別，禁問清單一個都不能少。"""
    required = {"資料庫選型", "框架選型", "部署平台", "檔案結構", "演算法選擇"}

    assert required <= {r.category for r in RULES}
```

> **期望值來源**：spec 成功定義 #9 的括號「禁問清單於 plan 階段定義為具體項目，至少涵蓋：資料庫選型、框架選型、部署平台、檔案結構、演算法選擇」。第三個測試防的是規則寫太寬 —— 一個會把正常業務問題判成禁問的清單，比沒有清單更糟。

## 需人工驗證的條件

Gate B 的誠實逃生口。**這幾條是唯一需要人工驗的清單，本計畫沒有另設驗證 task，所以它們必須在收尾時被點名，不能靜靜消失。**

| spec 條件 | 為什麼測不了 | 人工怎麼驗 |
|---|---|---|
| 3 GitHub repo + Actions 成功 | `manual / not unit-testable because` 需要一個真的 GitHub 帳號與一次真的 Actions 執行 | 安裝走完後開 repo 的 Actions 頁，確認最新一次結論為 success |
| 4 兩環境皆 200 | `manual / not unit-testable because` 需要真的部署到 Zeabur | 健檢第 8 項對兩個網址各發一次請求 |
| 5 重新部署後資料仍在 | `manual / not unit-testable because` 需要真的觸發一次重新部署 | 健檢第 9 項：寫入 marker → 重新部署 → 再讀一次 |
| 7 備份 Release 裡的檔案 | `manual / not unit-testable because` 進容器取快照需要真的 Zeabur 服務，上傳需要真的 GitHub 帳號 | 手動觸發一次備份 workflow，然後健檢第 9 項下載最新 Release 的檔案、開起來、找 marker |
| 9 禁問清單命中 0 | `manual / not unit-testable because` 需要 Claude 真的產生問題，非決定性 | 用預先寫好的數組模糊需求各開一次對話，把 Claude 的問題貼進比對器 |
| 11 清空記憶後不重問 | `manual / not unit-testable because` 需要清空 Cowork 的 project memory 並開新 session | 清空後開新 session，數 Claude 重問了幾個已記錄的決策 |
| 12 走查記錄動用文件外知識 = 0 | `manual / not unit-testable because` 這條測的是文件，不是程式 | 只照文件做，每動用一次文件外知識記一筆，不當場修，走完再一起修並重跑 |
| 13 以該路徑實際執行一次操作 | `manual / not unit-testable because` 需要真的 Zeabur 帳號 | 健檢第 7 項實際跑一次唯讀操作並記錄結果 |
| 三個 Cowork 平台假設 | `manual / not unit-testable because` Cowork VM 的行為官方沒有文件，只能在真環境觀察 | Task 1 的驗收步驟，在真的 Cowork 上裝一次 plugin 並確認三件事 |

---

### Task 1: Repo 骨架，並在真的 Cowork 上驗掉三個平台假設

這個 task 的產出不是功能，是**一個能證明 hook 真的會跑的最小 plugin**。後面十七個 task 全部疊在這三個假設上，先驗掉再往上蓋。

**Files:**
- Create: `.claude-plugin/marketplace.json`
- Create: `plugins/starter-kit/.claude-plugin/plugin.json`
- Create: `plugins/starter-kit/hooks/hooks.json`
- Create: `plugins/starter-kit/scripts/_shared.py`
- Create: `plugins/starter-kit/scripts/canary.py`
- Create: `pytest.ini`
- Test: `tests/conftest.py`
- Test: `tests/test_hook_payload.py`

**Interfaces:**
- Consumes: 無，這是第一個 task
- Produces: `scripts/_shared.py` 提供 `read_payload() -> dict`、`emit(obj: dict) -> None`、`run(cmd: list[str], cwd, timeout: int) -> tuple[int, str, str]`、`repo_root(start: Path) -> Path | None`、`plugin_root() -> Path`。後面三個 hook 全部只透過這五個函式跟外界互動。

- [ ] **Step 1: 建立 marketplace 與 plugin 的兩份 manifest**

`.claude-plugin/marketplace.json`：

```json
{
  "name": "ai-project-starter",
  "owner": {
    "name": "ai-project-starter"
  },
  "description": "給非技術者的 Claude 環境包：行為設定、保命繩、Django 樣板與部署流程。",
  "plugins": [
    {
      "name": "starter-kit",
      "source": "./plugins/starter-kit",
      "description": "把一段話貼進 Claude，帶你裝完環境、開好專案、上線兩個環境。",
      "category": "productivity",
      "keywords": ["onboarding", "django", "non-technical"]
    }
  ]
}
```

`plugins/starter-kit/.claude-plugin/plugin.json`：

```json
{
  "name": "starter-kit",
  "version": "0.1.0",
  "description": "給非技術者的 Claude 環境包：行為設定、保命繩、Django 樣板與部署流程。",
  "license": "MIT"
}
```

- [ ] **Step 2: 寫 hook 共用模組**

`plugins/starter-kit/scripts/_shared.py`：

```python
"""Shared helpers for the plugin's hooks.

Standard library only. These scripts must run when pip is broken, when the
network is down, and when no virtualenv is active.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


_JSON_TYPE_NAMES = {
    bool: "boolean",
    int: "number",
    float: "number",
    str: "string",
    list: "array",
    type(None): "null",
}


def read_payload():
    """Read the hook payload from stdin.

    Always returns a dict. This is a guarantee, not a convention: every
    caller downstream can treat the result as a dict without checking.

    - Empty or whitespace-only stdin returns {} silently.
    - Malformed JSON writes one line to stderr and returns {}.
    - Valid JSON that is not a JSON object (a number, string, boolean,
      null, or array) writes one line to stderr naming what it got, and
      returns {}.
    - Bytes on stdin that are not valid UTF-8 are decoded with
      errors="replace" instead of raising.

    Never raises, for any byte sequence on stdin.
    """
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is not None:
        raw = buffer.read().decode("utf-8", errors="replace").strip()
    else:
        raw = sys.stdin.read().strip()

    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        sys.stderr.write(f"Failed to parse hook payload: {exc}\n")
        return {}

    if not isinstance(parsed, dict):
        type_name = _JSON_TYPE_NAMES.get(type(parsed), type(parsed).__name__)
        sys.stderr.write(f"Hook payload must be a JSON object; got {type_name}\n")
        return {}

    return parsed


def emit(obj):
    """Write a hook response to stdout and exit cleanly."""
    if obj:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.exit(0)


def run(cmd, cwd, timeout=120):
    """Run a command, never raising. Returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"
    except OSError as exc:
        return 127, "", str(exc)


def repo_root(start):
    """Walk up from `start` looking for a .git directory. None if not found."""
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def plugin_root():
    """The plugin directory.

    CLAUDE_PLUGIN_ROOT is documented for Claude Code and Cowork states it
    shares the same hooks schema, but Cowork does not document how the
    variable maps inside its VM. If the variable is set and names an existing
    directory, return it silently. Otherwise write one line to stderr and
    return the fallback (this file's parent directory).

    The fallback must be audible. A silent one would make a plugin that
    cannot find its own files look like a working plugin.
    """
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    fallback = Path(__file__).resolve().parent.parent

    if env is None:
        sys.stderr.write("CLAUDE_PLUGIN_ROOT is not set; using fallback\n")
        return fallback

    path = Path(env)
    if path.is_dir():
        return path

    sys.stderr.write(f"CLAUDE_PLUGIN_ROOT={env} does not exist; using fallback\n")
    return fallback
```

- [ ] **Step 3: 寫 canary hook**

`plugins/starter-kit/scripts/canary.py`：

```python
"""Prove that hooks actually fire inside Cowork.

Writes one line per event into the working folder. Task 1 is the only user
of this script; the health check replaces it with a real probe in Task 12.
"""

import datetime
import sys
from pathlib import Path

from _shared import emit, read_payload

payload = read_payload()
event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
line = f"{datetime.datetime.now().isoformat()} {event} keys={sorted(payload)}\n"

try:
    with (Path.cwd() / "hook-canary.log").open("a", encoding="utf-8") as handle:
        handle.write(line)
except Exception as exc:
    # Registered on PreToolUse for Write|Edit. An unhandled failure here would
    # end every single file edit in the session with a traceback.
    sys.stderr.write(f"Failed to write hook-canary.log: {exc}\n")

emit({})
```

`plugins/starter-kit/hooks/hooks.json`：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/canary.py SessionStart"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/canary.py PreToolUse"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/canary.py Stop"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: 建立 kit 自己的測試骨架**

`pytest.ini`：

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

`tests/conftest.py`：內容照「Behavior Tests」段落開頭那份共用 fixture 逐字寫入。

- [ ] **Step 5: 鎖住「hook 不會中斷使用者操作」這條**

`read_payload()` 是每個 hook 的第一個動作，而密鑰擋門掛在 `Write|Edit` 上。這條路徑上
任何一個未處理的例外，都會讓使用者的檔案編輯當場死掉。這件事靠肉眼檢查守不住 ——
實際執行時連續三輪 review 才把例外表面找乾淨，所以它需要測試。

`tests/test_hook_payload.py` 走真的介面（`subprocess` 餵原始位元組進 stdin，斷言退出碼），
涵蓋七種輸入：

| 送進去的 | 要看到的 |
|---|---|
| 空的 | `{}`，沒有 stderr |
| 合法的 JSON 物件 | 原樣回來 |
| 壞掉的 JSON | `{}`、一行 stderr、退出碼 0 |
| 不是 UTF-8 的位元組 | `{}`、退出碼 0 |
| `42` | `{}`、退出碼 0 |
| `[1,2]` | `{}`、退出碼 0 |
| 巢狀四千層的 `[` | `{}`、退出碼 0 |
| 上面每一種餵給 canary | 退出碼 0 |

先寫測試、看它紅、再讓它綠。

最後一項容易被漏掉：`json.loads` 遇到太深的巢狀會丟 `RecursionError`，那**不是**
`JSONDecodeError` 的子類別，所以只接 `JSONDecodeError` 接不到。接 `(ValueError,
RecursionError)` 才蓋得完 —— `JSONDecodeError` 本身是 `ValueError` 的子類別。

- [ ] **Step 6: 確認測試跑得起來**

Run: `python3 -m pytest tests/ -v`
Expected: PASS，7 個測試全綠，輸出乾淨無警告。

- [ ] **Step 7: Commit**

```bash
git add .claude-plugin plugins/starter-kit pytest.ini tests/
git commit -m "feat: add plugin skeleton and a canary that proves hooks fire"
```

- [ ] **Step 8:（人工）在真的 Cowork 上裝一次，驗掉三個假設**

推上 GitHub 之後，在 Claude Desktop 的 Cowork 分頁：Customize → Plugins → Personal plugins → 「+」→ Add marketplace → 輸入 `owner/ai-project-starter` → 裝 `starter-kit`。開一個新對話，隨便寫一個檔案，然後結束該輪。

檢查工作資料夾的 `hook-canary.log`，逐項記錄：

| 要驗的事 | 通過的樣子 | 沒過怎麼辦 |
|---|---|---|
| SessionStart 會觸發 | 檔案裡有一行 `SessionStart` | 開場注入改由 skill 或 folder instructions 承擔，Task 8 改寫 |
| PreToolUse 會觸發且拿得到 `tool_input` | 有一行 `PreToolUse`，`keys=` 含 `tool_input` | 密鑰擋門改成 commit 前檢查，Task 9 降級 |
| Stop 會觸發 | 檔案裡有一行 `Stop` | **這條沒過就整個保命繩設計不成立**，必須回頭改 spec，不能繼續 |
| `${CLAUDE_PLUGIN_ROOT}` 展開正確 | 三行都寫出來了，沒有 `No such file` | `_shared.plugin_root()` 的 fallback 會接住，但要確認 hooks.json 的路徑寫法改用什麼 |

**把結果寫進 `docs/onboarding/platform-notes.md` 並 commit。** 這份紀錄是後面每個 task 的前提。

---

### Task 2: Django 樣板骨架

**Files:**
- Create: `plugins/starter-kit/skills/install-wizard/template/manage.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/project/__init__.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/project/settings/__init__.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/project/settings/base.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/project/settings/dev.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/project/settings/prod.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/project/urls.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/project/wsgi.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/core/` （`__init__.py`、`apps.py`、`models.py`、`admin.py`、`views.py`、`urls.py`、`migrations/__init__.py`）
- Create: `plugins/starter-kit/skills/install-wizard/template/tests/test_starter.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/pytest.ini`
- Create: `plugins/starter-kit/skills/install-wizard/template/requirements.txt`
- Create: `plugins/starter-kit/skills/install-wizard/template/scripts/run_tests.sh`
- Create: `plugins/starter-kit/skills/install-wizard/template/.gitattributes`
- Create: `plugins/starter-kit/skills/install-wizard/template/.gitignore`
- Create: `plugins/starter-kit/skills/install-wizard/template/CLAUDE.md`
- Test: `tests/test_template_project.py`

**Interfaces:**
- Consumes: Task 1 的 `tests/conftest.py`，其中 `TEMPLATE` 常數指向這個目錄
- Produces: `project.settings.base` 定義 `DATA_DIR`；`project.settings.prod` 讀 `DJANGO_DEBUG`、`DJANGO_SECRET_KEY`、`DJANGO_ALLOWED_HOSTS`、`DATA_DIR` 四個環境變數；`core.models.Note` 提供一個 `body` 欄位，供健檢寫 marker 用；`scripts/run_tests.sh` 是本機與 CI 唯一的測試入口

- [ ] **Step 1: 先寫會失敗的測試**

`tests/test_template_project.py`：內容照「Behavior Tests / B1」那段逐字寫入。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_template_project.py -v`
Expected: FAIL，錯誤是找不到 `requirements.lock.txt`。

- [ ] **Step 3: 寫依賴與測試入口**

`requirements.txt`：

```
Django>=5.2,<6.0
gunicorn>=23.0,<24.0
pytest>=8.0,<9.0
pytest-django>=4.9,<5.0
```

`scripts/run_tests.sh`：

```sh
#!/bin/sh
# The one and only way tests are run. CI calls this same script, so a green
# run here means a green run there.
set -e
exec "${PYTHON:-python3}" -m pytest tests/ "$@"
```

`pytest.ini`：

```ini
[pytest]
DJANGO_SETTINGS_MODULE = project.settings.dev
testpaths = tests
python_files = test_*.py
addopts = -q --no-migrations
```

`--no-migrations` 讓測試直接照 model 建表，省掉 migration 重播，是 30 秒預算裡最大的一筆。

- [ ] **Step 4: 寫 settings 三分**

`project/settings/base.py`：

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Where the SQLite file lives. In containers this points at a mounted volume;
# data written outside a volume does not survive the next deploy.
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"
WSGI_APPLICATION = "project.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
        # SQLite allows one writer at a time. Wait instead of failing.
        "OPTIONS": {"timeout": 20, "init_command": "PRAGMA journal_mode=WAL;"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hant"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

WAL 是安全的，因為探針量到 Zeabur 的 volume 是 `/dev/vda2 ... ext4` 這個本機區塊裝置。SQLite 官方明講 WAL 不能跑在網路檔案系統上，所以這個結論綁在「自租單機」這個架構上，換架構要重新確認。

`project/settings/dev.py`：

```python
from .base import *  # noqa: F401,F403

DEBUG = True
SECRET_KEY = "django-insecure-CHANGE-ME"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
```

`project/settings/prod.py`：

```python
import os

from .base import *  # noqa: F401,F403

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host]
```

- [ ] **Step 5: 寫最小的 app 與起點測試**

`core/models.py`：

```python
from django.db import models


class Note(models.Model):
    """A single line of text. The health check writes its marker here."""

    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.body[:40]
```

`core/views.py`：

```python
from django.http import JsonResponse

from .models import Note


def health(request):
    """Liveness endpoint. Returns 200 as long as the database answers."""
    return JsonResponse({"ok": True, "notes": Note.objects.count()})
```

`core/urls.py`：

```python
from django.urls import path

from . import views

urlpatterns = [path("health/", views.health, name="health")]
```

`core/admin.py`：

```python
from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("body", "created_at")
```

`core/apps.py`：

```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
```

`project/urls.py`：

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
```

`project/wsgi.py`：

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.prod")
application = get_wsgi_application()
```

`tests/test_starter.py`：

```python
import pytest


@pytest.mark.django_db
def test_a_saved_note_can_be_read_back_again():
    """存進去的一筆「紀錄」，再讀出來還在。"""
    from core.models import Note

    Note.objects.create(body="第一筆")

    assert Note.objects.get().body == "第一筆"


@pytest.mark.django_db
def test_the_health_page_answers(client):
    """打開健康檢查網址，回 200。"""
    assert client.get("/health/").status_code == 200
```

兩個測試都要 `@pytest.mark.django_db`。健康檢查那頁會去數資料庫裡有幾筆紀錄，
少了這個標記 pytest-django 會直接擋下資料庫存取 —— 而樣板的第一次執行如果是紅的，
「從第一天就有綠的基準」這個前提就不成立了。

`template/manage.py`：Django 的標準樣板，只有一處要注意 ——

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

`manage.py` 預設 dev、`wsgi.py` 預設 prod，這個不對稱是 Django 的慣例：手動下指令
通常是在自己機器上，跑起來的服務則是在正式環境。**代價是容器裡跑 `manage.py migrate`
必須確保 `DJANGO_SETTINGS_MODULE` 已經是 prod**，否則會靜默地用開發設定去動正式資料庫。
Task 4 的 Dockerfile 用 `ENV` 設死它，就是為了這件事。

- [ ] **Step 6: 寫 git 屬性與忽略清單**

`.gitattributes`：

```
* text=auto eol=lf
*.png binary
*.sqlite3 binary
```

`.gitignore`：

```
.env
.env.*
*.sqlite3
reports/
staticfiles/
__pycache__/
*.py[cod]
.venv/
```

- [ ] **Step 7: 寫進 git 的專案規則**

Cowork 的內建記憶是黑盒子 —— 看不到、不能編輯、沒有版本。所以重要的結論不能只留在
記憶裡，要寫成檔案進 git。這個檔案 Claude 自己可以改，那正是它必須進版本控制的理由：
改了會留下痕跡，自動 commit hook 會把它記下來。

`template/CLAUDE.md`：

```markdown
# 這個專案的規則

## 講話

繁體中文，白話。術語第一次出現時用括號補一句人話。不要用表情符號。

## 這個專案已經定好的事

不要重新討論這幾項，它們是環境包定死的：

- 後端用 Django，資料存在 SQLite 檔案裡
- 部署在 Zeabur，`develop` 分支上測試環境、`main` 分支上正式版
- 測試綠了才會存檔，這是自動的

## 決定過的事去哪裡找

- 詞彙表在 `CONTEXT.md` —— 同一個東西只用一個名字，以這份為準
- 做過的決定在 `docs/adr/` —— 開工前先讀，不要重問已經決定過的事

## 動手之前

新功能先跑 think-first skill 把需求問清楚，不要直接開始寫。
```

- [ ] **Step 8: 產出 lock 檔**

Run:
```bash
cd plugins/starter-kit/skills/install-wizard/template
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
.venv/bin/pip freeze > requirements.lock.txt && rm -rf .venv
```
Expected: `requirements.lock.txt` 裡每一行都是 `套件==版本`，沒有任何 `latest`。

- [ ] **Step 9: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_template_project.py -v`
Expected: PASS，且 `test_fresh_project_suite_is_green_within_30_seconds` 印出的耗時遠低於 30 秒。

- [ ] **Step 10: Commit**

```bash
git add plugins/starter-kit/skills/install-wizard/template tests/test_template_project.py
git commit -m "feat: add the Django template with a green baseline from day one"
```

---

### Task 3: 中文測試報告與詞彙一致性

報告是給非技術者看的，它同時是三件事：系統沒壞的證據、系統會做什麼的清單、跟同事解釋這東西能幹嘛的文件。所以報告渲染的是 docstring，不是測試函式名。

**Files:**
- Create: `plugins/starter-kit/skills/install-wizard/template/conftest.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/scripts/check_glossary.py`
- Create: `plugins/starter-kit/skills/install-wizard/template/CONTEXT.md`
- Modify: `plugins/starter-kit/skills/install-wizard/template/tests/test_starter.py`
- Test: `tests/test_report_glossary.py`

**Interfaces:**
- Consumes: Task 2 的樣板目錄與 `tests/test_starter.py`
- Produces: `scripts/check_glossary.py` 提供 `used_terms(html: str) -> set[str]`、`defined_terms(context_md: str) -> set[str]`、`undefined_terms(html: str, context_md: str) -> list[str]`（回傳已排序），以及 `main() -> int`；`conftest.py` 在每次測試結束後把報告寫到 `reports/test-report.html`

- [ ] **Step 1: 先寫會失敗的測試**

`tests/test_report_glossary.py`：內容照「Behavior Tests / B13」那段逐字寫入。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_report_glossary.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'check_glossary'`。

- [ ] **Step 3: 寫詞彙檢查腳本**

`template/scripts/check_glossary.py`：

```python
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
```

- [ ] **Step 4: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_report_glossary.py -v`
Expected: PASS，4 個測試全過。

- [ ] **Step 5: 寫報告產生器**

`template/conftest.py`：

```python
"""Render the test run as a Chinese HTML report.

The report lists what the system promises to do, taken from each test's
docstring. Test function names stay in English; the docstring is the part a
non-technical reader sees.
"""

import html
from pathlib import Path

REPORT = Path("reports/test-report.html")

_docs = {}
_results = []


def pytest_itemcollected(item):
    _docs[item.nodeid] = (item.function.__doc__ or "").strip()


def pytest_runtest_logreport(report):
    if report.when != "call":
        return
    _results.append((report.nodeid, report.passed))


def pytest_sessionfinish(session, exitstatus):
    rows = []
    for nodeid, passed in _results:
        doc = _docs.get(nodeid, "")
        mark = "通過" if passed else "沒過"
        colour = "#2f7d32" if passed else "#c62828"
        rows.append(
            f'<tr><td style="color:{colour}">{mark}</td>'
            f"<td>{html.escape(doc) or html.escape(nodeid)}</td></tr>"
        )
    total = len(_results)
    failed = sum(1 for _, passed in _results if not passed)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "<!DOCTYPE html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\">"
        "<title>測試報告</title></head><body>"
        "<h1>這個系統保證會做的事</h1>"
        f"<p>共 {total} 項，沒過 {failed} 項。</p>"
        '<table border="1" cellpadding="6">' + "".join(rows) + "</table>"
        "</body></html>",
        encoding="utf-8",
    )
```

`html.escape` 會把 `&` 與 `<` 轉掉，但 `「」` 是一般字元不受影響，所以詞彙檢查抓得到。

- [ ] **Step 6: 建立詞彙表，並讓起點測試用標記過的詞**

`template/CONTEXT.md`：

```markdown
# 這個專案在講什麼

這裡放這個專案自己的詞。同一個東西只用一個名字，Claude 跟你都照這份講。

## 語言

**紀錄**：
存進系統的一行文字。目前用來確認資料存得進去、也讀得回來。
```

把 `template/tests/test_starter.py` 的第一個 docstring 改成標記過的版本：

```python
    """存進去的一筆「紀錄」，再讀出來還在。"""
```

- [ ] **Step 7: 確認整條鏈通了**

Run:
```bash
cd plugins/starter-kit/skills/install-wizard/template
sh scripts/run_tests.sh && python3 scripts/check_glossary.py
```
Expected: 測試全過，然後印出「測試報告上的名詞都在詞彙表裡查得到。」

- [ ] **Step 8: Commit**

```bash
git add plugins/starter-kit/skills/install-wizard/template tests/test_report_glossary.py
git commit -m "feat: render the suite as a Chinese report and hold it to the glossary"
```

---

### Task 4: 容器化與 volume

**Files:**
- Create: `plugins/starter-kit/skills/install-wizard/template/Dockerfile`
- Create: `plugins/starter-kit/skills/install-wizard/template/entrypoint.sh`
- Create: `plugins/starter-kit/skills/install-wizard/template/zeabur.yaml`
- Modify: `tests/test_template_project.py`

**Interfaces:**
- Consumes: Task 2 的 `project/settings/prod.py`（讀 `DATA_DIR`）與 `project/wsgi.py`
- Produces: 容器讀 `PORT`、`DATA_DIR` 兩個環境變數；`zeabur.yaml` 宣告 `staging-data` 與 `prod-data` 兩個 volume，掛載點都是 `/data`

- [ ] **Step 1: 先寫會失敗的測試**

在 `tests/test_template_project.py` 追加「Behavior Tests / B5」那兩個測試。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_template_project.py -v`
Expected: FAIL，找不到 `zeabur.yaml`。

- [ ] **Step 3: 寫 Dockerfile**

```dockerfile
# Pinned to the Python line the Cowork VM runs, so local and container match.
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    DATA_DIR=/data \
    DJANGO_SETTINGS_MODULE=project.settings.prod

WORKDIR /app

COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY . .

# SQLite needs to create -wal and -shm files, so the directory must be
# writable, not just the database file.
RUN useradd --create-home app && mkdir -p /data && chown -R app:app /app /data
USER app

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
```

- [ ] **Step 4: 寫 entrypoint**

`entrypoint.sh`：

```sh
#!/bin/sh
# Migrations run here, not in GitHub Actions: Actions cannot reach the SQLite
# file, which lives on a volume inside this container.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Two workers. SQLite serialises writes, so more workers buy contention, not
# throughput.
exec gunicorn project.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --access-logfile -
```

建完要記得 `chmod +x entrypoint.sh scripts/run_tests.sh`。

- [ ] **Step 5: 寫 Zeabur 模板**

`zeabur.yaml`：

```yaml
apiVersion: zeabur.com/v1
kind: Template
metadata:
  name: starter-kit-app
spec:
  services:
    - name: staging
      template: GIT
      spec:
        source:
          branch: develop
        ports:
          - id: web
            port: 8080
            type: HTTP
        volumes:
          - id: staging-data
            dir: /data
        env:
          DATA_DIR:
            default: /data
          DJANGO_SETTINGS_MODULE:
            default: project.settings.prod
    - name: prod
      template: GIT
      spec:
        source:
          branch: main
        ports:
          - id: web
            port: 8080
            type: HTTP
        volumes:
          - id: prod-data
            dir: /data
        env:
          DATA_DIR:
            default: /data
          DJANGO_SETTINGS_MODULE:
            default: project.settings.prod
```

兩個 volume id 不同，所以在 staging 寫的東西不會出現在 prod。`volumes` 這個宣告已由 `probes/volume-check/zeabur-with-volume.yaml` 實測生效——實驗組的 `/data` 是真的 ext4 掛載點。

- [ ] **Step 6: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_template_project.py -v`
Expected: PASS。

- [ ] **Step 7: Commit**

```bash
git add plugins/starter-kit/skills/install-wizard/template tests/test_template_project.py
git commit -m "feat: containerise the template with the volume mounted before first boot"
```

---

### Task 5: 正式環境設定守門

Django 自己的 `check --deploy` 抓 `DEBUG`（W018）與 `django-insecure-` 開頭的 `SECRET_KEY`（W009），但 `ALLOWED_HOSTS` 只檢查為空（W020），**不檢查萬用字元**。spec 成功定義 #6 要的第三項它給不了，所以要自己寫一層。

**Files:**
- Create: `plugins/starter-kit/skills/install-wizard/template/scripts/check_deploy.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_prod_settings.py`

**Interfaces:**
- Consumes: Task 2 的 `project/settings/prod.py`
- Produces: `scripts/check_deploy.py` 提供 `problems(settings) -> list[str]`，每個字串以 `DEBUG`／`SECRET_KEY`／`ALLOWED_HOSTS` 其中之一開頭；`main() -> int` 有問題回非零

- [ ] **Step 1: 補上兩個 fixture**

在 `tests/conftest.py` 追加：

```python
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
```

- [ ] **Step 2: 寫會失敗的測試**

`tests/test_prod_settings.py`：內容照「Behavior Tests / B7」那段逐字寫入。

- [ ] **Step 3: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_prod_settings.py -v`
Expected: FAIL，找不到 `scripts/check_deploy.py`。

- [ ] **Step 4: 寫守門腳本**

```python
"""Refuse to deploy a production configuration that is unsafe.

Django's own deploy check covers DEBUG and the insecure default key, but it
only flags an ALLOWED_HOSTS that is empty. A wildcard passes its check and
fails ours.
"""

import os
import sys

TEMPLATE_DEFAULT_KEY = "django-insecure-CHANGE-ME"


def problems(settings):
    """Every reason this configuration must not go to production."""
    found = []
    if getattr(settings, "DEBUG", False):
        found.append("DEBUG 是開的。正式環境開著它，出錯時會把程式碼細節顯示給所有人看。")
    key = getattr(settings, "SECRET_KEY", "")
    if not key:
        found.append("SECRET_KEY 是空的。這把鑰匙用來簽登入狀態，沒有它任何人都能偽造登入。")
    elif key == TEMPLATE_DEFAULT_KEY or key.startswith("django-insecure-"):
        found.append("SECRET_KEY 還是樣板的預設值。這個值是公開的，等於沒有鎖。")
    hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
    if not hosts:
        found.append("ALLOWED_HOSTS 是空的，網站會拒絕所有連線。")
    elif "*" in hosts:
        found.append("ALLOWED_HOSTS 含有萬用字元，等於接受任何網址轉過來的請求。")
    return found


def main():
    import django
    from django.conf import settings

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.prod")
    django.setup()

    found = problems(settings)
    if found:
        print("正式環境的設定有問題，先修好才能上線：")
        for item in found:
            print(f"  - {item}")
        return 1
    print("正式環境設定沒問題。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_prod_settings.py -v`
Expected: PASS，4 個測試全過。

- [ ] **Step 6: Commit**

```bash
git add plugins/starter-kit/skills/install-wizard/template/scripts/check_deploy.py tests/conftest.py tests/test_prod_settings.py
git commit -m "feat: block deploys whose production settings are unsafe"
```

---

### Task 6: CI workflow 與超集檢查

「超集」直接測很難，所以收斂成兩個測得動的條件：**CI 走的是本機那支同一個入口**，而且**不存在第二條測試路徑**。破了任一條就會出現「我這邊都綠的，為什麼 CI 紅了」。

**Files:**
- Create: `plugins/starter-kit/skills/install-wizard/template/.github/workflows/tests.yml`
- Create: `plugins/starter-kit/skills/install-wizard/template/scripts/check_ci_superset.py`
- Test: `tests/test_ci_superset.py`

**Interfaces:**
- Consumes: Task 2 的 `scripts/run_tests.sh`
- Produces: `scripts/check_ci_superset.py` 提供 `uses_shared_entrypoint(workflow: str) -> bool` 與 `stray_test_commands(workflow: str) -> list[str]`

- [ ] **Step 1: 先寫會失敗的測試**

`tests/test_ci_superset.py`：內容照「Behavior Tests / B9」那段逐字寫入。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_ci_superset.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'check_ci_superset'`。

- [ ] **Step 3: 寫超集檢查**

```python
"""Keep CI and local on one test path.

Parsing YAML would need a dependency, and these scripts are standard library
only. The workflow is ours, so matching on lines is enough and honest about
what it can see.
"""

import re
import sys
from pathlib import Path

ENTRYPOINT = "scripts/run_tests.sh"
TEST_COMMAND = re.compile(r"^\s*(?:-\s*run:\s*)?(.*\bpytest\b.*)$", re.MULTILINE)


def uses_shared_entrypoint(workflow):
    """True when the workflow runs the same script local runs."""
    return ENTRYPOINT in workflow


def stray_test_commands(workflow):
    """Test invocations that bypass the shared entrypoint."""
    stray = []
    for line in workflow.splitlines():
        if ENTRYPOINT in line:
            continue
        match = TEST_COMMAND.match(line)
        if match:
            stray.append(match.group(1).strip())
    return stray


def main():
    workflow = Path(".github/workflows/tests.yml")
    if not workflow.exists():
        print("找不到 CI 設定檔。")
        return 1
    text = workflow.read_text("utf-8")
    if not uses_shared_entrypoint(text):
        print(f"CI 沒有走 {ENTRYPOINT}，本機跟 CI 會跑出不一樣的結果。")
        return 1
    stray = stray_test_commands(text)
    if stray:
        print("CI 裡有另一條測試路徑，本機重現不了它的紅：")
        for item in stray:
            print(f"  - {item}")
        return 1
    print("CI 跟本機跑的是同一組測試。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 寫 CI workflow**

`.github/workflows/tests.yml`：

```yaml
name: tests

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        # 3.10 mirrors the Cowork VM, 3.12 mirrors nothing yet but catches
        # breakage before the VM moves. Same tests, two runtimes.
        python-version: ["3.10", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -r requirements.lock.txt
      - name: Run the tests
        run: sh scripts/run_tests.sh
      - name: Check the glossary
        run: python3 scripts/check_glossary.py
      - name: Check CI and local agree
        run: python3 scripts/check_ci_superset.py

  deploy-safety:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: pip install -r requirements.lock.txt
      - name: Check the production settings
        env:
          DJANGO_SETTINGS_MODULE: project.settings.prod
          DJANGO_DEBUG: "0"
          DJANGO_SECRET_KEY: ${{ secrets.DJANGO_SECRET_KEY }}
          DJANGO_ALLOWED_HOSTS: ${{ vars.DJANGO_ALLOWED_HOSTS }}
          DATA_DIR: /tmp
        run: |
          python3 manage.py check --deploy --fail-level WARNING
          python3 scripts/check_deploy.py
```

- [ ] **Step 5: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_ci_superset.py -v`
Expected: PASS，3 個測試全過。

- [ ] **Step 6: Commit**

```bash
git add plugins/starter-kit/skills/install-wizard/template tests/test_ci_superset.py
git commit -m "feat: run one test path in CI and prove it is the local one"
```

---

### Task 7: 備份

**排程放在私有備份庫，不放公開的程式碼庫。** `GITHUB_TOKEN` 只能操作自己所在的 repo，跨 repo 上傳 Release 需要一組 PAT——而把「能寫入私有備份庫」的憑證放進公開 repo，等於把備份的門鑰匙掛在門外。反過來讓排程跑在私有庫、由它主動去抓，用預設 token 就夠，公開庫一把鑰匙都不用放。私有庫每月 2000 分鐘免費，每天跑一次用不到 30 分鐘。

快照怎麼離開容器：**用 Zeabur CLI 進容器執行，把結果從 stdout 帶出來**。資料庫在容器裡的 volume 上，Actions 直接碰不到。這條路不需要在對外的網站上開任何額外的路由——公開的程式碼裡不會多出一個「這裡可以下載整個資料庫」的入口。

代價要寫清楚，實作時會撞到：

- **CLI 沒有任何指令列得出環境 ID**（探針實測）。所以服務 ID 與環境 ID 由安裝嚮導從網址列抓下來，存成私有備份庫的變數。
- **容器裡沒有 `sqlite3` 指令**，base image 是 `python:3.10-slim`。所以進容器跑的是 `python -c`，用內建的 `sqlite3` 模組。
- **stdout 只能帶文字**，所以快照要 base64 編碼再傳出來。傳輸壞掉不會當場報錯，所以解碼之後一定要跑一次完整性檢查——這正是 `verify()` 被拆成獨立函式的第二個用途。
- Actions 的 runner 沒有網路限制，所以 `zeabur.com` 在這裡一定連得到。egress 白名單那個問題只影響 Cowork 裡面，不影響這條路。

**Files:**
- Create: `plugins/starter-kit/skills/install-wizard/template/scripts/backup_snapshot.py`
- Create: `plugins/starter-kit/skills/install-wizard/backup-repo/backup.yml`
- Create: `plugins/starter-kit/skills/install-wizard/backup-repo/README.md`
- Test: `tests/test_backup.py`

**Interfaces:**
- Consumes: Task 2 的 `core/models.Note` 與 `project/settings/base.DATA_DIR`
- Produces: `scripts/backup_snapshot.py` 提供 `verify(path) -> Path`（沒過丟 `SnapshotCorrupt` 並刪檔）、`snapshot(db_path, out_path) -> Path`（目標檔已存在丟 `FileExistsError`）、`expired_tags(releases, now, keep_days) -> list[str]`，以及 `main()` 支援 `expired` 與 `verify` 兩個子指令

- [ ] **Step 1: 先寫會失敗的測試**

`tests/test_backup.py`：內容照「Behavior Tests / B6」那段逐字寫入。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_backup.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'backup_snapshot'`。

- [ ] **Step 3: 寫快照腳本**

```python
"""Take a consistent snapshot of the SQLite database.

Copying the file can capture a torn write, producing a backup that looks
valid and is not — a failure only discovered during a restore. VACUUM INTO
avoids that, but SQLite documents that an interrupted run leaves a corrupt
output, so every snapshot is verified before it is handed back.
"""

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SnapshotCorrupt(RuntimeError):
    """The snapshot did not pass its integrity check and was discarded."""


def verify(path):
    """Return `path` if it is a healthy database; delete it and raise if not.

    Kept separate from `snapshot` so the corrupt path is reachable from a
    test without a test-only branch living in production code. The backup
    workflow also calls it on its own, after transferring the file.
    """
    path = Path(path)
    try:
        result = sqlite3.connect(path).execute("PRAGMA integrity_check").fetchone()
        healthy = bool(result) and result[0] == "ok"
    except sqlite3.DatabaseError:
        healthy = False

    if not healthy:
        path.unlink(missing_ok=True)
        raise SnapshotCorrupt(f"{path} 沒通過完整性檢查，已刪除。")
    return path


def snapshot(db_path, out_path):
    """Write a verified snapshot of `db_path` to `out_path`."""
    out_path = Path(out_path)
    if out_path.exists() and out_path.stat().st_size > 0:
        raise FileExistsError(f"{out_path} 已經存在，不覆蓋既有備份。")

    source = sqlite3.connect(db_path)
    try:
        source.execute("VACUUM INTO ?", (str(out_path),))
    finally:
        source.close()

    return verify(out_path)


def expired_tags(releases, now, keep_days):
    """Release tags older than the retention window."""
    cutoff = now - timedelta(days=keep_days)
    expired = []
    for release in releases:
        created = datetime.fromisoformat(release["createdAt"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created < cutoff:
            expired.append(release["tagName"])
    return expired


def main():
    import json

    command = sys.argv[1]
    if command == "expired":
        releases = json.loads(Path(sys.argv[2]).read_text("utf-8"))
        for tag in expired_tags(releases, datetime.now(timezone.utc), keep_days=90):
            print(tag)
        return 0
    if command == "verify":
        verify(sys.argv[2])
        print("備份檔完整。")
        return 0
    snapshot(command, sys.argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_backup.py -v`
Expected: PASS，4 個測試全過。

- [ ] **Step 5: 寫私有備份庫的說明**

`plugins/starter-kit/skills/install-wizard/backup-repo/README.md`：

```markdown
# 備份

這個 repo 是私有的，因為裡面有使用者帳號和密碼。

每天自動從正式環境抓一份資料庫快照，存成這個 repo 的 Release，保留三個月。

## 要設定的東西

| 名稱 | 種類 | 內容 |
|---|---|---|
| `ZEABUR_API_TOKEN` | secret | Zeabur 的 API token |
| `ZEABUR_SERVICE_ID` | variable | 正式環境那個服務的 ID |
| `ZEABUR_ENV_ID` | variable | 正式環境的環境 ID |
| `CODE_REPO` | variable | 程式碼 repo，格式 `帳號/repo 名稱` |

服務 ID 與環境 ID 要從 Zeabur 網站的網址列抓 —— CLI 沒有任何指令列得出來。
安裝嚮導會帶你做這一步。

## 要還原的時候

到 Releases 下載那天的 `.sqlite3` 檔，交給 Claude，跟它說你要還原到哪一天。
```

- [ ] **Step 6: 寫私有備份庫的 workflow**

`plugins/starter-kit/skills/install-wizard/backup-repo/backup.yml`：

```yaml
name: backup

# This workflow lives in the PRIVATE backup repository, not in the public
# code repository. That way the default GITHUB_TOKEN is enough and no
# credential that reaches this repo is ever stored in a public one.
on:
  schedule:
    - cron: "17 19 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  snapshot:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch the backup script from the code repository
        run: |
          curl -sSfL -o backup_snapshot.py \
            "https://raw.githubusercontent.com/${{ vars.CODE_REPO }}/main/scripts/backup_snapshot.py"

      - name: Install the Zeabur CLI
        run: npm install -g zeabur@0.21.0

      # The database sits on a volume inside the container, so the snapshot is
      # taken in there and carried out through stdout. The image is
      # python:3.10-slim, which has no sqlite3 command — hence python -c.
      - name: Take a consistent snapshot inside the container
        env:
          ZEABUR_API_TOKEN: ${{ secrets.ZEABUR_API_TOKEN }}
        run: |
          zeabur service exec \
            --service-id "${{ vars.ZEABUR_SERVICE_ID }}" \
            --env-id "${{ vars.ZEABUR_ENV_ID }}" \
            -- python -c '
          import base64, os, sqlite3, sys, tempfile
          src = os.path.join(os.environ.get("DATA_DIR", "/data"), "db.sqlite3")
          out = os.path.join(tempfile.mkdtemp(), "snap.sqlite3")
          conn = sqlite3.connect(src)
          conn.execute("VACUUM INTO ?", (out,))
          conn.close()
          with open(out, "rb") as handle:
              sys.stdout.write(base64.b64encode(handle.read()).decode())
          os.remove(out)
          ' > snapshot.b64
          python3 -c "
          import base64, pathlib
          data = pathlib.Path('snapshot.b64').read_text().strip()
          pathlib.Path('snapshot.sqlite3').write_bytes(base64.b64decode(data))
          "

      # Transport does not report its own failures, so the file is checked
      # after it arrives, not only where it was made.
      - name: Refuse to keep a snapshot that does not open
        run: python3 backup_snapshot.py verify snapshot.sqlite3

      - name: Publish it as a release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          TAG="backup-$(date -u +%Y-%m-%d)"
          mv snapshot.sqlite3 "${TAG}.sqlite3"
          gh release create "$TAG" "${TAG}.sqlite3" \
            --repo "${{ github.repository }}" \
            --title "$TAG" --notes "Automatic snapshot."

      - name: Drop snapshots older than three months
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release list --repo "${{ github.repository }}" --limit 500 \
            --json tagName,createdAt > releases.json
          python3 backup_snapshot.py expired releases.json | while read -r tag; do
            gh release delete "$tag" --repo "${{ github.repository }}" --cleanup-tag --yes
          done
```

- [ ] **Step 7: Commit**

```bash
git add plugins/starter-kit/skills/install-wizard tests/test_backup.py
git commit -m "feat: back up from the private repo so no key sits in a public one"
```

---

### Task 8: 行為層三支柱、禁問清單與開場注入

**Files:**
- Create: `plugins/starter-kit/behavior/pillars.md`
- Create: `plugins/starter-kit/behavior/forbidden-questions.md`
- Create: `plugins/starter-kit/checks/__init__.py`
- Create: `plugins/starter-kit/checks/question_audit.py`
- Create: `plugins/starter-kit/scripts/session_start.py`
- Modify: `plugins/starter-kit/hooks/hooks.json`
- Test: `tests/test_question_audit.py`

**Interfaces:**
- Consumes: Task 1 的 `scripts/_shared.py`
- Produces: `checks/question_audit.py` 提供 `Rule`（具 `category`、`pattern`、`why`、`ask_instead` 四個欄位）、`load_rules() -> list[Rule]`、`forbidden_hits(text: str, rules) -> list[Rule]`

- [ ] **Step 1: 先寫會失敗的測試**

`tests/test_question_audit.py`：內容照「Behavior Tests / B12」那段逐字寫入。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_question_audit.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'checks.question_audit'`。

- [ ] **Step 3: 寫禁問清單**

`plugins/starter-kit/behavior/forbidden-questions.md`：

```markdown
# 禁問清單

這些問題不能用技術的樣子問使用者。不是不能問，是要換成他答得出來的問法。

| 類別 | 判定樣式 | 為什麼不能這樣問 | 該問什麼 |
|---|---|---|---|
| 資料庫選型 | `SQLite\|Postgres\|PostgreSQL\|MySQL\|MongoDB\|用哪個資料庫\|資料庫要用` | 他沒有判斷依據，答什麼都是猜 | 最多多少人同時用？會開放給公司外的人嗎？ |
| 框架選型 | `Django\|FastAPI\|Flask\|Rails\|React\|Vue\|用哪個框架\|前端要用` | 同上，而且選錯的代價他看不見 | 直接決定，寫進 ADR，告訴他結論就好 |
| 部署平台 | `Zeabur\|Vercel\|Heroku\|AWS\|GCP\|部署到哪\|要用哪個平台` | 這是成本與維運的取捨，不是他的取捨 | 這東西要給公司外的人用嗎？壞掉多久之內要修好？ |
| 檔案結構 | `目錄結構\|檔案要放哪\|資料夾怎麼分\|要不要拆成\|monorepo` | 他看不懂目錄，也不會因此改變任何決定 | 直接決定 |
| 演算法選擇 | `演算法\|貪婪\|動態規劃\|要用什麼演算法\|排序方式要用` | 他要的是結果對不對，不是怎麼算 | 排出來的班要先滿足誰的偏好？有沒有一定不能違反的規則？ |
| 認證機制 | `OAuth\|JWT\|SAML\|session 還是 token\|認證要用` | 純技術實作 | 除了員工和主管，還有第三種人嗎？ |
| 快取與效能 | `Redis\|memcache\|要不要加快取\|要不要加索引` | 過早最佳化，而且他無從判斷 | 直接決定；真的變慢再告訴他 |
| 測試框架 | `pytest\|unittest\|jest\|測試框架要用` | 純技術實作 | 直接決定 |
```

- [ ] **Step 4: 寫比對器**

`plugins/starter-kit/checks/question_audit.py`：

```python
"""Compare a batch of questions against the forbidden list.

The list is deliberately narrow. A rule that flags an ordinary business
question is worse than no rule, because it trains everyone to ignore the
output.
"""

import re
from dataclasses import dataclass
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parent.parent / "behavior" / "forbidden-questions.md"
ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", re.M)


@dataclass(frozen=True)
class Rule:
    category: str
    pattern: str
    why: str
    ask_instead: str


def load_rules(path=RULES_FILE):
    """Read the forbidden list from its markdown table."""
    text = Path(path).read_text("utf-8")
    return [
        Rule(category=c, pattern=p, why=w, ask_instead=a)
        for c, p, w, a in ROW.findall(text)
    ]


def forbidden_hits(text, rules):
    """Rules this text trips, in list order."""
    return [rule for rule in rules if re.search(rule.pattern, text, re.IGNORECASE)]
```

- [ ] **Step 5: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_question_audit.py -v`
Expected: PASS，4 個測試全過。若 `test_the_word_data_alone_does_not_trigger_a_hit` 沒過，代表某條樣式寫太寬，收窄它而不是改測試。

- [ ] **Step 6: 寫三支柱**

`plugins/starter-kit/behavior/pillars.md`：

```markdown
## 怎麼講話

繁體中文，白話。術語第一次出現時用括號補一句人話，之後就直接用。
不要用表情符號。結論先講，再展開。

## 怎麼動手

放手模式。讀檔案、寫新檔案、跑分析、跑測試 —— 直接做，不用問。

只有兩種事要停下來問：**刪除**，以及**對外發布**（上正式版、寄信、發訊息、
把東西公開出去）。

## 怎麼決定

1. 技術決策底下藏著業務取捨 → 翻譯成業務問題來問。不是不能問，是不能用
   技術的樣子問。
2. 底下沒有業務取捨 → 自己決定，寫一則 ADR，然後告訴他你決定了什麼，
   不要求他確認。
3. 好幾個業務答案交互產生的後果 → 自己推導、自己處理，不要再回頭問。

**檢查點**：如果一個技術決策翻譯不出業務問題，那是信號 —— 代表你還沒想清楚
這個決策會影響什麼。回頭再想，不要當作「沒有業務取捨」跳過。

**翻譯是有損的**：翻完要自問「他的答案夠不夠支撐這個技術決策」，不夠就補問。
```

- [ ] **Step 7: 寫開場注入 hook**

`plugins/starter-kit/scripts/session_start.py`：

```python
"""Load the behaviour pillars at the start of every session."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import emit, plugin_root, read_payload

read_payload()

pillars = plugin_root() / "behavior" / "pillars.md"
if not pillars.exists():
    emit({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "警告：環境包的行為設定檔找不到，Claude 現在是預設行為。"
                f"預期路徑：{pillars}"
            ),
        }
    })

emit({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": pillars.read_text("utf-8"),
    }
})
```

把 `hooks.json` 的 `SessionStart` 項目從 canary 改成：

```json
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/session_start.py"
```

- [ ] **Step 8: 手動確認注入的內容是完整的**

Run: `echo '{}' | python3 plugins/starter-kit/scripts/session_start.py`
Expected: 一段 JSON，`additionalContext` 裡含「放手模式」與「翻譯是有損的」兩句。

- [ ] **Step 9: Commit**

```bash
git add plugins/starter-kit/behavior plugins/starter-kit/checks plugins/starter-kit/scripts/session_start.py plugins/starter-kit/hooks/hooks.json tests/test_question_audit.py
git commit -m "feat: load the behaviour pillars and make the forbidden list checkable"
```

---

### Task 9: 密鑰擋門

**Files:**
- Create: `plugins/starter-kit/scripts/guard_secrets.py`
- Modify: `plugins/starter-kit/hooks/hooks.json`
- Test: `tests/test_safety_net.py`（本 task 只寫 B4 的三個測試）

**Interfaces:**
- Consumes: Task 1 的 `scripts/_shared.py`
- Produces: `scripts/guard_secrets.py` 讀 `tool_input.file_path`，命中就輸出 `permissionDecision: "deny"`，沒命中輸出空字串

- [ ] **Step 1: 先寫會失敗的測試**

`tests/test_safety_net.py`：寫入「Behavior Tests / B4」的前兩個測試（`test_writing_a_secret_file_is_refused` 與 `test_writing_an_ordinary_file_is_allowed`）。第三個測試依賴 Task 10 的 commit hook，留到那時候再加。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_safety_net.py -v`
Expected: FAIL，找不到 `guard_secrets.py`。

- [ ] **Step 3: 寫擋門腳本**

```python
"""Refuse to write files that hold credentials.

The code repository is public, which is what buys unlimited CI minutes. The
price is that anything leaked is leaked publicly. This is a guard rail, not
insurance.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import emit, read_payload

BLOCKED = [
    (re.compile(r"(^|/)\.env(\.|$)"), "環境變數檔"),
    (re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$"), "SSH 私鑰"),
    (re.compile(r"\.(pem|key|p12|pfx)$"), "憑證或私鑰"),
    (re.compile(r"credentials?\.json$"), "雲端服務憑證"),
    (re.compile(r"(^|/)\.netrc$"), "登入資訊檔"),
]

payload = read_payload()
path = str(payload.get("tool_input", {}).get("file_path", ""))

for pattern, label in BLOCKED:
    if pattern.search(path):
        name = path.rsplit("/", 1)[-1]
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"{name} 看起來是{label}。這個專案的程式碼是公開的，"
                    "密鑰寫進去就等於公開。請改成用環境變數，"
                    "或告訴我你確定要這樣做的理由。"
                ),
            }
        })

emit({})
```

- [ ] **Step 4: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_safety_net.py -v`
Expected: PASS，`.env`、`.env.local`、`id_rsa`、`server.pem`、`gcp-credentials.json`、`api.key` 六個參數化案例全過，一般檔案放行。

- [ ] **Step 5: 接上 hook**

把 `hooks.json` 的 `PreToolUse` 項目從 canary 改成：

```json
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/guard_secrets.py"
```

- [ ] **Step 6: Commit**

```bash
git add plugins/starter-kit/scripts/guard_secrets.py plugins/starter-kit/hooks/hooks.json tests/test_safety_net.py
git commit -m "feat: refuse to write credential files into a public repository"
```

---

### Task 10: 測試綠才 commit

git 歷史上每一個 commit 都是測試綠的狀態。回溯到任何一點，拿到的都是能跑的版本。這讓放手模式真正安全 —— 不是「反正壞了可以回」，是「隨時可以回到一個確定能跑的版本」。

**Files:**
- Create: `plugins/starter-kit/scripts/commit_if_green.py`
- Modify: `plugins/starter-kit/hooks/hooks.json`
- Modify: `tests/test_safety_net.py`

**Interfaces:**
- Consumes: Task 1 的 `scripts/_shared.py`、Task 2 的 `scripts/run_tests.sh`
- Produces: `scripts/commit_if_green.py` 讀 `stop_hook_active`，測試紅時輸出 `{"decision": "block", "reason": ...}`，綠時建立一個 commit 並輸出空字串

- [ ] **Step 1: 補齊測試**

在 `tests/test_safety_net.py` 追加「Behavior Tests / B2」的五個測試，以及 B4 的 `test_an_untracked_env_file_never_gets_committed`。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_safety_net.py -v`
Expected: FAIL，找不到 `commit_if_green.py`。

- [ ] **Step 3: 寫 commit hook**

```python
"""Run the tests at the end of each turn and commit only when they are green.

Every commit in history is therefore a working version. When the suite is
red the changes stay in the working tree — nothing is thrown away, it just
does not become a commit.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import emit, read_payload, repo_root, run

FAILED_TEST = re.compile(r"^(FAILED|ERROR)\s+(\S+)", re.MULTILINE)

payload = read_payload()
root = repo_root(Path.cwd())

if root is None:
    emit({})

# Nothing changed this turn, so there is nothing to test and nothing to commit.
_, status, _ = run(["git", "status", "--porcelain"], cwd=root)
if not status.strip():
    emit({})

runner = root / "scripts" / "run_tests.sh"
if not runner.exists():
    emit({})

code, out, err = run(["sh", str(runner), "--maxfail=1", "-q"], cwd=root, timeout=180)

if code != 0:
    # Already blocked once on this failure. Blocking again would trap the
    # conversation in a loop the user cannot get out of.
    if payload.get("stop_hook_active"):
        emit({})
    names = [name for _, name in FAILED_TEST.findall(out + err)] or ["（看不出是哪一個）"]
    emit({
        "decision": "block",
        "reason": (
            "測試沒過，所以這一輪的改動還沒有存檔。\n"
            f"壞掉的是：{', '.join(names[:5])}\n"
            "先把它修好，修好之後會自動存檔。改動都還在，沒有東西不見。"
        ),
    })

# Green. Stage everything git is willing to track — .gitignore keeps .env and
# friends out, and guard_secrets.py stops them being created in the first place.
run(["git", "add", "-A"], cwd=root)
_, staged, _ = run(["git", "diff", "--cached", "--name-only"], cwd=root)
if not staged.strip():
    emit({})

run(["git", "commit", "-q", "-m", "chore: save a working version"], cwd=root)
emit({})
```

- [ ] **Step 4: 跑測試，確認轉綠**

Run: `python3 -m pytest tests/test_safety_net.py -v`
Expected: PASS，8 個測試全過。

- [ ] **Step 5: 接上 hook**

把 `hooks.json` 的 `Stop` 項目從 canary 改成：

```json
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/commit_if_green.py"
```

同時刪掉 `plugins/starter-kit/scripts/canary.py` —— 它的任務在 Task 1 就結束了。

- [ ] **Step 6: Commit**

```bash
git rm plugins/starter-kit/scripts/canary.py
git add plugins/starter-kit/scripts/commit_if_green.py plugins/starter-kit/hooks/hooks.json tests/test_safety_net.py
git commit -m "feat: commit only green states so every point in history runs"
```

---

### Task 11: 健檢框架與報告

探針分兩種輸入：**shell 看得到的事實**（檔案、指令、網路）由探針自己抓；**shell 看不到的事實**（現在是不是本機模式、MCP 通不通、瀏覽器擴充功能在不在）由 health-check skill 探完之後放進 `facts` 傳進來。這條界線是整個健檢設計的關鍵 —— 它讓判定邏輯測得動，而不是變成一坨只能人工看的 shell。

**Files:**
- Create: `plugins/starter-kit/checks/model.py`
- Create: `plugins/starter-kit/checks/runner.py`
- Create: `plugins/starter-kit/checks/render.py`
- Create: `plugins/starter-kit/checks/probes/__init__.py`
- Test: `tests/test_health_check.py`

**Interfaces:**
- Consumes: Task 8 建立的 `checks/__init__.py`
- Produces: `CheckResult(id, title, ok, detail, hint="")`；`run_all(facts: dict, probes: list | None) -> list[CheckResult]`，任一探針拋例外都轉成該項紅燈；`default_probes() -> list`，回傳長度為 9 的探針清單，import 寫在函式裡所以探針還沒寫完時這個模組仍然載得進來；`render_html(results) -> str` 與 `render_json(results) -> str`

- [ ] **Step 1: 先寫會失敗的測試**

`tests/test_health_check.py`：寫入「Behavior Tests / B11」那三個測試。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_health_check.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'checks.model'`。

- [ ] **Step 3: 寫型別與 runner**

`plugins/starter-kit/checks/model.py`：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """One line of the health report."""

    id: str
    title: str
    ok: bool
    detail: str
    hint: str = ""
```

`plugins/starter-kit/checks/runner.py`：

```python
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
```

- [ ] **Step 4: 跑測試，確認前兩個轉綠**

Run: `python3 -m pytest tests/test_health_check.py -v`
Expected: `test_one_red_item_does_not_affect_the_others` 與 `test_a_probe_that_crashes_becomes_a_red_item_not_a_dead_report` PASS；`test_the_report_covers_all_nine_items` 仍 FAIL（探針還沒寫）。

- [ ] **Step 5: 寫報告渲染**

`plugins/starter-kit/checks/render.py`：

```python
"""Render the health report for a person and for a script."""

import html
import json


def render_json(results):
    """The machine-readable form. Tests assert on this, not on the HTML."""
    return json.dumps(
        [
            {"id": r.id, "title": r.title, "ok": r.ok, "detail": r.detail, "hint": r.hint}
            for r in results
        ],
        ensure_ascii=False,
        indent=2,
    )


def render_html(results):
    """The form a non-technical reader opens."""
    red = [r for r in results if not r.ok]
    rows = []
    for r in results:
        mark = "綠" if r.ok else "紅"
        colour = "#2f7d32" if r.ok else "#c62828"
        extra = f"<br><small>{html.escape(r.hint)}</small>" if r.hint else ""
        rows.append(
            f'<tr><td style="color:{colour};font-weight:600">{mark}</td>'
            f"<td>{html.escape(r.title)}</td>"
            f"<td>{html.escape(r.detail)}{extra}</td></tr>"
        )
    headline = "全部都好了。" if not red else f"有 {len(red)} 項要處理。"
    return (
        '<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
        "<title>環境健檢</title></head><body>"
        f"<h1>環境健檢</h1><p>{headline}</p>"
        '<table border="1" cellpadding="6">'
        "<tr><th>狀態</th><th>檢查項目</th><th>結果</th></tr>"
        + "".join(rows)
        + "</table></body></html>"
    )
```

- [ ] **Step 6: Commit**

```bash
git add plugins/starter-kit/checks tests/test_health_check.py
git commit -m "feat: run health probes in isolation so one failure cannot hide the rest"
```

---

### Task 12: 八項一般探針

**Files:**
- Create: `plugins/starter-kit/checks/_shim.py`
- Create: `plugins/starter-kit/checks/probes/environment.py`、`toolchain.py`、`suite.py`、`safety_net.py`、`history.py`、`github.py`、`service.py`、`data.py`
- Modify: `tests/test_health_check.py`

**Interfaces:**
- Consumes: Task 11 的 `CheckResult`、Task 1 的 `scripts/_shared.run`
- Produces: 每個模組一個 `probe(facts: dict) -> CheckResult`。`facts` 用得到的鍵：`repo`、`sample`、`local_mode`、`workdir`、`hooks_fired`、`github`、`endpoints`、`prod_env`、`backup`

- [ ] **Step 1: 補上 B3 的兩個測試**

在 `tests/test_health_check.py` 追加「Behavior Tests / B3」那兩個測試。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_health_check.py -v`
Expected: FAIL，`No module named 'checks.probes.history'`。

- [ ] **Step 3: 寫第 1 項與第 2 項**

`environment.py`：

```python
"""1 執行環境：本機模式、工作資料夾位置。"""

import platform
from pathlib import Path

from ..model import CheckResult


def probe(facts):
    problems = []
    if facts.get("local_mode") is not True:
        problems.append(
            "現在不是本機模式。雲端模式會讀到舊的檔案內容，而且它回報的檔案時間是對的，"
            "所以從裡面怎麼檢查都查不出來。請到設定關掉「Run new tasks in the cloud」。"
        )
    workdir = Path(facts.get("workdir", Path.cwd()))
    if platform.system() == "Windows" or str(workdir).startswith("\\\\"):
        text = str(workdir)
        if text.startswith("\\\\") or ":" not in text[:2]:
            problems.append("工作資料夾在網路磁碟上，Cowork 不支援。請搬到 C:\\Users\\ 底下。")
    return CheckResult(
        id="environment",
        title="執行環境",
        ok=not problems,
        detail="；".join(problems) or f"本機模式，工作資料夾在 {workdir}",
    )
```

`toolchain.py`：

```python
"""2 工具鏈：Python、git、SQLite 版本。"""

import sqlite3
import sys

from .._shim import run
from ..model import CheckResult

MIN_SQLITE = (3, 27, 0)


def probe(facts):
    problems = []
    if sys.version_info < (3, 10):
        problems.append(f"Python 太舊（{platform_version()}），需要 3.10 以上。")
    version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    if version < MIN_SQLITE:
        problems.append(
            f"SQLite 是 {sqlite3.sqlite_version}，備份用的功能需要 3.27.0 以上。"
        )
    code, out, _ = run(["git", "--version"], cwd=".")
    if code != 0:
        problems.append("找不到 git。")
    return CheckResult(
        id="toolchain",
        title="工具鏈",
        ok=not problems,
        detail="；".join(problems)
        or f"Python {platform_version()}、SQLite {sqlite3.sqlite_version}、{out.strip()}",
    )


def platform_version():
    return ".".join(str(part) for part in sys.version_info[:3])
```

`plugins/starter-kit/checks/_shim.py` 讓 checks 用得到 hook 的共用函式：

```python
"""Re-export the hook helpers so checks and hooks share one implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from _shared import repo_root, run  # noqa: E402,F401
```

- [ ] **Step 4: 寫第 3、4、5 項**

`suite.py`：

```python
"""3 測試綠且 30 秒內跑完。"""

import time
from pathlib import Path

from .._shim import run
from ..model import CheckResult

BUDGET_SECONDS = 30


def probe(facts):
    root = Path(facts.get("repo", "."))
    runner = root / "scripts" / "run_tests.sh"
    if not runner.exists():
        return CheckResult(
            id="suite", title="測試", ok=False,
            detail="這個專案還沒有測試入口，所以沒有任何東西在保護你。",
        )
    started = time.monotonic()
    code, out, err = run(["sh", str(runner)], cwd=root, timeout=300)
    elapsed = time.monotonic() - started
    if code != 0:
        return CheckResult(id="suite", title="測試", ok=False,
                           detail=(out + err)[-800:])
    if elapsed >= BUDGET_SECONDS:
        return CheckResult(
            id="suite", title="測試", ok=False,
            detail=f"測試是綠的，但跑了 {elapsed:.1f} 秒，超過 {BUDGET_SECONDS} 秒。",
            hint="每輪對話結束都會跑一次，太慢會讓每次對話都卡住。",
        )
    return CheckResult(id="suite", title="測試", ok=True,
                       detail=f"全綠，{elapsed:.1f} 秒。")
```

`safety_net.py`：

```python
"""4 保命繩通電：三個 hook 是不是真的會跑。

安裝了不等於會跑。Cowork 官方文件沒有講它的 VM 裡哪些 hook 事件會觸發，
所以這一項驗的是實際跑過的痕跡，不是設定檔的內容。
"""

from ..model import CheckResult

EXPECTED = {
    "SessionStart": "每次對話開始載入行為設定",
    "PreToolUse": "阻止密鑰被寫進檔案",
    "Stop": "測試綠了才存檔",
}


def probe(facts):
    fired = set(facts.get("hooks_fired", []))
    missing = [f"{name}（{what}）" for name, what in EXPECTED.items() if name not in fired]
    if missing:
        return CheckResult(
            id="safety_net",
            title="三道保命繩",
            ok=False,
            detail="這幾道沒有通電：" + "；".join(missing),
            hint="沒通電代表保護是假的，不要在這個狀態下繼續做正式的東西。",
        )
    return CheckResult(
        id="safety_net", title="三道保命繩", ok=True, detail="三道都通電了。"
    )
```

`history.py`：

```python
"""5 git 歷史抽驗：任一個 commit checkout 出來都是綠的。

Each commit is checked out into a throwaway worktree under a temporary
directory. The user's working folder is never touched — checking it out in
place would fail on a dirty tree, or strand the repository on a detached
HEAD with their work apparently gone.
"""

import random
import shutil
import tempfile
from pathlib import Path

from .._shim import run
from ..model import CheckResult


def probe(facts):
    root = Path(facts.get("repo", "."))
    sample = int(facts.get("sample", 3))
    code, out, _ = run(["git", "rev-list", "HEAD"], cwd=root)
    if code != 0:
        return CheckResult(id="history", title="歷史版本", ok=False,
                           detail="讀不到 git 歷史。")

    commits = out.split()
    chosen = commits if len(commits) <= sample else random.sample(commits, sample)
    broken = []
    scratch = Path(tempfile.mkdtemp(prefix="health-history-"))
    try:
        for commit in chosen:
            checkout = scratch / commit[:7]
            code, _, err = run(
                ["git", "worktree", "add", "--detach", "-q", str(checkout), commit],
                cwd=root,
            )
            if code != 0:
                broken.append(f"{commit[:7]}（取不出來：{err.strip()[:80]}）")
                continue
            try:
                runner = checkout / "scripts" / "run_tests.sh"
                if not runner.exists():
                    continue
                code, _, _ = run(["sh", str(runner)], cwd=checkout, timeout=300)
                if code != 0:
                    broken.append(commit[:7])
            finally:
                run(["git", "worktree", "remove", "--force", str(checkout)], cwd=root)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        run(["git", "worktree", "prune"], cwd=root)

    return CheckResult(
        id="history", title="歷史版本",
        ok=not broken,
        detail=f"回不去的版本：{', '.join(broken)}" if broken
        else f"抽驗 {len(chosen)} 個版本，都跑得起來。",
    )
```

- [ ] **Step 5: 跑測試，確認 B3 轉綠**

Run: `python3 -m pytest tests/test_health_check.py -v`
Expected: `test_history_probe_reports_green_when_every_commit_passes` 與 `test_history_probe_names_the_commit_that_fails` PASS。

- [ ] **Step 6: 寫第 6、8、9 項**

`github.py`：

```python
"""6 GitHub：repo 存在，而且 Actions 至少成功跑過一次。"""

from ..model import CheckResult


def probe(facts):
    info = facts.get("github", {})
    if not info.get("repo"):
        return CheckResult(id="github", title="GitHub", ok=False,
                           detail="還沒有對應的 repo。")
    if info.get("last_conclusion") != "success":
        return CheckResult(
            id="github", title="GitHub", ok=False,
            detail=f"{info['repo']} 有了，但 Actions 最近一次是 "
                   f"{info.get('last_conclusion') or '從來沒跑過'}。",
        )
    return CheckResult(id="github", title="GitHub", ok=True,
                       detail=f"{info['repo']}，Actions 最近一次成功。")
```

`service.py`：

```python
"""8 兩個環境活著，而且正式環境的設定是安全的。"""

from ..model import CheckResult

TEMPLATE_DEFAULT_KEY = "django-insecure-CHANGE-ME"


def probe(facts):
    endpoints = facts.get("endpoints", {})
    env = facts.get("prod_env", {})
    problems = []
    for name in ("staging", "prod"):
        status = endpoints.get(name)
        if status != 200:
            problems.append(f"{name} 回 {status or '連不上'}，不是 200。")
    if env.get("DJANGO_DEBUG") == "1":
        problems.append("正式環境的 DEBUG 是開的。")
    key = env.get("DJANGO_SECRET_KEY", "")
    if not key or key == TEMPLATE_DEFAULT_KEY or key.startswith("django-insecure-"):
        problems.append("正式環境的 SECRET_KEY 還是預設值或空的。")
    if "*" in [h.strip() for h in env.get("DJANGO_ALLOWED_HOSTS", "").split(",")]:
        problems.append("正式環境的 ALLOWED_HOSTS 含有萬用字元。")
    return CheckResult(
        id="service", title="兩個環境", ok=not problems,
        detail="；".join(problems) or "staging 與 prod 都回 200，正式環境設定安全。",
    )
```

`data.py`：

```python
"""9 資料持久性與備份可還原。

這兩件事綁在一起，因為 spec 把它們綁在一起：備份要含的正是重新部署之後
還在的那筆資料。
"""

from ..model import CheckResult


def probe(facts):
    info = facts.get("backup", {})
    marker = info.get("marker")
    problems = []
    if not marker:
        problems.append("還沒有寫過測試資料，沒辦法確認資料會不會不見。")
    elif not info.get("survived_redeploy"):
        problems.append("寫進去的資料在重新部署之後不見了，代表 volume 沒掛好。")
    if not info.get("release_tag"):
        problems.append("備份還沒成功跑過一次。")
    elif not info.get("snapshot_opens"):
        problems.append("最新的備份檔打不開。")
    elif marker and marker not in info.get("snapshot_rows", []):
        problems.append("備份檔打得開，但裡面沒有那筆測試資料。")
    return CheckResult(
        id="data", title="資料安全", ok=not problems,
        detail="；".join(problems)
        or f"資料撐過重新部署，備份 {info['release_tag']} 打得開而且找得到那筆資料。",
    )
```

- [ ] **Step 7: 跑測試**

Run: `python3 -m pytest tests/test_health_check.py -v`
Expected: 除 `test_the_report_covers_all_nine_items` 外全過（第 7 項在 Task 13）。

- [ ] **Step 8: Commit**

```bash
git add plugins/starter-kit/checks tests/test_health_check.py
git commit -m "feat: add eight health probes that each fail on their own"
```

---

### Task 13: Zeabur 三層路徑判定

三條路各有各的死法：CLI 最完整但 `zeabur.com` 不在預設白名單、加自訂網域的機制壞了五個月還沒修；MCP 不受網路限制但 26 個工具裡沒有租主機、沒有重新部署、沒有刪除；瀏覽器補得上 MCP 缺的那幾項、也不受網路限制，但對日常操作脆弱。所以不在設計時選路，在安裝時探測。

**Files:**
- Create: `plugins/starter-kit/checks/probes/zeabur.py`
- Modify: `tests/test_health_check.py`

**Interfaces:**
- Consumes: Task 11 的 `CheckResult`
- Produces: `probe(facts)` 讀 `facts["zeabur"]` 的 `cli`、`mcp`、`browser`、`proven` 四個布林值

- [ ] **Step 1: 先寫會失敗的測試**

在 `tests/test_health_check.py` 追加「Behavior Tests / B10」那五個測試。

- [ ] **Step 2: 跑它，確認失敗**

Run: `python3 -m pytest tests/test_health_check.py -v`
Expected: FAIL，`No module named 'checks.probes.zeabur'`。

- [ ] **Step 3: 寫路徑判定**

```python
"""7 Zeabur 走哪一條路。

Ordered by coverage, not by convenience. The CLI does everything; MCP cannot
rent a server, restart, redeploy or delete — and renting is step one of
installation while redeploy is a daily operation; the browser fills exactly
those gaps but is brittle against console redesigns.
"""

from ..model import CheckResult

PATHS = [
    ("cli", "CLI", "全部操作都能做，也最快。"),
    ("mcp", "MCP", "部署、log、環境變數、網域可以做；租主機、重新部署、刪除做不到。"),
    ("browser", "瀏覽器", "MCP 做不到的那幾項靠它，但畫面改版就會壞。"),
]

WHY_BLOCKED = {
    "cli": "CLI：zeabur.com 不在允許連線的清單裡。",
    "mcp": "MCP：連不上 Zeabur 的 MCP 伺服器。",
    "browser": "瀏覽器：Chrome 擴充功能沒有安裝或沒有開啟。",
}


def probe(facts):
    info = facts.get("zeabur", {})
    available = [(key, label, note) for key, label, note in PATHS if info.get(key)]

    if not available:
        return CheckResult(
            id="zeabur", title="Zeabur 操作路徑", ok=False,
            detail="三條路都不通。" + " ".join(WHY_BLOCKED[key] for key, _, _ in PATHS),
            hint="三條全不通就沒辦法部署。先確認 Chrome 擴充功能有沒有裝，那條不受網路限制。",
        )

    key, label, note = available[0]
    if info.get("proven") is False:
        return CheckResult(
            id="zeabur", title="Zeabur 操作路徑", ok=False,
            detail=f"{label} 看起來可用，但還沒有實際跑成功過一次操作，不算數。",
            hint="請用這條路跑一次唯讀操作（例如列出專案）再檢查一次。",
        )
    others = [lbl for k, lbl, _ in available[1:]]
    backup = f"備援還有 {'、'.join(others)}。" if others else "沒有備援。"
    return CheckResult(
        id="zeabur", title="Zeabur 操作路徑", ok=True,
        detail=f"{label} —— {note} 已實際跑成功一次。{backup}",
    )
```

- [ ] **Step 4: 跑測試，確認全綠**

Run: `python3 -m pytest tests/ -v`
Expected: PASS，包含 `test_the_report_covers_all_nine_items`（九項到齊）。

- [ ] **Step 5: Commit**

```bash
git add plugins/starter-kit/checks/probes/zeabur.py tests/test_health_check.py
git commit -m "feat: name the Zeabur path at install time instead of assuming one"
```

---

### Task 14: 安裝嚮導 skill

貼一段 prompt 沒辦法全自動安裝 —— 裝 plugin、裝 connector、改設定都是 UI 動作，Anthropic 刻意鎖在使用者手動同意後面。能做的是一步步帶他點完，並且**把順序寫死**：Zeabur 在 ZeaburOS 沒裝好時建專案只回 `An error occurred, please try again later`，既沒說原因也沒說下一步，非技術者會卡死在那裡。

**Files:**
- Create: `plugins/starter-kit/skills/install-wizard/SKILL.md`

**Interfaces:**
- Consumes: `template/`、`backup-repo/backup.yml`（同目錄）、Task 13 的 Zeabur 路徑判定
- Produces: 使用者的工作資料夾、公開程式碼 repo、私有備份 repo、Zeabur 的 staging 與 prod 兩個服務

- [ ] **Step 1: 寫 SKILL.md**

```markdown
---
name: install-wizard
description: 帶使用者從零裝好整套環境 —— 檢查機器、註冊三個服務、建立專案、部署兩個環境。使用者第一次開始、或說「幫我設定環境」「從頭開始」時使用。
---

# 安裝嚮導

你要帶的人不會寫程式。每一步都先講「這一步在幹嘛」，再講「你要點什麼」。
一次只給一件事做。他做完回報，你才給下一件。

**不要問他任何技術選擇。** 技術棧已經定了：Django、SQLite、GitHub、Zeabur。
他要決定的只有名字、帳號、以及業務規則。

## 順序不能換

Zeabur 的錯誤訊息說不清楚原因，所以順序錯了他會卡死在一個沒有下一步的畫面。

1. **機器行不行** —— 跑官方 readiness check（不用安裝、不用登入）。
   不通過就停在這裡，把原因講清楚，不要讓他裝到一半才發現。
2. **確認是本機模式** —— 設定裡關掉「Run new tasks in the cloud」。
   雲端模式會讀到舊的檔案內容，而且它回報的時間是對的，所以測試會驗到錯的東西。
3. **工作資料夾** —— Windows 必須在 `C:\Users\<他的名字>\` 底下。
   不能用網路磁碟、不能用被搬過位置的「文件」資料夾。
4. **GitHub** —— 註冊、建立一個**公開**的程式碼 repo、再建一個**私有**的備份 repo。
   公開換來無限的 CI 額度；備份放私有的，因為裡面有帳號和密碼。
5. **Zeabur** —— 註冊、儲值、租一台主機、裝 ZeaburOS、**然後才**建專案。
   ZeaburOS 沒裝好就建專案，只會得到一個沒有原因的錯誤。
6. **建立專案** —— 把這個 skill 目錄底下 `template/` 的東西複製到他的工作資料夾。
7. **產生密鑰** —— 用 `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
   產一組 `DJANGO_SECRET_KEY`，設進 Zeabur 的環境變數。**不要寫進任何檔案。**
8. **接上部署** —— `develop` 分支接 staging，`main` 分支接 prod。
9. **抄下兩組 ID** —— 開啟正式環境那個服務的頁面，從網址列抄下服務 ID 與
   環境 ID。**CLI 沒有任何指令列得出環境 ID**，只能從網址抓，所以這一步不能跳。
10. **備份** —— 把 `backup-repo/backup.yml` 放進私有 repo 的 `.github/workflows/`，
    設定 `ZEABUR_API_TOKEN` 這個 secret，以及 `ZEABUR_SERVICE_ID`、`ZEABUR_ENV_ID`、
    `CODE_REPO` 三個變數。`backup-repo/README.md` 也一起放進去。
11. **跑一次環境健檢** —— 用 health-check skill，九項全綠才算裝完。

## Zeabur 怎麼操作

不要假設任何一條路可用。先讓 health-check skill 探測，它會告訴你走 CLI、
MCP 還是瀏覽器。**直接用 `npx zeabur` 或 `curl` 打 Zeabur 的網址，失敗訊息
不會提到網路限制，沒有人查得出原因。**

## connector

GitHub 與 Google 的 connector 要他自己在設定裡連。授權畫面會跳出來要他登入 ——
那是正常的，那個畫面是 GitHub 或 Google 的，不是我們的。
```

- [ ] **Step 2: 確認樣板複製得到**

Run: `python3 -c "from pathlib import Path; p=Path('plugins/starter-kit/skills/install-wizard/template'); print(len(list(p.rglob('*'))), 'files')"`
Expected: 印出一個大於 25 的數字，遠低於 plugin 的 5000 檔上限。

- [ ] **Step 3: Commit**

```bash
git add plugins/starter-kit/skills/install-wizard/SKILL.md
git commit -m "feat: add the install wizard with the order that avoids dead ends"
```

---

### Task 15: 環境健檢 skill

**Files:**
- Create: `plugins/starter-kit/skills/health-check/SKILL.md`
- Create: `plugins/starter-kit/checks/collect.py`

**Interfaces:**
- Consumes: Task 11–13 的 `run_all`、`PROBES`、`render_html`、`render_json`
- Produces: `collect.py` 的 `main()` 讀一份 facts JSON、跑九項、寫出 `reports/health-check.html` 與 `reports/health-check.json`

- [ ] **Step 1: 寫 facts 收集入口**

`plugins/starter-kit/checks/collect.py`：

```python
"""Turn a facts file into the health report.

The skill gathers what the shell cannot see — whether this is local mode,
whether MCP answers, whether the browser extension is there — and writes it
into the facts file. Everything else the probes find for themselves.
"""

import json
import sys
from pathlib import Path

from .render import render_html, render_json
from .runner import run_all


def main(facts_path, out_dir):
    facts = json.loads(Path(facts_path).read_text("utf-8"))
    results = run_all(facts)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "health-check.html").write_text(render_html(results), encoding="utf-8")
    (out / "health-check.json").write_text(render_json(results), encoding="utf-8")
    red = [r for r in results if not r.ok]
    for item in red:
        print(f"紅：{item.title} —— {item.detail}")
    print(f"\n九項裡有 {len(results) - len(red)} 項是綠的。")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
```

- [ ] **Step 2: 寫 SKILL.md**

```markdown
---
name: health-check
description: 跑一輪環境健檢，吐一張九項綠燈報告。使用者說「檢查環境」「看看有沒有問題」「裝好了嗎」，或安裝流程走到最後時使用。
---

# 環境健檢

九項檢查。**每一項都獨立**，一項紅了其他項照常給結果 —— 一份產不出來的報告
等於什麼都沒檢查。

## 你要先探測的四件事

shell 看不到這些，所以你要自己探完，寫進 facts 檔：

| 要探的 | 怎麼探 |
|---|---|
| 現在是不是本機模式 | 看設定，或問使用者確認「Run new tasks in the cloud」是關的 |
| 三個 hook 有沒有真的跑過 | 寫一個檔案、結束一輪，看行為有沒有發生 |
| Zeabur 三條路 | CLI：跑一次 `zeabur project list`。MCP：呼叫一次它的唯讀工具。瀏覽器：確認 Chrome 擴充功能能開 Zeabur 的畫面 |
| Zeabur 那條路實際跑成功過沒有 | 用選中的那條跑一次唯讀操作，成功才把 `proven` 設成 true |

## 然後

把探到的東西寫成 facts JSON，跑：

    python3 -m checks.collect facts.json reports/

報告在 `reports/health-check.html`。**用他看得懂的話講紅的那幾項**，
不要把 JSON 貼給他。

## 講結果的方式

綠的一句話帶過。紅的要講三件事：哪裡不對、會有什麼後果、下一步做什麼。
不要用「請檢查您的設定」這種話 —— 他不知道要檢查什麼。
```

- [ ] **Step 3: 跑一次確認出得了報告**

Run:
```bash
cd plugins/starter-kit
echo '{"local_mode": true, "hooks_fired": ["SessionStart","PreToolUse","Stop"], "zeabur": {"cli": true, "proven": true}}' > /tmp/facts.json
python3 -m checks.collect /tmp/facts.json /tmp/reports
```
Expected: 印出數項紅的（因為沒有真的專案），最後一行是「九項裡有 N 項是綠的。」，且 `/tmp/reports/health-check.html` 開得起來。

- [ ] **Step 4: Commit**

```bash
git add plugins/starter-kit/checks/collect.py plugins/starter-kit/skills/health-check
git commit -m "feat: turn the probes into a report a non-technical reader can act on"
```

---

### Task 16: 想清楚再做 skill

改造自 [mattpocock/skills](https://github.com/mattpocock/skills) 的 `grill-with-docs`（MIT）。原版是 `grilling` 加 `domain-modeling` 的組合，寫給工程師，四處要改：技術問題翻譯成業務問題再問、`CONTEXT.md` 用繁中、ADR 的「為什麼」用白話、語氣改掉 —— relentless 對工程師是優點，對非技術者是壓迫感。

**Files:**
- Create: `plugins/starter-kit/skills/think-first/SKILL.md`
- Create: `plugins/starter-kit/skills/think-first/CONTEXT-FORMAT.md`
- Create: `plugins/starter-kit/skills/think-first/ADR-FORMAT.md`

**Interfaces:**
- Consumes: Task 8 的 `behavior/forbidden-questions.md`、Task 3 的 `check_glossary.py` 讀得懂的 `CONTEXT.md` 格式
- Produces: 使用者專案裡的 `CONTEXT.md` 與 `docs/adr/NNNN-slug.md`

- [ ] **Step 1: 寫 SKILL.md**

```markdown
---
name: think-first
description: 在動手做之前，把使用者模糊的想法問清楚，同時把講定的詞寫進 CONTEXT.md、把難以回頭的決定寫成 ADR。使用者提出一個新功能或新專案、或說「我想做一個…」時使用。
---

# 想清楚再做

一次問一輪。每輪問的是**現在就答得出來**的問題 —— 答案還要等別的問題才能定的，
留到下一輪。

## 只問他答得出來的問題

技術決策底下藏著業務取捨的，翻譯成業務問題來問。翻譯的樣子：

| 不要這樣問 | 要這樣問 |
|---|---|
| 要 soft delete 還是 hard delete？ | 員工離職之後，他填過的班表要保留還是消失？ |
| 用 SQLite 還是 PostgreSQL？ | 最多多少人同時用？會開放給公司外的人嗎？ |
| 要不要做權限系統？ | 除了員工和主管，還有第三種人嗎？ |
| 要不要加 audit log？ | 排好的班被改了，需要知道是誰改的嗎？ |

底下**沒有**業務取捨的，自己決定，寫一則 ADR，然後告訴他你決定了什麼 ——
不要求他確認。禁問的清單在 `behavior/forbidden-questions.md`。

**檢查點**：翻譯不出業務問題，代表你還沒想清楚這個決策會影響什麼。回頭再想，
不要當作「沒有業務取捨」跳過。

**翻譯是有損的**：翻完要自問「他的答案夠不夠支撐這個技術決策」，不夠就補問。

**交互後果自己接住**：要能查「誰改的」加上離職帳號要保留，等於稽核紀錄會指向
已經離職的人，所以那些帳號真的不能刪。這是從兩個業務答案推出來的技術後果，
不要再回頭問他。

## 語氣

不要連珠炮。他不是在被考試，他是在想事情。一輪問完等他，他答得含糊就換個
講法再問一次，不要逼他。

## 邊講邊寫

詞一講定就寫進 `CONTEXT.md`，不要等到最後。格式見 [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md)。

**`CONTEXT.md` 是他唯一看得懂、也唯一有資格審查的技術產物。** 他今天說「員工」、
明天說「同事」、後天說「人員」，你每次照字面理解，系統裡就會長出三張表 ——
而他永遠不會發現，因為他看不懂程式碼。所以他換講法的時候要當場指出來：
「你剛剛說的『同事』，是我們之前講的『員工』嗎？」

難以回頭的決定寫成 ADR，格式見 [ADR-FORMAT.md](./ADR-FORMAT.md)。
```

- [ ] **Step 2: 寫兩份格式檔**

`CONTEXT-FORMAT.md` 定義的格式必須跟 Task 3 的 `check_glossary.py` 對得上 ——
`## 語言` 段落底下，每個詞寫成 `**詞**：` 開頭的一行，接一到兩句定義。
另外要求：測試的 docstring 提到這些詞的時候用 `「」` 框起來，這樣報告上的詞
才驗得到。

`ADR-FORMAT.md`：檔名 `docs/adr/NNNN-slug.md`，內容一到三句話講清楚
「當時的情況、決定了什麼、為什麼」。**「為什麼」要用白話** —— 不是
「to avoid N+1 queries」，是「這樣資料變多的時候不會變慢」。

- [ ] **Step 3: 確認格式對得上檢查腳本**

Run:
```bash
cd plugins/starter-kit/skills/install-wizard/template
python3 -c "
import sys; sys.path.insert(0,'scripts')
from check_glossary import defined_terms
print(defined_terms(open('CONTEXT.md',encoding='utf-8').read()))
"
```
Expected: `{'紀錄'}`。

- [ ] **Step 4: Commit**

```bash
git add plugins/starter-kit/skills/think-first
git commit -m "feat: adapt the grilling flow for someone who cannot read the code"
```

---

### Task 17: 部署 skill

**Files:**
- Create: `plugins/starter-kit/skills/deploy/SKILL.md`

**Interfaces:**
- Consumes: Task 13 的路徑判定、Task 5 的 `check_deploy.py`、Task 4 的 `zeabur.yaml`
- Produces: 無新程式碼；這個 skill 是流程

- [ ] **Step 1: 寫 SKILL.md**

```markdown
---
name: deploy
description: 把改好的東西送上線 —— 先上測試環境看，確認沒問題再上正式版。使用者說「上線」「發布」「讓大家可以用」時使用。
---

# 上線

## 流程

1. 測試綠了嗎？不綠就先修，不要問他要不要硬上。
2. 跑 `python3 scripts/check_deploy.py`。有問題就修，別上。
3. push 到 `develop` → 自動上 staging。
4. **給他 staging 的網址，請他自己看一眼。**
5. 他說對了，才 merge 到 `main` → 上正式版。

## 上正式版一定要問

他不會用 PR，所以 merge 由你代做。但「上正式版」屬於對外發布，要停下來問。
問法：

> staging 看起來對嗎？對的話我就把它變成正式版了。

**不要**在他還沒回答之前 merge。

## Zeabur 怎麼碰

先確認健檢報告說走哪一條路（CLI／MCP／瀏覽器）。**不要假設哪條可用** ——
被擋掉的 `npx zeabur` 或 `curl` 的錯誤訊息不會提到網路限制，查不出原因。

如果要重新部署：MCP 做不到，走 CLI 或瀏覽器。

## 資料庫改動

`manage.py migrate` 在容器啟動的時候自己會跑，不要放進 GitHub Actions ——
Actions 碰不到容器裡的資料庫檔案。

## log 只留 48 小時

他週五出問題、週一才講，log 已經沒了。遇到這種情況直接跟他說查不到，
不要假裝在查。
```

- [ ] **Step 2: Commit**

```bash
git add plugins/starter-kit/skills/deploy
git commit -m "feat: add the deploy flow that stops before going public"
```

---

### Task 18: 開場白與走查文件

**Files:**
- Create: `docs/onboarding/kickoff-prompt.md`
- Create: `docs/onboarding/walkthrough.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: 前面全部
- Produces: 一段可以直接複製貼上的文字，以及一份從零走到完成的文件

- [ ] **Step 1: 寫開場白**

`docs/onboarding/kickoff-prompt.md` 的內容要能直接複製。它必須**自帶最小的行為指示**，
因為貼進去的當下 plugin 還沒裝，三支柱還沒生效：

```markdown
我完全沒有寫過程式，想用你幫我做一個公司內部要用的小工具。

請你：
- 用繁體中文跟我講話，不要用術語。真的要用的時候，第一次出現先用括號解釋一句。
- 不要問我技術問題。要用什麼資料庫、什麼框架、檔案放哪裡，你直接決定就好，
  決定完告訴我一聲。
- 需要我決定的，請換成我答得出來的問法 —— 講我的工作，不要講程式。
- 讀檔案、寫檔案、跑測試你直接做。只有要刪東西、或要讓公司以外的人看到的時候，
  停下來問我。

第一件事：請幫我裝一個叫 starter-kit 的環境包。
到側邊欄的 Customize → Plugins → Personal plugins 按「+」→ Add marketplace，
輸入 WeihaoLiTW/ai-project-starter，然後裝 starter-kit。
裝好之後，請帶我跑安裝嚮導。
```

- [ ] **Step 2: 寫走查文件**

`docs/onboarding/walkthrough.md`：從零到九項全綠的每一步，含每一步要看到什麼畫面、
出錯了怎麼辦。**這份文件是成功條件 #12 的受測物** —— 走查的規則是只照文件做，
每一次發現自己動用文件外的知識就記一筆缺陷，不當場修，繼續走完，最後一起修再重跑。

必須寫進去的坑（全部來自實測）：

| 坑 | 文件要寫什麼 |
|---|---|
| Windows 用 `.exe` 裝會得到沒有 Cowork 的 Claude | 一定要用 `.msix`，而且要系統管理員權限 |
| Zeabur 共享叢集已經停了 | 一定要先租主機 |
| ZeaburOS 沒裝就建專案 | 只會回 `An error occurred, please try again later`，順序不能換 |
| 2 GB 的機器跑不動 | ZeaburOS 加 K3s 加兩個空容器就吃掉 1503 MB / 3659 MB |
| 沒掛 volume 之前寫的資料會不見 | volume 要在第一次啟動前掛好 |
| Zeabur 自訂網域不驗證所有權 | 打錯字不會當場報錯，要等連不上才發現 |
| 自訂網域白名單失效 | 加了也可能還是被擋，這是平台的問題，不是你設錯 |
| Chat 的記憶不會帶進 Cowork | 兩邊是分開的。在 Chat 講過的事，到 Cowork 要重講一次 |
| Cowork 的記憶看不到也改不掉 | 所以重要的結論都寫在 `CONTEXT.md`、`docs/adr/`、`CLAUDE.md` 這三個檔案裡，那才是真相 |

- [ ] **Step 3: 更新 README 的 Roadmap**

把 `README.md` 的 Roadmap 從六個「未開始」章節，改成指向 `docs/onboarding/` 與
`docs/superpowers/specs/`，並說明這個 repo 同時是 marketplace。

- [ ] **Step 4: 跑一次完整測試**

Run: `python3 -m pytest tests/ -v`
Expected: PASS，50 個測試函式、55 個案例全綠。

- [ ] **Step 5: Commit**

```bash
git add docs/onboarding README.md
git commit -m "docs: add the prompt to paste and the walkthrough it has to survive"
```

---

## 收尾：這份計畫走完之後還剩什麼

實作全部完成、34 個測試全綠之後，**還有九件事只能人工驗**，清單在上面的
「需人工驗證的條件」。其中兩件會決定要不要回頭改設計：

1. **Task 1 Step 8 的三個 Cowork 平台假設。** `Stop` hook 不會觸發的話，
   整個保命繩設計不成立，要回頭改 spec。這是唯一一個「沒過就不能往下做」的檢查點。
2. **成功條件 #12 的走查。** 它測的是文件，不是程式，而且走查者知道太多這件事
   在這裡是優點 —— 每動用一次文件外的知識，就精準定位到一個文件缺口。
