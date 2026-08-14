# 週日 101 訓練備妥包 — Spec

2026-08-14

## 這份 spec 在定義什麼

一份**訓練備妥包**,讓主講者(你)在週日對 1-3 位非技術新手(101),辦一場半天的
「安心用 AI 開發」訓練。所謂「備妥」= 三塊交付物在週日前各自備妥且驗過一次:

1. **Demo run-of-show** —— 你在 Claude Code CLI 上,一條排練過、確定能跑的完整開發 loop(含 dev→staging→prod),外加一支成功錄影當 fallback。
2. **學員本機路徑** —— 學員在自己的 Cowork 上,現場貼一段 prompt 自助安裝,走到「改→測→綠→commit→push→看 CI 綠」,全程不碰部署。
3. **概念材料** —— 三個核心概念的 101 版講法,每個都釘到 demo 裡的一個時刻。

交付物是「訓練站得住」,**不是**任何一個正式對外服務,也**不是** kit 的架構改造。

## 不做(本 spec 範圍外)

- **Cloudflare 遷移** —— 另開一份獨立 spec,不綁週日。本 spec 完全建立在現有的
  Zeabur kit 之上。
- **學員部署** —— 學員只做本機 + GitHub,不上 Zeabur。
- **學員路徑碰 Zeabur / Google** —— 對「本機 loop」無教學價值,只增加現場易卡的步驟。
- **改動 kit 現有的 Zeabur 部署設計**。
- 排班系統或任何具體應用程式(那是 kit 的 v2)。

## 對象與前提

**主講者**:你。技術背景足夠,在 CLI 上操作。

**學員**:1-3 位非技術新手。半天(3 小時+)的場次,人少 → 現場安裝卡住可一對一救,
這是「GitHub 進現場安裝」風險可接受的前提。

### 學員 pre-work 硬前提(報名時就確認,不能現場補)

| 前提 | 為什麼不能現場補 |
|---|---|
| Claude Pro + Cowork 可用 | Cowork 需付費方案;沒有的人當天到場也裝不了 |
| 已開好一個 GitHub 帳號 | 開帳號是最慢、且主講者不能代做的一步;現場只留「授權」那一下 |

**Windows 學員另需**(已確認有 Windows 學員,所以這是必備項):`.msix` 安裝、系統
管理員權限、Virtual Machine Platform;工作資料夾必須在 `C:\Users\<使用者>\` 底下。
這些是 kit 既有的 Cowork 安裝陷阱,對 101 會靜默失敗,必須進 pre-work 檢查,並在
週日前逐台確認過。

## 訓練形式與表面

**形式:混合。** 你 demo 完整 loop;學員在自己機器上做簡化版(改→測→綠→commit
→push→CI),不部署。

**表面錯位(已接受的約束):**

| | 表面 | 理由 |
|---|---|---|
| 主講 demo | **Claude Code CLI** | 你的慣用表面,不改 |
| 學員動手 | **Cowork** | 跨 OS(Mac/Windows 都有);kit 本來就為它設計(見 ADR-1) |

**後果:你的螢幕 ≠ 學員螢幕。** 因此 demo 只用來教「概念」;學員動手的每一步指示
必須是 Cowork 版、能獨立照做,**不得依賴「照台上畫面做」**。這是缺口 4 的繞法,
寫成成功條件 8。

## 交付物一:Demo run-of-show(P0,最大風險)

**這是本 spec 唯一與人數無關的單點失敗。**

你在 CLI 上,用 kit 既有的 install-wizard 13 步流程,把一個 app 從零建到 Zeabur
staging + prod。好消息:ADR-4 那套「Zeabur 三路徑地獄」是 **Cowork 的 egress 限制**;
你在 CLI 是 per-domain approval,`zeabur` CLI 大概直通,不受那套白名單管轄。

**demo app**:直接用 kit 的 Django template(最小、自帶一個通過測試)。demo 時改動的
是**首頁上一個可見字串**,好讓 staging/prod 的差異在瀏覽器裡直接看得見。排班系統只作為
概念 4「行為層」的訪談範例出現 —— Claude 訪談你的排班需求、翻成業務問題,**不建置、
不部署**,以免部署那條 loop 變複雜。

**排練腳本(固定不變)**:
```
改首頁一個字串 → pytest 綠 → commit → push develop → staging 出現該字串
→(停,問「上正式版嗎」)→ merge main → prod 出現該字串
```
在這條腳本裡順手示範「新 session 失憶又讀檔接上」的記憶時刻(見交付物三)。

**硬要求:跑通後立刻錄一次成功的完整 run 當 fallback。** 現場垮了就放錄影。這跟 kit
自己「每個 commit 都綠 = 永遠有個能回的版本」是同一個精神 —— demo 也要有綠色回退點。

## 交付物二:學員本機路徑(P0)

**install-wizard 的「本機檔位」** —— 擴充既有 skill,不新建。這個檔位只走既有 13 步
裡的:

- 1 機器 readiness check
- 2 確認本機模式
- 3 工作資料夾(Windows 的 `C:\Users\` 限制)
- 4 GitHub:註冊/授權 + 建**一個公開的 code repo**(拿無限 CI)。**本機檔位不建私有備份 repo。**
- 6 複製 template 到工作資料夾
- 7 裝相依套件(`pip install -r requirements.lock.txt`)
- push 到 GitHub → template 自帶的 `tests.yml` 自動觸發 → 學員看到 CI 綠

**跳過**:第 5(Zeabur 租主機/ZeaburOS)、8-12(密鑰、接部署、抄 ID、備份)、
以及 Google connector。

**必須處理的 CI 陷阱**:template 的 `.github/workflows/tests.yml` 有兩個 job ——
`test`(不需 secret,會綠)和 `deploy-safety`(沒設 `DJANGO_SECRET_KEY` /
`DJANGO_ALLOWED_HOSTS` 就 `exit 1` 紅燈)。本機檔位不設部署 secret,學員一 push 就會
看到一個**紅 X**,直接打破成功條件 4,也把「everything 都是綠的、安心」的情緒賣點
反轉。**本機檔位複製 template 後必須拿掉 `deploy-safety` job**(讓學員公開 repo 的 CI
只剩 `test`,直接綠)。完整/demo 路徑不動,保留 kit 作者刻意的「未設定就紅、提醒
部署者補 secret」行為(見 ADR-F)。

**學員 kickoff prompt**:既有 `kickoff-prompt.md` 的變體,指向同一個 marketplace
(`WeihaoLiTW/ai-project-starter`),但請 Claude 走「本機檔位」而非完整安裝。這是**一段
自助跑完的長 prompt** —— 學員貼進自己的 Cowork,它邊跑邊帶學員設定好所需帳號(GitHub)
與環境(工作資料夾、git、Django 骨架、套件),**跑完那個 folder 就 dev-ready、可直接
開始開發**。不含 Zeabur、不含 Google。

**微練習(≤10 分鐘)**:改一個指定字串 → 跑測試 → 綠 → commit。讓學員親手感受
「改一點、測一下、綠了才存」的節奏。

> **硬 deadline 依賴(待確認)**:學員是從 `WeihaoLiTW/ai-project-starter` 這個公開
> marketplace 裝 plugin 的。所以「本機檔位」的改動**必須在週日前 merge/push 到那個
> repo**,否則學員裝到的是舊版、走不了本機檔位。需確認:(a) 那個 repo 是公開且可裝;
> (b) 你有權 push;(c) 本機檔位趕得上週日前 merge。

## 交付物三:概念材料(P1)

五個概念的 101 版講法(不看 code 就懂),每個釘到 demo 的一個時刻:

| 概念 | 101 講法 | demo 時刻 |
|---|---|---|
| **git = 隨時能倒帶** | 每存一次都是一個存檔點,而且每個存檔點都是「測試綠、確定能跑」的。壞了就回到上一個好的存檔點,不會回到半殘狀態。 | commit 那一步;`git log` 看到一串綠存檔點 |
| **model 每次都是重新開始** | 每次對話 AI 都從一張白紙開始 —— 它**不會**自動記得你之前講過、做過的事。學員最容易誤會的就是「Claude 會記住之前所有東西」,這一點要當場戳破。它有時看起來像記得,是因為你**刻意設計了東西讓它每次重讀**:資料夾規則(CLAUDE.md)、技能(skill)、以及 Claude 自帶的 memory 功能。其中最可靠、你看得到也改得到的是 repo 裡的檔案(CLAUDE.md / CONTEXT.md);自帶 memory 是黑盒子(看不到、不能編輯),別依賴它。 | 開一個新 session,它「忘記」→ 讀 CLAUDE.md / CONTEXT.md 才接上 |
| **dev→staging→prod** | 先在自己電腦試(dev),對了推到一個給自己看的網站(staging),再對了才上真正給人用的(prod)。每一關都能先看再決定。 | demo 腳本裡 staging 先看 → 才 promote prod |
| **AI 不會問你答不出來的技術問題** | 好的 AI 助手不會問你「要用哪個資料庫、哪個框架」—— 你答不出來,答了也是猜。它會把技術決策翻成你答得出來的**業務問題**(例如「最多幾人同時用?會給公司外的人用嗎?」),技術的部分它自己扛。 | 你丟一句模糊的「我想做個排班系統」,Claude 不問技術、改問業務規則(think-first skill) |
| **跑一個真服務至少要有哪些東西** | 一個能給別人用的服務,至少要有:一台一直開著的機器(運算)、一個網址(網域)、一個資料留得住的地方(不會一關機就消失)。平台(Zeabur)的作用就是把這些一次幫你備好。只用自己的電腦(本機)可以開發,但**別人連不到、電腦一關就沒了** —— 這就是為什麼要「上線」。 | demo 部署時指著 Zeabur:這台是租的機器、`xxx.zeabur.app` 是網域、volume 是資料留得住的地方 |

**載體**:做成清楚、視覺化、好懂的形式 —— slides,或互動式「teach-me」帶著走,**不要一大堆文字**。可用 `slides` skill 產出。

每個技術名詞第一次出現都要有一句白話解釋(成功條件 7)。

## 成功定義(成品層級)

### Demo

1. 你 CLI 上的 app,staging 與 prod 兩個網址 HTTP 狀態碼皆為 **200**。
2. 完整 demo loop 實際跑通至少一次:改首頁字串 → `pytest` 綠 → commit → push develop → staging → merge main → prod,且 **prod 網址內容包含該次改動的字串**。
3. 存在一支錄影,錄下第 2 條的一次成功完整 run。

### 學員路徑

4. 一個符合 pre-work 前提(Cowork + GitHub 帳號)的**乾淨帳號**,只照學員 prompt 與指示走,達成全部:Django 骨架在、`pytest` 綠、本機至少一個 commit、GitHub 上該 repo 有對應 push、Actions 至少成功執行過一次(結論 success —— 該 repo 的 CI 已由本機檔位移除 `deploy-safety` job,只跑 `test`)。且**過程中 Claude 提出、落在禁問清單(`plugins/starter-kit/behavior/forbidden-questions.md`)的問題數 = 0**。
5. 微練習可在 **≤10 分鐘**內完成(改指定字串 → 跑測試 → 綠 → commit)。
6. 學員 prompt 與所有學員指示中,**不含任何 Zeabur 或 Google 的註冊/授權步驟**(可檢查:文字中不出現 Zeabur、Google connector 的安裝動作)。

### 概念材料

7. 概念材料對列出的每個概念(目前五個)各有:一個「不看 code 就懂」的講法 + 一個對應的 demo 時刻;且材料中出現的每個技術名詞,**第一次出現都有一句白話解釋**(可檢查:名詞清單 vs 解釋覆蓋率 = 100%)。

### 表面錯位繞法

8. 學員動手的每一步指示都是 Cowork 版、能獨立照做,**不含「照台上/我的畫面做」這類對 demo 螢幕的依賴**(可檢查:學員指示中不引用 demo 畫面)。

## 驗證方式(高層次)

- **第 1-3 條**:在你的 CLI 機器上實際建置 + 跑一次完整 loop + 錄影;三者存在即為驗證。第 1 條以 `curl -I` 讀兩個網址狀態碼;第 2 條以 prod 頁面內容包含改動字串為準。
- **第 4-6 條**:用一個乾淨的 Claude(Cowork)+ GitHub 帳號,照學員 prompt 排練走一次(dry-run),記錄是否全達成、是否有 Claude 提出禁問清單問題、是否動用 prompt 外知識。
- **第 7-8 條**:對概念材料與學員指示做靜態檢查(名詞覆蓋、概念↔demo 對應、無畫面依賴)。

全部條件週日前可完成,不需等待真實時間流逝。

## 待確認項(請在 review 頁框選留言)

1. **學員裝 plugin 的來源 repo(唯一未決前提)**:學員靠貼一段 prompt,去「一個網路上的公開清單」把 starter-kit 裝到自己的 Cowork。那個清單就是 GitHub 上的 `WeihaoLiTW/ai-project-starter` 這個 repo。**已查證(2026-08-14):此 repo 目前是 PRIVATE(私有),你是 ADMIN(有 push 權)。** 私有代表**學員的 Cowork 抓不到、裝不了**。因此週日前必須:(a) 把這個 repo 改成 **public(公開)**,或改用別的散布方式;(b) 把「本機檔位」的改動推上去。改 public 會讓 repo 全部內容對外公開 —— 動作前先確認裡面沒有不能公開的東西(帳密、內部資訊)。push 權已確認、非阻塞;卡點是 (a) 公開 與 (b) 本機檔位趕不趕得及。

## 決策紀錄(供 plan 階段歸檔 ADR)

### ADR-A: This spec targets Sunday training readiness on the existing Zeabur kit; Cloudflare is deferred

**Decision:** Scope this spec to making the Sunday 101 training stand up on the current
Zeabur-based kit, plus a gap analysis. The Cloudflare migration gets its own separate
spec, not tied to Sunday.

**Drivers:** Sunday is two days out. A platform migration to Cloudflare touches ~25
files (deploy skill, health-check, install-wizard, template `prod.py`, backup, probes,
tests) and collides with a load-bearing architectural assumption — Django + SQLite +
persistent volume + long-running container does not map onto Cloudflare Workers'
serverless, no-persistent-filesystem model without Cloudflare Containers or a rewrite.
Cloudflare was never in the original infra research, so it also carries un-evaluated
risk. Landing that safely for a live 101 demo in two days is not realistic.

**Rejected:** Cloudflare-first (migrate now, demo the new architecture Sunday) — too
much surface, un-evaluated platform, architectural mismatch, two-day deadline.

### ADR-B: Demo on Claude Code CLI, students on Cowork; the screen mismatch is accepted

**Decision:** The presenter demos on Claude Code CLI (unchanged). Students use Cowork.
The resulting screen mismatch is accepted, and student hands-on instructions must stand
alone rather than mirror the demo screen.

**Drivers:** The presenter will not switch surfaces. Cowork is the students' surface
because it exists on both macOS and Windows and the kit was built for it (ADR-1). A
bonus: the Zeabur egress pain (ADR-4) is a Cowork constraint; on the CLI, per-domain
approval likely makes the `zeabur` CLI work directly, which lowers demo-build risk.

**Consequence:** the demo teaches concepts only; every student hands-on step must be a
self-contained Cowork instruction, never "copy what I did on screen."

**Rejected:** unifying both sides on one surface. Forcing the presenter onto Cowork was
declined by the presenter; forcing students onto CLI reintroduces ADR-1's Windows
sandbox hazard (the sandbox falls back to unsandboxed execution for a user who approves
everything).

### ADR-C: Student path includes GitHub push + CI, but excludes Zeabur and Google

**Decision:** The student local path runs to local commit **plus** GitHub push and a
green CI run. It does not touch Zeabur or Google.

**Drivers:** With 1-3 students over a half day, one-on-one rescue makes the live GitHub
authorize step acceptable, and push + CI completes the "everything is recorded" story
(off-machine backup, tests re-run in the cloud). Zeabur and Google add fragile,
time-eating steps with no teaching payoff for a local development loop.

**Rejected:** local-commit-only (robuster install with zero external accounts, but the
student never personally experiences the cloud record); students-also-deploy-to-Zeabur
(the fragile, high-value-only-for-the-demo part).

**Accepted cost:** the student live install now depends on a GitHub authorize step, and
students must arrive with a GitHub account already created.

### ADR-D: The from-scratch demo deploy must ship a recorded successful run as fallback

**Decision:** Build the Zeabur staging+prod demo app from scratch on the CLI, and
require a recording of one successful end-to-end run as a fallback.

**Drivers:** The presenter has no existing deployment, so this is built from zero in two
days by a first-time Zeabur user, against a platform with notoriously poor error
messages (kit known-limitation #11: creating a project before ZeaburOS is installed
returns only "An error occurred, please try again later") and 48-hour log retention.
It is the single largest, audience-independent point of failure.

**Consequence:** the recording is the demo's "green rewind point" — the same ethos as
the kit's test-before-commit safety net. If the live run fails, play the recording.

### ADR-E: Student pre-work prerequisites are confirmed at signup, not fixed live

**Decision:** Two hard prerequisites — Claude Pro + Cowork, and an already-created
GitHub account — are confirmed when students sign up, not resolved during the session.

**Drivers:** Cowork needs a paid plan (cannot be granted live); GitHub account creation
is the slowest step and cannot be done by the presenter on the student's behalf.
Discovering either gap on Sunday means that student cannot participate.

### ADR-F: The local-only path drops the deploy-safety CI job instead of relaxing it

**Decision:** The install-wizard local-only mode removes the `deploy-safety` job from
the copied template's `tests.yml`, leaving a tests-only CI. The full/demo path keeps
the job unchanged.

**Drivers:** The template's `deploy-safety` job is deliberately red-until-configured —
its own name reads "紅燈常見原因:secrets 還沒設定", a to-do reminder aimed at whoever
is deploying. A local-only student never sets those secrets, so that job would show a
permanent red X, which both breaks the "Actions success" success condition and inverts
the training's emotional payoff ("everything is green, you're safe"). Relaxing the job
(making missing-secrets pass) was rejected because it would silently delete a guard the
kit's authors put there on purpose for the deploying audience.

**Rejected:** gating the job on a variable so it self-skips (still mutates shared
behavior for the full path); leaving it red and redefining success as "the `test` job
is green" (a 101 seeing any red X asks why, undercutting the message).

**Consequence:** the local-only mode is the one place that diverges the template's CI,
and that divergence is confined to a single job removal at copy time.

## 引用來源

- 現有 kit 設計 spec:`docs/superpowers/specs/2026-08-08-starter-kit-design.md`
- 禁問清單:`plugins/starter-kit/behavior/forbidden-questions.md`
- 安裝嚮導:`plugins/starter-kit/skills/install-wizard/SKILL.md`
- 開場白:`docs/onboarding/kickoff-prompt.md`
- marketplace:`.claude-plugin/marketplace.json`
