# starter-kit 本機優先重構 — 設計

## 背景與目標

現行 kit 一開始就把整套線上部署堆疊（Django + Zeabur + GitHub）當預設，install-wizard 主線是
13 步「從零到部署」，還帶一個九項探針的健檢引擎與一個 deploy skill。對多數學員來說，一開始只需要
在自己電腦上動手做、每一步能測、錯了能回；預裝一堆用不到又看不懂的東西反而是負擔。

這次把預設翻成**本機優先**，並依一條原則大幅瘦身：**kit 只編碼「模型預設不會做的事」，不重複
「模型本來就會的事」。** 怎麼部署、怎麼健檢，模型遇到自然會做，不必用 skill 教；跟非技術者的互動
方式、把技術問題翻成他答得出來的問法、不要做出一看就是 AI 的醜東西、危險動作硬停——這些模型預設
不會做，才是 kit 的價值，而且要常駐在 session start（每次都套）。

**時機**：週日訓練前要上（已定）。這次的方向是「砍」，剛好縮小表面積，對趕死線與當天穩定性有利。

## 設計

### A. 預設 = 本機優先

裝好 kit 後只設本機四樣：
- **git**：`git init` + 設好 `user.name` / `user.email`（安裝時就設，不再是壞了才處理）。
- **行為層**：`pillars.md`（強化後）由 SessionStart hook 每次注入。
- **安全繩**：`commit_if_green.py`（測試綠了才自動存檔）、`guard_danger.py`（擋刪除）、
  `guard_secrets.py`（擋密鑰）。
- **極簡骨架**：`local-template/` — Python + pytest 的一個 trivial 測試 + `run_tests.sh`，讓安全繩
  從第一步就會動。

不碰 Django / GitHub / Zeabur。

### B. 三個加購段（使用者有需求才主動推薦，無 skill 引導，模型現場用資產）

- 「要做網頁」→ 複製 Django `template/`（opt-in 資產）。網頁美化的 `web-design` **不綁這個加購**，只要
  在弄 HTML（含本機 dev）就會自動套。
- 「要備份 / 分享 / CI」→ 建 GitHub public repo + push。
- 「要讓別人用 / 上線」→ Zeabur staging/prod（用現有 `zeabur.yaml`、prod 設定、`backup-repo/`）。

部署資產（Django template、`zeabur.yaml`、`backup-repo/`、template 內 scripts）**保留**成 opt-in，
訓練當天不碰；它們編碼了實測過的非顯而易見設定，刪掉是多做多錯又斷了未來的路。

### C. 刪除（模型本來就會的程序）

- `deploy` skill：整個移除，不留 script。非顯而易見的安全句抽進 `pillars.md`（見 E）。
- `health-check` skill + `checks/` 引擎 + 9 個探針：**完整刪除**。
- 連帶刪除只服務上述的測試：`tests/test_health_check.py`、`tests/test_question_audit.py`。

### D. install-wizard

- 維持 skill，frontmatter 設 `disable-model-invocation: true`（不自動觸發、只有被明確叫才跑）。
- SKILL.md 改寫：主線為本機起點六步，Django/GitHub/Zeabur 收進「什麼時候加什麼」加購段。
- 學員本機 prompt 明確指示叫它。
- 其餘 skill（think-first、web-design）維持可自動觸發。

### E. 常駐行為（session start）強化

`pillars.md` 併入以下「模型預設不會做」的內容，每次注入：
- 互動 persona：用白話跟非技術者講話、把技術決策翻成業務問題、以「幫他把事做成」的立場對話。
  **問法的節奏（一次問一輪、答得含糊就換講法再問）不進常駐行為，留在 think-first。**
- 安全硬停：上正式版＝對外發布，一定停下來問（已有，強化）；log 查不到就老實說「查不到」，不要編。
- `forbidden-questions.md` 的內容併入行為指引（不再有自動稽核探針；guard 靠 session start 常駐，不靠檢查）。

`think-first` skill 保留「深問法」的完整程序（含一次問一輪、換講法再問的節奏）；session start 只帶
persona（怎麼講話、翻業務問題的立場），所以平常對話都用對的口氣，但完整問法要 think-first 被觸發才跑。

### F. web-design skill（新增）

自包含的網頁美化指引。**只要在做網頁/HTML 就會用到，不限上線或加購——本機 dev 剛做出一個頁面時
就該套**（可自動觸發，非 install 加購專屬）。原則（白話、可執行）：版面克制（一個重點其他安靜、
留白夠）、排版（中文字重別太重、行高夠、標題內文對比清楚）、單一主色、避開一看就是 AI 的預設感
（過亮紫藍漸層、三張一樣的卡片）、產出自包含一頁（樣式內嵌、系統字、不依賴外部資源）。

### G. 學員 prompt

`docs/onboarding/kickoff-prompt-local.md` 的 paste block 改成純本機：拿掉 GitHub push；明確叫
install-wizard。完整部署版 `docs/onboarding/kickoff-prompt.md` 保留為「要上線」的版本。

### H. slides 更新

deck 新增/改寫兩區塊，並把每項回扣前面教過的概念：
- 首次幫你裝的（本機四樣）：git→01 git、測試骨架+安全繩→02 測試/CI、行為層+hook→05 prompt、
  guard→06 權限；think-first+記憶→04 記憶。
- 之後自己加的（三加購）：Django+美化→07 服務/08 資料進出、GitHub→01/02 雲端延伸、
  Zeabur→03 env / CASE。
- 講清楚為什麼裝這幾樣、為什麼分兩批。

### I. 完成信號（學員體驗）

Claude 檢查關鍵幾項後，用一句「裝好了」帶過（學員選擇的輕體驗）。**我們要測的成功條件**不依賴那句話，
而是錨在可觀察事實（見「成功定義」1–3）。

## 成功定義（成品層級）

1. 跑完本機起點後，工作資料夾是一個 git repo 且身份已設：`git rev-parse --git-dir` 成功，且
   `git config user.name` 與 `git config user.email` 皆非空字串。
2. `local-template/` 複製到乾淨資料夾、`pip install -r requirements-local.txt` 後，
   `sh scripts/run_tests.sh` exit code = 0，且 < 30 秒完成。
3. 在該資料夾改一個檔並觸發 Stop hook，`commit_if_green` 產出**恰一個** commit（訊息
   `chore: save a working version`）；且此流程在測試前**未手動設過 git 身份**的情況下仍成立
   （因為步驟 4 已設）。
4. `kickoff-prompt-local.md` 的 paste block 文字中**不出現** `Zeabur`、`Google`、`GitHub` 的
   安裝/上傳動作，且**出現**明確叫 install-wizard 的指示。
5. `install-wizard/SKILL.md` frontmatter 含 `disable-model-invocation: true`。
6. `plugins/starter-kit/skills/deploy/`、`plugins/starter-kit/skills/health-check/`、
   `plugins/starter-kit/checks/` 三個路徑**皆不存在**；刪除後 `pytest tests/ -q` 全綠（無殘留
   import 錯誤、無孤兒測試）。
7. `pillars.md` 內容含這三類條目（可用關鍵字斷言，或測 `session_start` 注入內容含之）：互動核心原則、
   對外發布前停下來問、log 查不到就老實說。
8. `plugins/starter-kit/skills/web-design/SKILL.md` 存在且 frontmatter 有 `name` 與 `description`，
   且 description 涵蓋「做網頁／HTML 時使用」（可自動觸發、非 install 加購專屬）。
9. deck.html 含「首次裝什麼（本機四樣）」與「之後加什麼（三加購）」兩區塊，且每項標注回扣的概念。
10. opt-in 部署資產仍在（Django `template/`、`zeabur.yaml`、`backup-repo/`），且其既有測試
    （`test_prod_settings`、`test_template_project`、`test_backup`、`test_ci_superset`、
    `test_report_glossary`）全綠。

## 驗證方式

- **自動**：`pytest tests/ -q` 全綠——涵蓋條件 2、3、6、10，以及新增測試（本機骨架綠、
  install-wizard frontmatter 有 disable-model-invocation、web-design 存在且被引用、pillars 含關鍵條目、
  student prompt 純本機）。
- **半自動腳本檢查**：條件 1、4、5、7、8、9 用一次性檢查腳本或 grep 斷言（frontmatter 欄位、prompt
  文字、pillars 關鍵字、deck 區塊）。
- **手動**：在暫存資料夾實跑本機起點六步，確認條件 1–3 的實際行為。
- **Cowork 實測（唯一能消除的不確定）**：在 Windows Cowork 貼 `kickoff-prompt-local.md` 的 prompt，
  驗證它**能不能把 install-wizard 叫起來**（`disable-model-invocation` + Cowork 是否吃自然語言觸發，
  官方無文件，只能實測）。這是上線前的 go/no-go 檢查點。

## ADR（本次決策，inline，沿用本 repo 慣例）

沿用本 repo「ADR inline 寫在 spec」的慣例（無 `docs/adr/` 目錄）。本節四則決策相關，合併記錄，內部
編號。**本 spec supersede `2026-08-14-sunday-101-training-readiness-design.md` 中「本機＝例外檔位」
的框架與 ADR-F**（ADR-F 原本只在 local mode 移除 `deploy-safety`；現在本機是預設且不預裝部署，
`deploy-safety` 只在加購 web/deploy 路徑的 template CI 裡出現，語意隨之變更）。

**ADR-1：本機優先為預設，Django/GitHub/Zeabur 轉 opt-in**
- Drivers：多數學員初期只需本機動手＋能測能回；預裝部署堆疊＝用不到又看不懂的負擔；縮小表面積利於
  週日前上線的穩定性。
- Decision：預設只設本機四樣；部署三樣改成有需求才推薦，資產保留成 opt-in。
- Rejected：維持部署為預設（負擔、違反本機優先）；連部署資產一起刪（斷未來路、多做多錯）。
- Revisit：若之後 kit 的主要客群變成「一開始就要上線的人」，重看預設。

**ADR-2：kit 只編碼「模型預設不會做的」，刪除程序型 skill**
- Drivers：模型本來就會部署／健檢，重複編碼＝維護負擔；價值在互動方式、品味、安全硬停這些模型不會
  自動做的東西，且應常駐 session start。
- Decision：刪除 `deploy` skill、`health-check` skill 與整個 `checks/` 引擎；把非顯而易見的互動與
  安全 wording 抽進 `pillars.md`。
- Rejected：保留 skill（違反最小化）；健檢改成 mode-aware（仍留一大塊部署健檢 code）。
- **Trade-off（明記）**：失去健檢的顯式驗證報告，非技術學員無法自我確認環境有沒有暗坑，改靠模型的
  判斷＋安全繩 hook 兜底。這是接受的代價。
- Revisit：若實務上發現學員頻繁在「環境其實沒設好但被告知裝好了」踩坑，重評是否要一個極簡本機自檢。

**ADR-3：install-wizard 用 skill + `disable-model-invocation`，不改成 command**
- Drivers：Cowork 只確定支援 skill；plugin command 是否被 Cowork 支援無官方文件；
  `disable-model-invocation` 同樣達到「不自動觸發」，又保留目錄 bundling 與 Cowork 確定支援的介面。
- Decision：install-wizard 維持 skill，設 `disable-model-invocation: true`；kickoff prompt 明確叫它。
- Rejected：改成 command（Cowork 支援未知＋失去 bundling＋檔案佈局要重整）；維持可自動觸發
  （會在返場使用者說類似話時亂觸發）。
- Revisit：若 Windows Cowork 實測證實 command 可用且自然語言可觸發，重評。

**ADR-4：完成信號用口頭「裝好了」，不做健檢報告**
- Drivers：使用者選擇輕體驗（ADR-2 已刪健檢引擎，本條是其在 UX 層的延續）。
- Decision：Claude 檢查關鍵幾項後口頭說「裝好了」；成功條件錨在可觀察事實（git/測試/hook），不依賴
  一份給學員看的報告。
- Rejected：用「第一次自動存檔 commit」當親眼憑證（多一個示範步驟，使用者未採）。
- Revisit：同 ADR-2 的 Revisit。
