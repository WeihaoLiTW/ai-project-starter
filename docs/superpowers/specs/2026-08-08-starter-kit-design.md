# 非技術新手 Claude 環境包 — Spec

2026-08-08

## 這份 spec 在定義什麼

一包給非技術者的 Claude 環境設定，讓他把一段話貼進自己的 Claude 之後，得到一個
**行為對、環境備妥、能開始做真服務**的工作環境。

v1 的交付物是「環境備妥 + 行為對」，不是任何一個具體的應用程式。排班系統之類的
實際服務屬於後續版本。

## 對象與前提

**對象**：朋友自己的公司／小團隊的非技術同事。沒有現成的 git 基礎設施，初期每人
自己一個帳號。

**前提條件**（不滿足就不該往下裝）：

| 項目 | 要求 |
|---|---|
| Claude 方案 | Pro 以上（Cowork 需要付費方案） |
| 介面 | **Cowork**，不是 Chat 也不是 Code |
| Windows 安裝 | 必須用 `.msix` 安裝檔、需要系統管理員權限、需要 Virtual Machine Platform（家用版也有） |
| 網路 | 程式碼執行環境至少要開「套件管理器 + `github.com`」 |
| 組織政策 | Cowork 與其網路存取都可能被組織關閉 |

**安裝的第一步是跑官方 readiness check** —— 一個不用安裝、不用登入的小程式，
直接告訴這台機器能不能跑 Cowork。它把「家用版還是專業版」這類猜測完全繞開。

## 架構

| 元件 | 負責 | 成本 |
|---|---|---|
| GitHub | 程式碼、Actions（測試／備份） | $0（公開 repo，Actions 分鐘數無上限） |
| Zeabur Free 方案 | 部署控制台 | $0 |
| Tencent Cloud Tokyo 主機 | 跑容器（staging + prod 兩個環境） | **$4/月** |
| Django + SQLite | 後端、admin 後台、使用者系統 | $0 |
| Google | Sheets 讀取 | $0 |
| **合計** | | **$4/月** |

三個環境跑同一份程式碼：local 是 Cowork 執行環境裡的 Python，staging 和 prod 是
Zeabur 上同一個 image 的兩個環境，各自獨立的 SQLite 檔案。

### 為什麼是 Django 而不是更輕的選項

判準是**輕量、Claude 熟悉度、安全**三項。Django 在後兩項明顯勝出，第一項可接受
（150–250 MB，對 4 GB 的機器無關痛癢）。

決定性的是安全：Django 的防護是預設開啟、要主動關掉才會出事（ORM 防 SQL
injection、模板自動跳脫、內建 CSRF、PBKDF2 密碼雜湊），而且有專職 security team、
公開的漏洞揭露流程、三年支援的 LTS。

對照 FastAPI：使用者系統、admin 後台、ORM、CSRF、session、密碼雜湊全部要自己接，
**任何一塊漏掉就是洞**，而且不會報錯、不會當機，網站看起來完全正常。在「Claude
代寫、使用者無法審查」的情境下這個差異被放大。

Django 的 admin 後台另有一個不可取代的價值：**它是非技術者唯一能自己點開看見資料
的窗口**，而且有完整繁體中文。

## Kit 組成

| 類型 | 名稱 | 做什麼 |
|---|---|---|
| — | **開場白** | 要傳給對方的那段話。自帶最小行為指示，因為貼進去的當下 plugin 還沒裝 |
| hook | 開場注入 | 每次對話開始載入行為層三支柱 |
| hook | 自動 commit | 每輪對話結束前跑測試，綠了才 commit |
| hook | 密鑰擋門 | 阻止 `.env` 之類被 commit |
| skill | 安裝嚮導 | 帶對方走完 readiness check、三家註冊授權、環境建立 |
| skill | 環境健檢 | 跑一輪檢查吐綠燈報告 |
| skill | **想清楚再做** | grill-with-docs 改造版，維護 `CONTEXT.md` 與 ADR |
| skill | 部署 | 從改 code 到上線，含 staging 先看再上 prod |
| 樣板 | Django 專案骨架 | settings 分 dev/prod、Dockerfile、測試骨架、CI workflow、備份 workflow |
| connector | GitHub、Google | 遠端 MCP |

Excel 報表 skill 移至 v1.1 —— 它是能力展示，不是「環境備妥」的一部分。

## 行為層

**核心原則：不要問使用者他答不出來的問題。**

### 三支柱

**一、怎麼講話** —— 繁中、白話、術語第一次出現時用括號補一句人話。

**二、怎麼動手** —— 放手模式。讀取、產生新檔、跑分析直接做；只有刪除和對外發布
才停下來問。

**三、怎麼決定** —— 見下。

### 決策規則（三段）

1. **技術決策底下有業務取捨 → 翻譯成業務問題來問。** 不是「不能問」，是「不能用
   技術的樣子問」。
2. **底下沒有業務取捨 → Claude 直接決定，寫 ADR。** 密碼雜湊演算法、檔案命名、
   要不要加索引。
3. **業務答案之間的交互後果 → Claude 自己推導並處理，不再回頭問。**

**檢查點**：如果一個技術決策翻譯不出業務問題，那是信號 —— 代表還沒想清楚這個決策
會影響什麼，該回頭再想，而不是當作「沒有業務取捨」跳過。

**翻譯是有損的**：翻譯完要自問「使用者的答案是否足以支撐這個技術決策」，不夠要
補問。

### 翻譯的實例（已驗證有效）

| 問使用者的樣子 | 底下的技術決策 | 實測答案 |
|---|---|---|
| 員工離職後，他填過的班表要保留還是消失？ | soft delete vs hard delete | 全部保留 → soft delete |
| 最多多少人同時用？會開放給外部嗎？ | SQLite vs Postgres | 幾十人、只有內部 → SQLite 夠 |
| 除了員工和主管，還有第三種人嗎？ | 要不要做權限系統 | 就兩種 → Django 內建 `is_staff` 就夠 |
| 排好的班被改了，需要知道是誰改的嗎？ | 要不要做 audit log | 需要且要能查 → 要做 |

**這組實測證明了規則的必要性**：三題往簡單走，一題往複雜走，而那個往複雜走的
（audit log）**正是 Claude 自己絕對會決定省掉的** —— 「內部小工具、幾十人、不對
外」，任何合理的技術判斷都會說不用做稽核。但使用者說要，因為他知道排班會有爭議。
那是業務知識，不是技術判斷。

**交互後果的實例**：要能查「誰改的」+ 離職帳號保留 = audit log 會指向已離職的人，
所以那些使用者記錄真的不能刪。這是從兩個業務答案推出的技術後果，Claude 要自己
接住。

### 決定了要說，但不要求確認

> 資料我存在一個叫 SQLite 的檔案裡 —— 就是一個檔案，簡單、備份容易，你們這個規模
> 夠用。哪天人多到跑不動，我會告訴你要換。

使用者有知情權，但不用承擔他判斷不了的決策責任。

### 網路操作一律走 MCP，不走 shell

程式碼執行環境的網路受組織設定管控，而**MCP 不受 egress 限制**。在本機模式下
plugin 的 MCP server 是在使用者電腦上原生執行、不在 VM 裡，用的是主機網路。

| 操作 | 走法 |
|---|---|
| GitHub | 官方遠端 MCP |
| Zeabur | 官方本機 MCP |
| Google Sheets | 官方 connector |
| 查文件 | web fetch／search（不受 egress 限制） |

這條要寫進行為層，否則 Claude 會很自然地用 `git push`，然後在網路關閉的環境下失敗。

### 寫死的預設（使用者不需要知道，但錯了會出事）

- 技術棧：Django + SQLite + Zeabur + GitHub
- `DEBUG` 一律從環境變數讀，prod 絕不為 true
- `SECRET_KEY` 從環境變數讀，不進 git
- **volume 必須在第一次啟動前掛好**
- 備份必須用 SQLite 的一致性快照（`VACUUM INTO`），**不能直接複製檔案**
- PocketBase／第三方元件一律鎖版本，不用 `latest`

## 三道保命繩

```
Claude 改了程式碼
  → 每輪對話結束前自動跑測試
  → 綠了才 commit
  → 紅了不 commit，直接修到綠
```

結果是 **git 歷史上每一個 commit 都是測試綠的狀態**。回溯到任何一點，拿到的都是
能跑的版本。這讓「放手模式」真正安全 —— 不是「反正壞了可以回」，是「隨時可以回到
一個確定能跑的版本」。

**這三道全部不需要網路** —— git 的本機操作（commit、log、diff、checkout）不連外。
最關鍵的安全機制不受組織網路政策影響。

**起點問題**：樣板專案自帶一個最小的通過測試，所以從第一天就有綠的基準，不會出現
「還沒有測試所以無法判斷」的空窗。

### 測試設計

**測行為，不測實作。** 測「員工填了時段之後，主管在後台看得到」，不是
`save_shift()` 回傳 True —— 後者在重構時會壞掉，然後非技術者面對一個他看不懂的
紅字。

**測試報告是中文 HTML**，列出系統保證會做的每件事。對非技術者，這張表同時是三件
事：系統沒壞的證據、系統會做什麼的清單、跟同事解釋這東西能幹嘛的文件。

**CI 跑的測試必須是 local 測試的超集**，多出來的部分只能是「非得真實部署才驗得
了」的東西。破了這條就會出現「我這邊都綠的，為什麼 CI 紅了」，而非技術者無法在本地
重現問題。

## 想清楚再做

基於 [mattpocock/skills](https://github.com/mattpocock/skills) 的 `grill-with-docs`
（MIT）。它比純 `grill-me` 多做兩件事：訪談中即時維護 `CONTEXT.md` 詞彙表，並在
遇到難以回頭的決策時寫 ADR。

**為什麼對非技術者比想像中重要**：他的問題不只是想太淺，是**講的話沒有固定意義**。
今天說「員工」、明天說「同事」、後天說「人員」，Claude 每次照字面理解，系統裡就
同時出現三張表 —— 而他永遠不會發現，因為他看不懂程式碼。

`CONTEXT.md` 是**他唯一看得懂、也唯一有資格審查的技術產物**。

### 四項改造（原版是寫給工程師的）

1. **技術問題翻譯成業務問題再問**，不直接 grill 技術決策
2. `CONTEXT.md` 用繁中寫
3. ADR 的「為什麼」用白話 —— 不是「to avoid N+1 queries」，是「這樣資料多的時候
   不會變慢」
4. 語氣改掉 —— 原版的 relentless 對工程師是優點，對非技術者是壓迫感

### 詞彙一致性貫穿全鏈

```
使用者講的話 → CONTEXT.md 詞彙表 → 程式碼裡的名字 → 測試報告上的中文
```

四個地方同一套詞。而且這是**可驗證的** —— 檢查測試報告上出現的名詞是否都在
`CONTEXT.md` 有定義。

## 記憶

**不需要另做知識庫，repo 就是記憶。** `CONTEXT.md`、`docs/adr/`、folder
instructions 都是檔案、都進 git，有版本、能回溯、跟程式碼綁在一起不會漂移。

**但 Cowork 的內建記憶是黑盒子**（看不到、不能編輯、沒有版本），所以：

1. **重要結論不能只留在記憶裡，必須寫進 repo 的檔案。** 記憶是加速器，不是真相
   來源。
2. **folder instructions 進 git。** 它可以被 Claude 自己更新 —— 好用，但也代表
   Claude 可能悄悄改掉規則。進 git 之後自動 commit hook 會記下來。

另外要告知使用者：**Chat 的記憶不會帶進 Cowork**，兩邊是分開的。

## 部署與備份

**環境切分**：staging 和 prod 是同一個 Zeabur 專案的兩個環境（不是兩個專案），
變數與資源各自隔離，跑在同一台主機上。

**觸發**：push 到 `develop` → staging；merge 到 `main` → prod。

**上 prod 要問**：非技術者不會用 PR，所以 Claude 代為 merge，但「上正式版」屬於
對外發布 → 停下來問。流程是 Claude 說「staging 看起來對嗎？要上正式版嗎」→ 同意
才動。

**migration 在容器啟動時執行**（entrypoint 裡跑 `manage.py migrate`），不走 GitHub
Actions —— Actions 連不到容器裡的 SQLite。

**網址**用預設 `xxx.zeabur.app`，子網域名稱自訂，自動 HTTPS。v1 不碰自訂網域：
DNS 設定要在網域商後台做，A 記錄／CNAME／TTL 對非技術者是純黑話，而且這不是取捨、
是操作步驟，「翻譯成業務問題」幫不上忙。

**備份**：GitHub Actions 排程 → 用 `VACUUM INTO` 產一致性快照 → 抓下來 → 推到
**私有 repo 的 Release**，保留 **3 個月**。

選 Release 而不是 commit 進 git，是因為 SQLite 是二進位檔，git 無法差異壓縮，每天
一份就是每天多存一整份。選私有 repo 而不是 Actions artifact，是因為**公開 repo 的
artifact 任何人都能下載**，而裡面有使用者帳號與密碼雜湊。

## 成功定義（成品層級）

### 環境備妥

1. 環境健檢報告 8 項全綠。
2. 工作資料夾裡有 Django 專案，`pytest` 全綠且**執行時間 < 30 秒**。
3. GitHub 上有對應 repo，Actions 至少成功執行過一次（結論為 success）。
4. Zeabur 上 staging 與 prod 各有一個網址，**兩者 HTTP 狀態碼皆為 200**。
5. 在 prod 寫入一筆測試資料 → 觸發重新部署 → **該筆資料仍存在**。
6. prod 的 `DEBUG` 為 `False`、`SECRET_KEY` 不等於樣板預設值、`ALLOWED_HOSTS`
   不含 `*`。
7. 備份 workflow 成功執行過一次，私有 repo 的 Release 中存在一個 SQLite 檔，**該檔
   可被 `sqlite3` 開啟，且包含第 5 條寫入的那筆測試資料**。
8. git 歷史上**任意**一個 commit checkout 出來，`pytest` 皆為綠。

### 行為層

9. 對「我想做個排班系統」這類模糊需求，Claude **提出的問題中落在禁問清單上的數量
   = 0**，且**提出的業務規則問題數量 ≥ 1**。（禁問清單於 plan 階段定義為具體項目，
   至少涵蓋：資料庫選型、框架選型、部署平台、檔案結構、演算法選擇。）
10. 測試報告 HTML 中出現的領域名詞，**能在 `CONTEXT.md` 找到定義的比例 = 100%**。
11. 清空 Cowork 的 project memory 後開啟全新 session，Claude 讀 repo 即可接續工作，
    **重新詢問已記錄於 `CONTEXT.md` 或 `docs/adr/` 之決策的次數 = 0**。

### 走得通

12. 在乾淨機器與乾淨帳號上依文件從零走完安裝流程，**走查記錄中「動用文件外知識」
    的次數 = 0**。

## 驗證方式

第 1–8 條由**環境健檢 skill 本身執行** —— 它跑完吐一張綠燈報告，報告即為驗證結果。
第 5 與第 7 條需要實際觸發一次重新部署與一次備份 workflow。

第 9 條以預先寫好的數組模糊需求作為輸入，比對 Claude 提出的問題與禁問清單。

第 10 條以腳本比對測試報告 HTML 中的名詞與 `CONTEXT.md` 的詞條。

第 11 條清空 project memory 後開新 session，觀察 Claude 是否重問已記錄的決策。

第 12 條為人工走查，規則是：**只照文件做；每一次發現自己動用文件外的知識，就記下
一筆缺陷，不當場修，繼續走完**。每一步計時。走完後修掉全部缺陷，重跑，直到記錄
為零。這條把「走查者知道太多」從缺點轉為偵測器 —— 每動用一次文件外知識，就精準
定位到一個文件缺口。

全部條件可在單一 session 內完成，無需等待真實時間流逝。

Code-level tests are authored in the plan phase (codex as QA), not in this spec.

## 範圍邊界（v1 不做）

- Excel 報表 skill（移至 v1.1）
- 自訂網域綁定
- 排班系統或任何具體應用程式（v2）
- 行銷／業務／營運情境 skills（v3）
- Google Sheets 逐格編輯（官方 connector 做不到）
- 多人集中管理（Zeabur Team 方案 $79/月起，初期每人自己一個帳號）

## 已知限制

1. **貼一段 prompt 無法全自動安裝。** 裝 plugin、裝 connector、改設定都是 UI 動作，
   Anthropic 刻意鎖在使用者手動同意後面。能做的是 Claude 一步步帶他點完。
2. **Cowork 執行環境沒有 docker。** 已實測確認。架構因此不依賴它。
3. **程式碼執行環境的網路預設可能全封。** 需要至少開「套件管理器 + `github.com`」。
   若組織政策不允許，這套做不了 —— 應在安裝前誠實告知，而非讓對方裝到一半才發現。
4. **Windows 有兩個靜默失敗的陷阱**：沒有管理員權限、或用 `.exe` 而非 `.msix`
   安裝，都會得到一個看起來正常但沒有 Cowork 的 Claude Desktop，且沒有任何訊息說明
   原因。
5. **Zeabur log 只留 48 小時**（Dev $5 方案可延至 7 天）。若使用者週五出問題、週一
   才回報，log 已消失。這是明擺著的取捨，未替使用者決定。
6. **SQLite 不能水平擴展，並發寫入有限。** 內部工具綽綽有餘，但這是有天花板的選擇。
7. **沒掛 volume 之前寫入的資料活不過下一次部署。** 已實測確認，且原因不是「掛載
   會清空目錄」——對照組根本沒有掛載動作，資料就已經消失。
8. **Zeabur 的錯誤訊息品質差。** 實測撞到三個都是非技術者會卡死的類型，最嚴重的是
   ZeaburOS 未安裝時建專案只回 `An error occurred, please try again later`，既沒說
   原因也沒說下一步。安裝嚮導必須把順序寫死，而非等使用者撞到錯誤。
9. **Zeabur 自訂網域不驗證所有權。** 打錯字不會當場報錯，要等發現網址連不上才知道。
10. **Cowork connector 是否自動觸發 OAuth 未經實測。** 安裝嚮導照「不能自動」撰寫，
    若實際可自動，多餘步驟為無害空轉。
11. **公開 repo 換來無限 CI，代價是任何密鑰外洩即為公開。** hook 擋 `.env` 是防呆
    不是保險。

## 決策紀錄（供 plan 階段歸檔 ADR）

### ADR-1: Cowork over Claude Code

**Decision:** Target Claude Cowork, not the Code surface.

**Drivers:** The audience includes Windows users. Claude Code's Bash sandbox has no
native Windows support; when the sandbox cannot start, Claude Code falls back to
running commands unsandboxed, which is worse than no sandbox for a user who approves
everything without reading it. Restoring the sandbox requires WSL2, which contains
three steps Claude cannot perform (elevating PowerShell, rebooting, setting a Linux
password) plus a permanent usability defect: the project must live inside WSL's
filesystem for acceptable performance, where the user cannot find it in Explorer.

**Rejected:** Claude Code. It has the better network model — per-domain approval on
first use, requiring no admin rights — against Cowork's org-level all-or-nothing
setting. Reconsider if the audience ever becomes Mac-only.

### ADR-2: SQLite over a managed database

**Decision:** SQLite as the datastore for v1.

**Drivers:** Collapses an entire layer out of the architecture. Backup becomes file
copy, which a free scheduled GitHub Action can perform, removing the need for the
paid backup feature. Tests run against in-memory SQLite with zero external
dependencies, so the suite completes in seconds and works fully offline — which in
turn makes the whole test-before-commit safety net independent of network policy.

**Rejected:** Supabase (unnecessary once SQLite was chosen; free tier also caps at
2 projects across all orgs, pauses after 7 days of inactivity, and its own docs warn
against pointing its MCP at production data). Neon (wins decisively on multi-environment
cost — free branching, 100 projects, no pausing — but requires hand-building an admin
page to view user data, which this audience cannot do).

**Accepted ceiling:** no horizontal scaling, limited concurrent writes.

### ADR-3: Django over FastAPI, PocketBase, and Rails

**Decision:** Django with server-rendered templates. No API layer in v1.

**Drivers:** Security defaults are on unless deliberately disabled, and the project
has a dedicated security team, a public disclosure process, and three-year LTS
releases. The admin console is the only surface through which a non-technical owner
can inspect their own data, and it ships with complete Traditional Chinese
translations. Claude's familiarity with Django is high enough that fabricated
configuration is unlikely — which matters because the user cannot detect it.

**Rejected:** FastAPI — auth, admin, ORM, CSRF, sessions and password hashing all
become the author's responsibility, and any omission is a silent hole rather than a
crash. PocketBase — lightest option and bundles SQLite, auth and an admin UI in one
binary, but is pre-1.0 with no backward-compatibility guarantee, primarily
single-maintainer, has no dedicated security team, and its admin UI is English-only.
Rails 8 — heaviest of the three and its admin console requires a third-party gem.

**Deferred:** Django Ninja. Not needed while pages are server-rendered; adding it
later costs one dependency and a few files, and breaks nothing existing.

### ADR-4: Route network operations through MCP rather than the shell

**Decision:** Every network-dependent operation goes through an MCP server. The shell
is used only for local work.

**Drivers:** Code execution egress is governed by an org-level setting that a
corporate user may have no permission to change; the measured default on an
Enterprise account blocked every outbound request including google.com. MCP is
explicitly exempt from egress rules, and in local mode plugin MCP servers execute
natively on the device rather than inside the VM, so they use the host's network.
The design therefore survives a fully locked-down environment.

**Residual gap:** `pip install` cannot be routed through MCP, since MCP is a tool
protocol rather than a package manager. This sets the hard minimum: package-manager
egress must be enabled or the kit cannot function. `github.com` is also requested, to
avoid the alternative of writing files through the GitHub API, which would produce a
second commit history diverging from the local one.

### ADR-5: Backups to a private repo's Releases, not Actions artifacts

**Decision:** Scheduled Action takes a `VACUUM INTO` snapshot and uploads it to a
private repository's Releases, retained 3 months.

**Drivers:** Artifacts inherit repository visibility, and the code repo is public to
obtain unlimited Actions minutes — so artifacts would expose user accounts and
password hashes to anyone. Releases avoid inflating git history, which a daily binary
blob would otherwise do since git cannot delta-compress it.

**Critical detail:** a plain file copy of a live SQLite database can capture an
inconsistent snapshot, producing a backup that appears valid and is not. This is
worse than no backup, because the failure is only discovered during a restore.
`VACUUM INTO` must be used.

### ADR-6: Translate technical decisions into business questions rather than hiding them

**Decision:** A technical decision that conceals a business trade-off is surfaced as
a business question. One with no business trade-off is decided unilaterally and
recorded as an ADR. Consequences arising from the interaction of several business
answers are derived by Claude without returning to the user.

**Drivers:** Validated empirically. Of four translated questions, three led to
simpler implementations and one — audit logging — led to a more complex one. That
fourth is precisely the decision an unaided technical judgement would have skipped:
an internal tool for a few dozen users has no obvious need for an audit trail. The
user asked for it because scheduling produces disputes and disputes need evidence.
That is domain knowledge, not a technical judgement.

**Rejected:** the earlier formulation "never ask the user technical questions", which
would have caused exactly that omission.

**Detection rule:** if a technical decision cannot be translated into a business
question, that indicates the decision's consequences are not yet understood — not
that no trade-off exists.

## 實測數據來源

本 spec 引用的所有數值均來自 2026-08-04 至 2026-08-05 的實機驗證，完整過程記錄於
`docs/research/2026-08-03-starter-kit-infra-selection.html`，探針程式與模板位於
`probes/volume-check/`。

| 數值 | 來源 |
|---|---|
| 主機 2 vCPU / 3659 MB / 60 GB，$4/月 | `zeabur server get --id <server-id> --json` 於 Tencent Tokyo `bundle_starter_nmc_lin_med4_01` |
| ZeaburOS + K3s + 2 容器佔用 1503 MB | `zeabur server exec -- free -m` |
| volume 對照實驗（無 volume 資料消失／有 volume 資料留存） | `probes/volume-check/zeabur-no-volume.yaml` 與 `zeabur-with-volume.yaml`，以 `zeabur service exec` 寫入 marker 後 `service restart` 再讀取 |
| 自訂網域可在 Free 方案綁定、HTTP 200、ZeroSSL 憑證 | `zeabur domain create --domain <name>` 後 `curl -I` 與 `openssl s_client` |
| Cowork 本機 VM：Ubuntu 22.04 aarch64、4 核 / 3904 MB、無 docker、對外全部 000 | 於 Cowork 本機模式執行 shell 診斷腳本 |

### 官方文件依據

- [Get started with Claude Cowork](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork)
- [Claude Cowork architecture overview](https://support.claude.com/en/articles/14479288-claude-cowork-architecture-overview)
- [Use Claude Cowork safely](https://support.claude.com/en/articles/13364135-use-claude-cowork-safely)
- [Deploy Claude Desktop for Windows](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows)
- [Install plugins (Cowork)](https://claude.com/docs/cowork/guide/plugins)
- [Use Google Workspace connectors](https://support.claude.com/en/articles/10166901-use-google-workspace-connectors)
- [Configure the sandboxed Bash tool (Claude Code)](https://code.claude.com/docs/en/sandboxing)
- [Zeabur Pricing](https://zeabur.com/pricing)
- [Zeabur Volumes](https://zeabur.com/docs/en-US/data-management/volumes)
- [Zeabur Template Format](https://zeabur.com/docs/en-US/template/template-format)
- [GitHub Actions billing](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions)
- [mattpocock/skills](https://github.com/mattpocock/skills)
