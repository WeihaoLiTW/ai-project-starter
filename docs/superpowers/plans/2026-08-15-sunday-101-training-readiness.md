# 週日 101 訓練備妥包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓週日(2026-08-16)半天的 101 訓練站得住 —— 一條排練過的 demo、學員能自助跑通的本機路徑、五個概念材料。

**Architecture:** 建立在現有 Zeabur kit 之上。學員路徑是 install-wizard 的「本機檔位」(只到本機 + GitHub);demo 是主講者在 CLI 上手動建置 + 排練 + 錄影。大部分成功條件是操作/內容,以 `manual` 驗證;唯一自動測試是「學員 prompt 不含 Zeabur/Google」。

**Tech Stack:** Django template(既有)、GitHub Actions、Marp slides、Python(pytest 靜態檢查)。

## Global Constraints

以下每條逐字取自 spec,每個 task 隱含都要遵守:

- 學員表面 = Cowork;demo 表面 = Claude Code CLI;**學員指示不得依賴「照 demo 螢幕做」**。
- **學員路徑不碰 Zeabur、不碰 Google**。
- 本機檔位複製 template 後**必須移除 `deploy-safety` job**(ADR-F),學員公開 repo 的 CI 只剩 `test`。
- 學員 pre-work 硬前提(報名時確認):Claude Pro + Cowork、已開好的 GitHub 帳號。
- **已確認有 Windows 學員** → msix / 系統管理員 / Virtual Machine Platform / `C:\Users\` 工作資料夾檢查為必備,逐台在週日前確認。
- demo 跑通後**必須錄一支成功完整 run 當 fallback**(ADR-D)。
- **週日前**:`WeihaoLiTW/ai-project-starter` 改成 public + 本機檔位 push 上去(否則學員裝不到)。

---

## Traceability(spec 成功條件 → 行為分段 → 測試/manual)

| spec 條件 | 行為分段 | 驗證 |
|---|---|---|
| 1 staging/prod HTTP 200 | 部署後兩環境可連 | **manual**(排練時 `curl -I`) |
| 2 prod 內容含改動字串 | 改動經 staging→prod 後在 prod 可見 | **manual**(排練) |
| 3 存在成功錄影 | fallback 錄影存在 | **manual**(檔案存在) |
| 4 乾淨帳號跑通全milestone + 禁問=0 | 學員 end-to-end 走通 | **manual**(真帳號 dry-run);CI 綠依賴 B1 |
| 5 微練習 ≤10 分鐘 | 改字串→測→綠→commit 可快速完成 | **manual**(計時 dry-run) |
| 6 學員指示不含 Zeabur/Google | 學員貼的 prompt paste block 乾淨 | **B1(自動測試)** |
| 7 概念材料 5 概念各有講法+demo 時刻+名詞白話 | 概念材料完整可懂 | **manual**(靜態審閱) |
| 8 學員指示不依賴 demo 螢幕 | 學員指示能獨立照做 | **manual**(靜態審閱) |
| ADR-F 本機檔位 CI 無 deploy-safety | 學員 push 後 Actions 全綠 | **manual**(dry-run 觀察);B1 檢查 prompt 走本機檔位 |

自動測試只有 **B1**;其餘為 `manual`,清單見文末,收尾時逐條點名。

---

## File Structure

- `docs/onboarding/kickoff-prompt-local.md`(新增)—— 學員貼的「本機檔位」開場白;含一段學員 paste block(不得出現 Zeabur/Google)。
- `plugins/starter-kit/skills/install-wizard/SKILL.md`(修改)—— 加「本機檔位(local mode)」段:只走本機+GitHub 步驟、跳過 Zeabur/Google、複製 template 後移除 `deploy-safety` job。
- `tests/test_student_local_prompt.py`(新增)—— B1:抽出 `kickoff-prompt-local.md` 的 paste block,斷言不含 Zeabur/Google、且要求本機檔位。
- `docs/onboarding/prework.md`(新增)—— 學員 pre-work 前提 + Windows 逐台檢查清單。
- `docs/onboarding/demo-run-of-show.md`(新增)—— demo 排練腳本 + 建置順序 + 錄影步驟。
- `slides-output/2026-08-15-concepts/`(新增)—— 五概念 slides(併入既有 `slides-output/2026-08-15-data-io-focus/`)。
- (選配 P2)`plugins/starter-kit/skills/install-wizard/template/core/views.py` + `.../tests/test_starter.py`(修改)—— SVG 圖表範例 + 測試。

---

## Task 1 — 學員本機檔位(P0,學員路徑的核心)

**Files:**
- Create: `docs/onboarding/kickoff-prompt-local.md`
- Modify: `plugins/starter-kit/skills/install-wizard/SKILL.md`(加「本機檔位」段)
- Test: `tests/test_student_local_prompt.py`

**Interfaces:**
- Produces: `docs/onboarding/kickoff-prompt-local.md`,內含一個 ` ```markdown ` fenced paste block(學員整段複製貼進 Cowork 的內容)。
- Consumes: 既有 `docs/onboarding/kickoff-prompt.md` 的結構、`install-wizard/SKILL.md` 的 13 步。

- [ ] **Step 1: 寫 B1 失敗測試**

```python
# tests/test_student_local_prompt.py
import re
from pathlib import Path

PROMPT = Path("docs/onboarding/kickoff-prompt-local.md")


def _paste_block(text: str) -> str:
    # The student copies exactly one fenced ```markdown block; the test
    # asserts on that block only, so explanatory prose around it may still
    # name Zeabur/Google while the pasted instructions stay clean.
    m = re.search(r"```markdown\n(.*?)```", text, re.DOTALL)
    assert m, "kickoff-prompt-local.md must contain one ```markdown paste block"
    return m.group(1)


def test_student_paste_block_has_no_deploy_or_google_steps():
    block = _paste_block(PROMPT.read_text(encoding="utf-8"))
    assert "Zeabur" not in block, "student paste block must not mention Zeabur"
    assert "Google" not in block, "student paste block must not mention Google"


def test_student_paste_block_requests_local_mode():
    block = _paste_block(PROMPT.read_text(encoding="utf-8"))
    assert "本機檔位" in block, "student paste block must ask for local mode"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `pytest tests/test_student_local_prompt.py -v`
Expected: FAIL(檔案不存在 / paste block 缺)

- [ ] **Step 3: 寫 `docs/onboarding/kickoff-prompt-local.md`**

參照既有 `kickoff-prompt.md` 的結構(貼前三件事 + 一個 ```markdown paste block)。paste block 內容要點:繁中、不問技術、讀寫檔跑測試直接做、**第一件事請 Claude 走 starter-kit 的「本機檔位」安裝(只到本機 + GitHub,不碰部署)**。paste block 內**不得出現 Zeabur、Google**。貼之前三件事要含:必須 Cowork、需 Pro 方案、需先有 GitHub 帳號。

- [ ] **Step 4: 在 `install-wizard/SKILL.md` 加「本機檔位(local mode)」段**

明列本機檔位只走既有 13 步的:1 readiness check、2 本機模式、3 工作資料夾、4 GitHub(只建**一個公開 code repo**,不建私有備份 repo)、6 複製 template、7 裝套件、push 到 GitHub 看 CI 綠。**跳過**第 5、8-12 與 Google connector。**複製 template 後,刪掉 `.github/workflows/tests.yml` 裡的 `deploy-safety` job**,只留 `test`(理由:學員不設部署 secret,留著會紅 X,見 ADR-F)。

- [ ] **Step 5: 跑測試確認通過**

Run: `pytest tests/test_student_local_prompt.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docs/onboarding/kickoff-prompt-local.md plugins/starter-kit/skills/install-wizard/SKILL.md tests/test_student_local_prompt.py
git commit -m "feat: student local-only install path (kickoff prompt + wizard local mode)"
```

---

## Task 2 — Pre-work 文件(P0,學員前提)

**Files:**
- Create: `docs/onboarding/prework.md`

- [ ] **Step 1: 寫 `docs/onboarding/prework.md`**

兩個硬前提(報名時確認):(1) Claude Pro + Cowork 可用;(2) 已開好 GitHub 帳號。Windows 學員逐台檢查:用 `.msix` 安裝、有系統管理員權限、開了 Virtual Machine Platform、工作資料夾在 `C:\Users\<使用者>\` 底下(不可網路磁碟/被重導向的 Known Folder)。每項寫成學員/你可逐條打勾的清單。

- [ ] **Step 2: Commit**

```bash
git add docs/onboarding/prework.md
git commit -m "docs: student pre-work prerequisites and Windows install checklist"
```

*(驗證:條件 4/5 的 dry-run 前提 —— manual。)*

---

## Task 3 — 五概念材料(P0,訓練主體)

**Files:**
- Create: `slides-output/2026-08-15-concepts/slides.md`(+ 渲染 `slides.html`、`slides-paste.md`)
- 併入既有 `slides-output/2026-08-15-data-io-focus/`(「資料進出」那組當其中一段)

- [ ] **Step 1: 寫五概念 `slides.md`(Marp)**

五個概念各一頁,每頁:一個「不看 code 就懂」的講法 + 一個 demo 時刻。概念:(1) git = 隨時能倒帶(每個 commit 都綠);(2) model 每次重新開始(戳破「以為 Claude 都記得」,persistence 靠 CLAUDE.md/skill/memory);(3) dev→staging→prod;(4) AI 不問你答不出來的技術問題(行為層,排班當訪談範例);(5) 跑真服務要有哪些東西 + 「資料進出」是最難的(併入 data-io-focus 那組)。**每個技術名詞第一次出現加一句白話。**

- [ ] **Step 2: 渲染**

Run: `marp slides.md --html -o slides.html`
Expected: 產出 `slides.html`

- [ ] **Step 3: Commit**

```bash
git add slides-output/2026-08-15-concepts/
git commit -m "docs: five-concept training slides"
```

*(驗證:條件 7(概念+demo 時刻+名詞白話)、條件 8(不依賴 demo 螢幕)—— manual 靜態審閱。)*

---

## Task 4 — Demo run-of-show + 建置 + 錄影(P0,最大風險)

**Files:**
- Create: `docs/onboarding/demo-run-of-show.md`

- [ ] **Step 1: 寫 `docs/onboarding/demo-run-of-show.md`**

固定排練腳本:`改首頁一個字串 → pytest 綠 → commit → push develop → staging 出現該字串 →(停,問「上正式版嗎」)→ merge main → prod 出現該字串`。附:demo app = kit template;改動點 = 首頁一個可見字串;順帶示範「新 session 失憶→讀 CONTEXT.md 接上」。

- [ ] **Step 2:(操作)在 CLI 上把 demo app 從零建到 Zeabur staging + prod**

照 install-wizard 13 步(完整,含 Zeabur)。CLI 上 `zeabur` CLI 走 per-domain approval,大概直通。**順序不能換**:ZeaburOS 先於建專案。

- [ ] **Step 3:(操作)實跑一次完整 loop,驗條件 1、2**

`curl -I` 讀 staging 與 prod → 皆 200(條件 1)。跑完整腳本 → prod 頁面含改動字串(條件 2)。

- [ ] **Step 4:(操作)錄一支成功完整 run 當 fallback(條件 3、ADR-D)**

錄整條腳本跑通的畫面,存成 fallback。現場垮了就放這支。

- [ ] **Step 5: Commit run-of-show 文件**

```bash
git add docs/onboarding/demo-run-of-show.md
git commit -m "docs: demo run-of-show script for the Sunday session"
```

*(驗證:條件 1、2、3 —— manual,於 Step 3/4 完成。)*

---

## Task 5 —(選配 P2)template 加 SVG 圖表範例

只有行有餘力才做。狗狗/朵拉/Bee 都會用到圖表。

**Files:**
- Modify: `plugins/starter-kit/skills/install-wizard/template/core/views.py`
- Test: `plugins/starter-kit/skills/install-wizard/template/tests/test_starter.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_home_page_renders_an_svg_chart(client):
    # A visible chart on the home page: the response body contains an <svg>
    # element and at least one data point (a <polyline> or <rect>), so a
    # non-technical viewer sees a picture, not a table.
    resp = client.get("/")
    body = resp.content.decode()
    assert "<svg" in body
    assert "<polyline" in body or "<rect" in body
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `pytest tests/test_starter.py::test_home_page_renders_an_svg_chart -v`
Expected: FAIL

- [ ] **Step 3: 在 `core/views.py` 的首頁 view 產一段最小 SVG 折線圖**

用固定示範資料點,server-side 拼出 `<svg><polyline .../></svg>`,放進首頁 context 渲染。不引入前端相依。

- [ ] **Step 4: 跑測試確認通過**

Run: `pytest tests/test_starter.py::test_home_page_renders_an_svg_chart -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/starter-kit/skills/install-wizard/template/core/views.py plugins/starter-kit/skills/install-wizard/template/tests/test_starter.py
git commit -m "feat: minimal server-rendered SVG chart example in template"
```

---

## Behavior Tests(自動)

**B1 — 學員 paste block 不含部署/Google 步驟(條件 6)**
`tests/test_student_local_prompt.py`(Task 1)。抽出 `kickoff-prompt-local.md` 的 ```markdown paste block,斷言不含 `Zeabur`、`Google`,且含 `本機檔位`。
期望值來源:spec 條件 6 逐字(「不含任何 Zeabur 或 Google 的註冊/授權步驟」)+ ADR-C。斷言形狀 = invariant(不存在某類字串)。

**B2 —(選配)首頁顯示含資料的 SVG 圖表**
Task 5 的 `test_home_page_renders_an_svg_chart`。期望值來源:「圖表要看得見」= 頁面含 `<svg>` + 一個資料標記。

---

## Gate

**A. 覆蓋**:spec 條件 1-8 + ADR-F 全部在上方 Traceability 有對應分段。條件 6 → B1 自動測試;其餘 → `manual`,已明標。✅

**B. 溯源**:B1 期望值來源 = spec 條件 6 逐字。B2 = 「圖表看得見」。✅

---

## 人工驗證清單(收尾時逐條點名 —— 這是唯一需要人驗的)

- [ ] 條件 1:排練時 `curl -I` staging 與 prod 皆 200
- [ ] 條件 2:跑完 loop 後 prod 頁面含該次改動字串
- [ ] 條件 3:存在一支成功完整 run 的錄影(fallback)
- [ ] 條件 4:乾淨 Cowork+GitHub 帳號照學員 prompt 走通(骨架/綠/commit/push/CI 綠),禁問清單問題 = 0
- [ ] 條件 5:微練習計時 ≤10 分鐘
- [ ] 條件 7:五概念各有講法+demo 時刻+名詞白話(靜態審閱)
- [ ] 條件 8:學員指示不含「照台上畫面做」的依賴(靜態審閱)
- [ ] ADR-F:dry-run 觀察學員 push 後 Actions 全綠(deploy-safety 已移除)
- [ ] 週日前置:repo 改 public、本機檔位已 push 上去(這兩件由你自己在 GitHub 做)

---

## Execution Handoff

計畫已存到
`docs/superpowers/plans/2026-08-15-sunday-101-training-readiness.md`

**提醒:這份大半是操作/內容(建 demo、排練、錄影、真帳號 dry-run、審閱 slides、改 repo public),只有 Task 1、Task 5 是可交給 subagent 的 code。** 加上明天就要用,建議你**自己 inline 執行**(尤其 Task 4 的實機建置與錄影,subagent 做不了),把 Task 1 的 code 部分交我或 subagent 跑。

優先序:Task 1(學員路徑)+ Task 4(demo,最大風險)先行 → Task 2、3(pre-work、slides)→ Task 5 選配。
