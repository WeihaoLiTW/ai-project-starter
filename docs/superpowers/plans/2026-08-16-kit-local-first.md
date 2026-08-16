# starter-kit 本機優先重構 — 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 kit 預設翻成本機優先，刪掉模型本來就會的程序型 skill（deploy、health-check 引擎），把互動 persona 與安全硬停抽進常駐行為，新增 web-design skill，並讓學員第一次只裝本機四樣。

**Architecture:** 刪除 `checks/` 引擎與 deploy/health-check 兩個 skill；新增極簡 `local-template/`（Python + pytest）作為預設骨架；`install-wizard` 改本機優先主線 + opt-in 加購段並關閉自動觸發；`pillars.md` 併入 persona 與安全 wording；Django/Zeabur/backup 資產保留為 opt-in、不動。

**Tech Stack:** Python 3.10、pytest、Claude Code plugin（SKILL.md frontmatter、hooks）、既有 `tests/` 測試框架（`tests/conftest.py` 提供 `run_hook`、`installed_project` fixture）。

## Global Constraints

- 死線：週日訓練前要上。方向是「砍」，每個 task 結束 `pytest tests/ -q` 必須全綠，可隨時停在綠燈。
- 語言：plan 正文與文件 zh-tw；code、註解、commit、frontmatter 值為 English。
- opt-in 部署資產（`plugins/starter-kit/skills/install-wizard/template/`、`zeabur.yaml`、`backup-repo/`、template 內 scripts）**不動**，其既有測試全程保持綠。
- 骨架語言固定 Python + pytest（kit 既有取向；非技術者無選語言依據）。
- 完成信號給學員是口頭「裝好了」；測試只錨可觀察事實。

---

## Traceability（spec 成功條件 → 行為分段 → test）

| Spec SC | 行為分段 | Test |
|---|---|---|
| SC6 | 三個路徑刪除後整套測試仍全綠 | `B6a`（路徑不存在）、`B6b`（`pytest` 全綠，回歸） |
| SC2 | 乾淨資料夾複製骨架+裝相依 → `run_tests.sh` 綠且 <30s | `B2` |
| SC3 | 骨架上改一個檔 → 自動存出恰一個 commit（無需事先設身份） | `B3` |
| SC1 | 跑完本機起點 → git repo 且身份已設 | `manual-1`（wizard 是 NL 指令，非 code） |
| SC5 | install-wizard 標記為不自動觸發 | `B5` |
| SC7 | session start 注入含 persona / 發布前停 / log 老實說 | `B7` |
| SC8 | web-design skill 存在、描述涵蓋做網頁/HTML、可自動觸發 | `B8` |
| SC4 | 學員本機 prompt 純本機且明確叫 install-wizard | `B4a`（無 Zeabur/Google/GitHub）、`B4b`（叫 install-wizard） |
| SC9 | deck 含「首次裝/之後加」兩區塊、每項回扣概念 | `B9` |
| SC10 | opt-in 部署資產仍在且測試綠 | `B10`（既有 template 測試回歸） |
| （使用者要求） | 完成後 before/after 對照可 review | `manual-2`（Task 9 交付物） |
| （spec 驗證） | Cowork 貼 prompt 能否叫起 install-wizard | `manual-3`（Windows 實測 go/no-go） |

---

## Task 1：刪除程序型 skill 與健檢引擎（SC6）

**Files:**
- Delete: `plugins/starter-kit/skills/deploy/`（整個目錄）
- Delete: `plugins/starter-kit/skills/health-check/`（整個目錄）
- Delete: `plugins/starter-kit/checks/`（整個目錄，含 probes）
- Delete: `tests/test_health_check.py`、`tests/test_question_audit.py`
- Modify: `plugins/starter-kit/hooks/hooks.json`（若有引用 checks 的鉤子 → 移除；確認只留 SessionStart/PreToolUse×2/Stop）

- [ ] **Step 1**（marker：behavior test `B6a`/`B6b`，見 Behavior Tests）
- [ ] **Step 2：確認無外部 import 依賴** — 先 `grep -rn "checks" plugins/starter-kit/scripts tests | grep -v test_health_check | grep -v test_question_audit`，確認 `scripts/`、其餘測試都不 import `checks`（探索已確認 `checks/` 獨立，但刪前再驗一次）。
- [ ] **Step 3：刪目錄與測試檔** — 刪上列路徑。
- [ ] **Step 4：跑 `B6a`、`B6b`** — 路徑不存在；`pytest tests/ -q` 全綠。
- [ ] **Step 5：Commit** — `feat: remove deploy and health-check skills and the checks engine`

## Task 2：極簡本機骨架 local-template（SC2）

**Files:**
- Create: `plugins/starter-kit/skills/install-wizard/local-template/scripts/run_tests.sh`
- Create: `plugins/starter-kit/skills/install-wizard/local-template/tests/test_smoke.py`
- Create: `plugins/starter-kit/skills/install-wizard/local-template/pytest.ini`
- Create: `plugins/starter-kit/skills/install-wizard/local-template/conftest.py`（沿用 template 的中文 HTML 報告 plugin，去掉 Django 相依）
- Create: `plugins/starter-kit/skills/install-wizard/local-template/CLAUDE.md`（本機版：不寫死 Django/Zeabur；技術棧待選、綠了才存檔、新功能先 think-first）
- Create: `plugins/starter-kit/skills/install-wizard/local-template/requirements-local.txt`（只 pin `pytest`，版本對齊 template lock）
- Create: `plugins/starter-kit/skills/install-wizard/local-template/.gitignore`（`__pycache__/`、`*.pyc`、`.venv/`、`reports/`）

**Interfaces:**
- Produces：`run_tests.sh` 內容 = `"${PYTHON:-python3}" -m pytest tests/ "$@"`（單行，不含 glossary/ci-superset）。`commit_if_green.py` 已找 `scripts/run_tests.sh`，介面相容。

- [ ] **Step 1**（marker：`B2`）
- [ ] **Step 2：寫 `run_tests.sh`**（見 Interfaces）+ `chmod` 不需要（用 `sh` 呼叫）。
- [ ] **Step 3：寫 `tests/test_smoke.py`**：一個必過測試，docstring 白話。
```python
def test_the_project_runs():
    """這個專案跑得起來。"""
    assert True
```
- [ ] **Step 4：寫 `pytest.ini`**：`[pytest]` / `testpaths = tests` / `python_files = test_*.py` / `addopts = -q`。
- [ ] **Step 5：寫 `conftest.py`**（中文 HTML 報告，複製 template 版並移除 Django import；若原版無 Django 相依則原樣）、`CLAUDE.md`、`requirements-local.txt`、`.gitignore`。
- [ ] **Step 6：跑 `B2`** — 綠且 <30s。
- [ ] **Step 7：Commit** — `feat: add the minimal local-only project scaffold`

## Task 3：install-wizard 改本機優先 + 關自動觸發（SC5、支撐 SC1）

**Files:**
- Modify: `plugins/starter-kit/skills/install-wizard/SKILL.md`（frontmatter + 內文）
- Modify: `.claude-plugin/marketplace.json`、`plugins/starter-kit/.claude-plugin/plugin.json`（description 改本機優先）

- [ ] **Step 1**（marker：`B5`；SC1 標 `manual-1`）
- [ ] **Step 2：frontmatter 加 `disable-model-invocation: true`**，並收窄 `description`（避免返場使用者一句話就觸發；例如「Initialize the starter-kit on first run（僅在使用者要求安裝時）」）。
- [ ] **Step 3：改寫內文主線為本機起點六步**：readiness check → 本機模式 → 工作資料夾 → **git 設定（`git init` + 缺身份就用白話問名字/email 再 `git config`）** → 複製 `local-template/` + `pip install -r requirements-local.txt` → 檢查關鍵幾項後口頭「裝好了」。
- [ ] **Step 4：加「什麼時候加什麼」加購段**：做網頁→複製 Django `template/`（web-design 會自動套）；備份/分享/CI→GitHub public repo + push；上線→Zeabur（現有步驟與資產）。原 13 步併入此段作細節。
- [ ] **Step 5：改兩個 description**（marketplace.json / plugin.json）為本機優先語意。
- [ ] **Step 6：跑 `B5`**（frontmatter 有 disable-model-invocation）+ `pytest tests/ -q` 全綠。
- [ ] **Step 7：Commit** — `feat: make install-wizard local-first and non-auto-invoked`

## Task 4：pillars 併入 persona 與安全 wording（SC7）

**Files:**
- Modify: `plugins/starter-kit/behavior/pillars.md`
- Modify: `plugins/starter-kit/behavior/forbidden-questions.md`（內容併入行為指引語境；保留檔或併進 pillars 由實作定，但內容要進常駐注入）
- Modify（如需）: `plugins/starter-kit/scripts/session_start.py`（若 forbidden-questions 也要注入，讓它一併讀）

**Interfaces:**
- Consumes：`session_start.py` 現在讀 `behavior/pillars.md` 注入（`session_start.py:12,27`）。
- Produces：注入內容須含 persona（白話、翻業務問題、幫他把事做成的立場）、安全硬停（發布前停、log 查不到老實說），以及 forbidden-questions 的禁問精神。問法節奏（一次一輪）**不**進來。

- [ ] **Step 1**（marker：`B7`）
- [ ] **Step 2：pillars 併入 persona 段**（只 persona 立場，不含問法節奏）。
- [ ] **Step 3：pillars 併入安全硬停**：發布前停（強化既有）、log 查不到就老實說別編。
- [ ] **Step 4：把 forbidden-questions 精神併入行為注入**（併進 pillars 或讓 session_start 一併注入 forbidden-questions.md）。
- [ ] **Step 5：跑 `B7`** + `pytest tests/ -q` 全綠（含既有 `test_session_start.py`）。
- [ ] **Step 6：Commit** — `feat: fold persona and safety wording into the always-on behavior`

## Task 5：web-design skill（SC8）

**Files:**
- Create: `plugins/starter-kit/skills/web-design/SKILL.md`

- [ ] **Step 1**（marker：`B8`）
- [ ] **Step 2：寫 frontmatter** — `name: web-design`；`description` 涵蓋「使用者在做網頁／HTML、想讓它好看時使用」（**不設** disable-model-invocation → 可自動觸發）。
- [ ] **Step 3：寫內文原則**（白話、可執行）：版面克制、排版（中文字重/行高/對比）、單一主色、避開 AI 預設感、產出自包含一頁（樣式內嵌、系統字、零外部資源）。
- [ ] **Step 4：跑 `B8`** + `pytest tests/ -q` 全綠。
- [ ] **Step 5：Commit** — `feat: add the web-design skill`

## Task 6：學員本機 prompt 改純本機（SC4）

**Files:**
- Modify: `docs/onboarding/kickoff-prompt-local.md`
- （不動 `docs/onboarding/kickoff-prompt.md` 完整部署版）

- [ ] **Step 1**（marker：`B4a`/`B4b`）
- [ ] **Step 2：改 paste block**：拿掉「連上 GitHub、上傳程式碼」；貼前三件事的 GitHub 那點改「非必要，之後要備份/分享再開」；paste block 明確指示叫 install-wizard 跑本機檔位。
- [ ] **Step 3：跑 `B4a`/`B4b`**（延伸既有 `tests/test_student_local_prompt.py`）。
- [ ] **Step 4：Commit** — `feat: make the student local prompt purely local`

## Task 7：slides deck 更新（SC9）

**Files:**
- Modify: `slides-output/2026-08-15-concepts/deck.html`

- [ ] **Step 1**（marker：`B9`）
- [ ] **Step 2：新增/改寫兩區塊**：「第一次幫你裝什麼（本機四樣）」與「之後你自己能加什麼（三加購）」，每項標注回扣概念（git→01、測試骨架+安全繩→02、行為+hook→05、guard→06、記憶→04；Django+web-design→07/08、GitHub→01/02、Zeabur→03/CASE）。並講「為什麼裝、為什麼分兩批」。維持既有視覺系統（森林綠、系統字、inline SVG、無 emoji/em-dash）。
- [ ] **Step 3：跑 `B9`**（grep deck.html 兩區塊與概念字串）。
- [ ] **Step 4：Commit** — `docs: slides explain what the kit installs first and what you add later`

## Task 8：opt-in 資產回歸確認（SC10）

**Files:** 無修改（純回歸）。

- [ ] **Step 1：跑 `B10`** — 確認 `template/`、`zeabur.yaml`、`backup-repo/` 仍在，且 `test_prod_settings`、`test_template_project`、`test_backup`、`test_ci_superset`、`test_report_glossary` 全綠。
- [ ] **Step 2：若前面任一 task 誤傷資產** → 修回。否則本 task 無 commit。

## Task 9：before/after 對照 + review（使用者要求；`manual-2`）

**Files:**
- Create: `/tmp/kit-before-after.md`（review 載體，不進 repo）

- [ ] **Step 1：寫 before/after 對照**：三張表——(a) 結構樹 before vs after（刪了什麼、加了什麼）、(b) 第一次裝什麼 before（Django+Zeabur 全套）vs after（本機四樣）、(c) 學員體驗 before vs after。
- [ ] **Step 2：跑 `/wli-review-format /tmp/kit-before-after.md`**，把 preview url 給使用者。
- [ ] **Step 3：** 這是交付物、非單元測試 → `manual-2`。

---

## Behavior Tests

> 測試品質照 `superpowers:test-driven-development` 的 `writing-good-tests.md`。每個 test 附 expected value 來源（Gate B）。放 `tests/`，沿用 `tests/conftest.py` 的 `run_hook` 與 fixture。

**B6a — 三個路徑刪除**（→ SC6）
```python
from pathlib import Path
def test_procedural_skills_and_checks_engine_are_gone():
    root = Path(__file__).resolve().parent.parent / "plugins/starter-kit"
    assert not (root / "skills/deploy").exists()
    assert not (root / "skills/health-check").exists()
    assert not (root / "checks").exists()
```
來源：SC6 明列這三個路徑不存在。

**B6b — 刪除後整套綠**（→ SC6）：回歸，執行 `pytest tests/ -q` 收 0。來源：SC6「刪除後 pytest 全綠」。（此為 CI/命令層斷言，非新測試檔。）

**B2 — 骨架乾淨裝起來就綠且快**（→ SC2）
```python
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
```
來源：exit 0 = 綠（run_tests.sh 語意）；30s 門檻鏡射既有 `test_template_project.py` 的 fresh-project 門檻。

**B3 — 骨架上改一個檔就自動存出一個 commit（未先設身份也成立）**（→ SC3）
```python
import shutil, subprocess, sys
from pathlib import Path
from conftest import run_hook  # Stop hook 驅動 commit_if_green
def test_a_change_on_the_scaffold_auto_commits_once(tmp_path):
    src = Path(__file__).resolve().parent.parent / "plugins/starter-kit/skills/install-wizard/local-template"
    proj = tmp_path / "proj"; shutil.copytree(src, proj)
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-local.txt"], cwd=proj, check=True)
    subprocess.run(["git", "init"], cwd=proj, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=proj, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.x"], cwd=proj, check=True)
    (proj / "note.txt").write_text("hi")
    run_hook("commit_if_green.py", {}, cwd=proj)
    log = subprocess.run(["git", "log", "--oneline"], cwd=proj, capture_output=True, text=True).stdout
    assert log.count("\n") == 1
    assert "chore: save a working version" in log
```
來源：commit 訊息字面出自 `commit_if_green.py`（`chore: save a working version`）；「恰一個」出自 SC3。註：身份在測試內先設，對應 wizard 在真實流程會設好；wizard 本身設身份的動作為 `manual-1`。

**B5 — install-wizard 不自動觸發**（→ SC5）
```python
from pathlib import Path
def test_install_wizard_is_not_auto_invoked():
    fm = (Path(__file__).resolve().parent.parent
          / "plugins/starter-kit/skills/install-wizard/SKILL.md").read_text("utf-8")
    assert "disable-model-invocation: true" in fm.split("---", 2)[1]
```
來源：SC5 / ADR-3。

**B7 — 常駐行為含 persona 與安全 wording**（→ SC7）
```python
from conftest import run_hook
def test_session_start_injects_persona_and_safety_wording(tmp_path):
    _, resp, _ = run_hook("session_start.py", {}, cwd=tmp_path)
    ctx = resp["hookSpecificOutput"]["additionalContext"]
    assert "白話" in ctx                     # persona: 講話方式
    assert "業務" in ctx                     # persona: 翻業務問題
    assert "發布" in ctx or "正式版" in ctx  # 安全: 發布前停
    assert "查不到" in ctx                   # 安全: log 老實說
    assert "一次問一輪" not in ctx           # 問法節奏不進常駐（review 決策）
```
來源：SC7 列的三類 + review 留言「問法節奏留 think-first」。關鍵字對應 pillars 應含的條目。

**B8 — web-design skill 存在、描述涵蓋做網頁、可自動觸發**（→ SC8）
```python
from pathlib import Path
def test_web_design_skill_is_present_and_auto_invocable():
    p = Path(__file__).resolve().parent.parent / "plugins/starter-kit/skills/web-design/SKILL.md"
    assert p.exists()
    fm = p.read_text("utf-8").split("---", 2)[1]
    assert "name: web-design" in fm
    assert "description:" in fm
    assert ("網頁" in fm or "HTML" in fm)          # 描述涵蓋做網頁/HTML
    assert "disable-model-invocation: true" not in fm  # 可自動觸發
```
來源：SC8。

**B4a / B4b — 學員本機 prompt 純本機且叫 install-wizard**（→ SC4；延伸既有 `test_student_local_prompt.py`）
```python
import re
from pathlib import Path
def _paste_block():
    md = (Path(__file__).resolve().parent.parent
          / "docs/onboarding/kickoff-prompt-local.md").read_text("utf-8")
    return re.search(r"```(?:markdown)?\n(.*?)```", md, re.S).group(1)
def test_local_prompt_has_no_deploy_or_upload_steps():   # B4a
    b = _paste_block()
    assert "Zeabur" not in b and "Google" not in b and "GitHub" not in b
def test_local_prompt_invokes_the_install_wizard():      # B4b
    assert "install-wizard" in _paste_block()
```
來源：SC4（不出現三者、出現叫 install-wizard）。

**B9 — deck 含兩區塊與概念回扣**（→ SC9）
```python
from pathlib import Path
def test_deck_explains_first_install_and_later_addons():
    html = (Path(__file__).resolve().parent.parent
            / "slides-output/2026-08-15-concepts/deck.html").read_text("utf-8")
    assert "第一次" in html and "之後" in html          # 兩區塊存在
    assert "加購" in html or "自己" in html
    # 每項回扣概念：抽查關鍵配對出現
    assert "git" in html and "測試" in html and "權限" in html
```
來源：SC9（兩區塊 + 回扣概念）。斷言形狀為 invariant（存在性），因 deck 為敘事 HTML，精確字串無意義。

**B10 — opt-in 部署資產回歸**（→ SC10）
```python
from pathlib import Path
def test_optin_deploy_assets_still_present():
    root = Path(__file__).resolve().parent.parent / "plugins/starter-kit/skills/install-wizard"
    assert (root / "template").is_dir()
    assert (root / "template/zeabur.yaml").exists()
    assert (root / "backup-repo").is_dir()
```
來源：SC10；其功能面由既有 `test_prod_settings`/`test_template_project`/`test_backup`/`test_ci_superset` 回歸覆蓋。

---

## 人工驗證清單（Gate B 標記，收尾要點名）

- **`manual-1`（SC1）**：install-wizard 在真實流程 `git init` + 設身份——wizard 是自然語言指令、非 code，不便單元測。手動在暫存資料夾照六步跑一次確認。
- **`manual-2`（Task 9）**：before/after 對照 review 頁,交付物、非測試。
- **`manual-3`（spec 驗證）**：Windows Cowork 貼 `kickoff-prompt-local.md` 的 prompt，驗證能否把 `disable-model-invocation` 的 install-wizard 叫起來。**上線前 go/no-go**：叫不起來就要退回（例如改回可自動觸發或改用 command）——這是 ADR-3 的 Revisit 觸發點。

---

## Self-review（對照 spec）

- SC1–SC10 每條都有行為分段與 test 或明標 manual：SC1→manual-1、SC2→B2、SC3→B3、SC4→B4a/b、SC5→B5、SC6→B6a/b、SC7→B7、SC8→B8、SC9→B9、SC10→B10。無遺漏。
- 無 placeholder：每個 test 有具體 body 與期望值來源。
- 型別/名稱一致：`run_hook`、`commit_if_green.py`、`session_start.py`、`local-template/scripts/run_tests.sh` 與既有 code 對齊。
