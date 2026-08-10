# 走查文件：從零到九項全綠

## 這份文件是什麼

從「什麼都還沒裝」走到「環境健檢九項全綠」的每一步。每一步都寫「你會看到什麼」
跟「沒看到怎麼辦」，照著做就好，不需要先懂任何技術名詞。

**這份文件本身也是一個測試對象。** 如果你是被找來驗這份文件的人，規則是：**只照
文件做，每一次發現自己動用了文件外的知識（猜一個畫面上沒寫的按鈕位置、用你自己
知道但文件沒教的指令），就記一筆缺陷，不要當場修，繼續走完**。走完之後把記下來
的缺陷全部修掉，再重跑一次，直到一筆缺陷都記不到為止。

## 開始前要準備的東西

- 一台電腦（Windows 或 Mac）。
- 一個 email 地址（GitHub、Zeabur 註冊要用）。
- 一張信用卡，或支付寶餘額（Zeabur 儲值要用其中一種；Zeabur 是幫你把程式碼變成
  一個大家連得到的網站的服務，後面第 3.5 步會細講）。
- 一個 Claude 帳號，方案是 Pro 或以上（Cowork 需要付費方案才有；Cowork 是 Claude
  的其中一種模式，能直接讀寫你電腦裡的檔案、跑程式，不只是聊天，這整套環境包
  就是靠它做事）。
- Windows 使用者要有這台電腦的系統管理員權限，沒有的話先找有權限的人幫你裝。

沒有實測過完整流程一次要花多少時間，抓半天比較保守 —— 中間有幾處是等 Zeabur
主機開好、部署跑完這種零碎等待，不是你一直在動手。

## 第 0 步：裝對版本的 Claude Desktop

**這一步在 plugin 裝好之前，Claude 還沒辦法帶你走，你要自己做完。**

1. 先跑官方的 readiness check —— 一個不用安裝、不用登入的小程式，跑一次就直接
   告訴你「這台機器能不能跑 Cowork」，不用自己猜方案或系統版本夠不夠。
   從 https://claude.com/download 這個頁面找下載連結；如果找不到，到 Anthropic
   官方的「Get started with Claude Cowork」support 文章（
   https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork ）
   裡面會有連結。**Windows 分 x64 與 ARM64 兩個版本，依你電腦的處理器選對的那一個。**
   - 這個下載位置是查 Anthropic 現行官方文件與說明頁確認的，不是這份文件所在
     的專案自己實測過的步驟。畫面用詞可能隨版本更新變動；如果連結失效，用
     「Claude Cowork readiness check」去官方網站搜尋，通常還是能找到。
   - 看到什麼算過：畫面顯示這台機器可以跑 Cowork。
   - 沒過怎麼辦：畫面會講原因（例如虛擬化功能沒開）。先處理那個原因，不要跳過
     這一步硬裝。

2. 到 https://claude.com/download 下載 Claude Desktop 安裝檔。

   **Windows 使用者，這裡有兩個看起來裝成功、但其實沒有 Cowork 的陷阱**，而且兩個
   都不會跳出任何錯誤訊息告訴你哪裡不對：

   | 陷阱 | 會發生什麼 | 怎麼避開 |
   |---|---|---|
   | 用 `.exe` 安裝檔裝 | Claude Desktop 裝得起來、看起來正常，但完全沒有 Cowork | **一定要用 `.msix` 安裝檔**，不是 `.exe`。`claude.com/download` 頁面上的按鈕不分格式，直接用下面這兩個連結下載（依你電腦的處理器選一個）：[Windows x64 (.msix)](https://claude.ai/api/desktop/win32/x64/msix/latest/redirect)、[Windows ARM64 (.msix)](https://claude.ai/api/desktop/win32/arm64/msix/latest/redirect) |
   | 沒有系統管理員權限 | 一樣裝得起來、看起來正常，但沒有 Cowork | 用系統管理員權限重新安裝，或請有權限的人幫你裝——沒有管理員權限，這台機器就是裝不出有 Cowork 的版本，這不是你哪裡做錯，是這台機器目前的限制，找有管理員權限的人（例如公司的 IT）幫你裝 |

   還需要 Virtual Machine Platform 這個 Windows 功能（家用版也內建，不用額外買
   專業版）。

   Mac 使用者沒有上述兩個陷阱，macOS 11 以上都可以直接裝。

3. 裝好之後打開 Claude Desktop，確認畫面上（通常是輸入框旁邊）看得到 Chat／Cowork
   的模式切換。看不到就代表這台帳號或這個版本還沒有 Cowork——回頭確認方案是不是
   Pro 以上、安裝檔是不是 `.msix`（Windows）。

   有個已知但不常見的狀況：部分 Windows 11 家用版會被 readiness check 誤判成
   「可以」。如果裝完發現 Cowork 選項真的沒出現，用 Windows 內建的 PowerShell
   開一個視窗，輸入 `Get-Service vmms`——如果系統回報找不到這個服務，代表這台
   機器目前裝不了 Cowork，需要換一台或升級 Windows 版本。這一步不是每個人都要做，
   只有「裝完卻沒看到 Cowork」時才需要排查。

## 第 1 步：切到 Cowork，確認是本機模式

1. 在輸入框旁邊的模式切換，選 **Cowork**（不是 Chat，不是 Code）。
2. 找 Cowork 的設定，把「Run new tasks in the cloud」這個開關**關掉**。
   - 為什麼：雲端模式有個已知問題——一個檔案被改過之後再讀一次，可能讀到改之前
     的舊內容，但畫面上顯示的檔案時間卻是新的。這會讓「測試綠了才存檔」這道安全
     機制驗到錯的東西，等於白做。本機模式沒有這個問題。
   - 看到什麼算過：開關顯示關閉／灰色。
3. 看不到 Cowork 或這個開關：可能是你的組織把 Cowork 或它的網路存取整個關掉了。
   確認方案是 Pro 以上；如果是公司帳號，找 IT 或帳號管理員確認 Cowork 有沒有被
   組織政策鎖住。

## 第 2 步：貼開場白、裝 plugin

1. 開一個新的 Cowork 對話。
2. 打開同一個資料夾底下的
   `docs/onboarding/kickoff-prompt.md` ，把裡面「貼這一段」底下的整段文字複製，
   貼進對話框，送出。
3. Claude 會照著那段話的指示，帶你去：**側邊欄 → Customize → Plugins →
   Personal plugins → 按「+」→ Add marketplace**，要你輸入
   `WeihaoLiTW/ai-project-starter`，然後裝 `starter-kit`。
   - 看到什麼算過：Personal plugins 清單裡出現 `starter-kit`。
   - 沒看到 Add marketplace 這個選項：確認你在 Customize → Plugins → Personal
     plugins 這個路徑下，不是別的分頁。
4. 建議另外裝 **Claude in Chrome** 這個瀏覽器擴充功能，並在 Cowork 裡開啟它。
   它不是必需品，但後面第 3.5 步碰 Zeabur 網頁時，如果其他方式都連不上，它是
   唯一保證能用的備援路徑。
5. plugin 裝好之後，Claude 會自己接著問要不要開始跑安裝嚮導。跟著做，就是下面
   第 3 步的內容。

## 第 3 步：安裝嚮導

這一段 Claude 會帶你走，**你不需要自己記順序**，但知道「為什麼是這個順序」能讓
你看懂中途發生的事。順序對應 plugin 裡 `install-wizard` 這個 skill（plugin 裡的
一個功能模組，你可以把它想成一套寫好的操作流程）定死的 13 個步驟，中間插了一個
「找兩個環境的網址」——這是這份走查文件另外補的，給健檢用，install-wizard 本身
沒有把它列成單獨一步。

### 3.1 機器行不行

跟第 0 步的 readiness check 是同一件事，Claude 會再跟你確認一次結果。

### 3.2 確認本機模式

跟第 1 步的「Run new tasks in the cloud」是同一件事，Claude 會再跟你確認一次。

### 3.3 工作資料夾

Claude 會告訴你它打算把專案放在哪個資料夾。

- **Windows 使用者：這個資料夾必須在 `C:\Users\你的帳號名稱\` 底下。**
  不能是網路磁碟、不能是被搬過位置的「文件」資料夾（有些公司會把「文件」重新
  導向到雲端硬碟，那樣會出問題）。
- 看到什麼算過：Claude 講的路徑開頭確實是 `C:\Users\你的帳號名稱\`。

### 3.4 GitHub

GitHub（一個存放程式碼的網站，順便幫你自動跑測試、自動部署）是這整套環境包的
地基，Zeabur 部署跟每天的自動備份都靠它。

1. 到 https://github.com 註冊一個帳號（如果還沒有）。
2. 讓 Claude 幫你建立兩個 repo（repository，你可以把它想成「一個放程式碼的雲端
   資料夾，且改動都有記錄」）：一個**公開**的放程式碼，一個**私有**的放備份。
   - 為什麼要分兩個、為什麼一個公開一個私有：公開的 repo 換來 GitHub Actions
     （GitHub 附的自動化功能，會自動幫你跑測試、跑部署）無限的執行分鐘數，不
     公開的話每個月有額度上限；備份 repo 裡面會存到帳號、密碼相關的東西，不能
     公開讓所有人看到，所以要私有。
3. 連上 GitHub 的方式是 connector（Claude 官方用來連外部服務、取得授權的功能，
   在 Cowork 的設定裡）——這一步需要你自己在設定裡連一次，跳出來的登入畫面是
   GitHub 官方的頁面，不是這個 plugin 的，正常授權就好。

### 3.5 Zeabur（陷阱最多的一步，仔細看）

1. 到 https://zeabur.com 註冊帳號。
2. **儲值**——需要付款方式才能租主機。如果畫面只看到「綁信用卡」的選項，找一下
   「儲值 / Recharge」，通常在同一個設定頁，支付寶也能用。只看綁卡那半、以為
   自己沒有信用卡就做不下去，是常見的卡關點。
3. **Zeabur 原本免費的共享叢集已經停用**，現在一定要自己租一台主機，沒有免費
   繞過的方式。
4. **租主機時，規格不要選最小那一檔**（通常會標示接近 2GB 記憶體）。
   至少選 **2 vCPU / 4GB** 這一檔（在 Tencent Cloud Tokyo 這個地區，價格大約是
   每月 4 美元）。
   - 為什麼：下一步要裝的 ZeaburOS，加上它需要的 K3s（Zeabur 用來管理容器的
     底層系統），再加上這個 kit 本身要跑的兩個環境（staging、prod），光開機
     就會吃掉大約 1.5GB 記憶體。2GB 的機器會在後面某一步悄悄卡死，而且畫面上
     不會告訴你是記憶體不夠，只會覺得「怎麼卡住了」。
5. **主機租好之後，先裝 ZeaburOS，裝完才能建立專案，順序不能顛倒。**
   ZeaburOS 是 Zeabur 官方用來初始化主機的系統，安裝過程會把整台主機清空重灌，
   所以只能在還沒放任何東西上去之前做。
   - **如果順序顛倒**（沒裝 ZeaburOS 就先建立專案），你會看到一個完全沒解釋的
     錯誤訊息：`An error occurred, please try again later`。畫面上不會告訴你
     原因，也不會告訴你下一步該做什麼。**看到這句話，代表順序錯了**——回去把
     ZeaburOS 裝好再建立專案。

**Zeabur 怎麼操作這件事，Claude 會自己探測用哪一條路（指令列、程式接口、或
瀏覽器），不用你決定。** 你只要知道：如果 Claude 說某個 Zeabur 操作卡住或連不上，
不代表整個 Zeabur 帳號壞了，可能只是那一條路暫時走不通，換一條就好，這是設計上
本來就會發生的事，不是故障。

### 3.6 建立專案

Claude 會直接用工具把這個 plugin 附帶的專案樣板複製到你第 3.3 步選好的工作
資料夾。**這一步是 Claude 做的，你不用自己手動複製檔案**（樣板裡有幾個檔名開頭
是點的檔案，用滑鼠手動複製很容易漏掉，所以交給 Claude 做）。

### 3.7 裝相依套件

樣板需要的程式庫（Django 等）這台機器上還沒裝，Claude 會跑一行指令把它們裝好。
沒裝這一步的話，之後每一輪對話結束測試都會失敗——但那是「套件沒裝」，不是程式碼
真的壞了，看起來卻一樣是紅燈，很容易誤以為剛剛的改動出了問題。

### 3.8 產生密鑰

Claude 會跑一行指令產生一組給 Django（後端框架）用的密鑰，直接設進 Zeabur 的
環境變數，**不會出現在任何檔案裡**，你不需要自己抄或記這串東西。

### 3.9 接上部署

`develop` 這個分支的程式碼會自動部署到測試環境（staging），`main` 這個分支會
自動部署到正式環境（prod）。這一步 Claude 會直接設定好，你不需要動手。

### 3.10 抄下服務 ID 與環境 ID

這一步**不能跳過、也不能用猜的**——目前沒有任何指令列得出環境 ID，只能自己去
網頁上抄。

1. 到 Zeabur 主控台，打開**正式環境（prod）**那個服務的頁面。
2. 看網址列，會長得像：

   ```
   https://zeabur.com/projects/<一串專案ID>/services/<一串服務ID>?envID=<一串環境ID>
   ```

   - `projects/` 後面那一段是**專案 ID**（這一步不需要）。
   - `services/` 後面那一段是**服務 ID**。
   - 網址最後 `?envID=` 等號後面那一段是**環境 ID**。
3. 把服務 ID 和環境 ID 抄下來，交給 Claude（下一步會用到）。

- 這個網址結構是查 Zeabur 官方文件（
  https://zeabur.com/docs/en-US/developer/public-api ）與官方論壇上 Zeabur
  員工的回覆確認的，不是這份文件所在的專案自己在真實主控台上操作過一次拍下來
  的畫面。如果你看到的網址跟這裡描述的不完全一樣，找 `projects`、`services`、
  `envID` 這三個關鍵字出現的位置，原理不會變。

### 3.11 找兩個環境的網址（staging 與 prod）

健檢（第 3.14 步）會需要 staging 跟 prod 兩個網址去確認網站真的連得上，接下來
3.12 設定部署安全變數也會用到 prod 的網址。這兩個網址的子網域名稱是你安裝時自己
取的，沒有地方會自動幫你記下來，Claude 也查不到一個能穩定列出它的指令，所以需要
你自己去看一次：

1. 到 Zeabur 主控台，分別點進 staging 跟 prod 兩個服務。
2. 展開該服務頁面裡的 **Domains** 這個分頁，裡面會列出一個免費的
   `xxx.zeabur.app` 網址（`xxx` 是你當初取的名字）。
3. 把兩個網址都交給 Claude。

- 這個位置是查 Zeabur 官方文件（
  https://zeabur.com/docs/en-US/deploy/networking/public-networking ）確認的，
  同樣沒有在這份文件所在的專案裡實際操作拍過畫面，如果分頁名稱跟「Domains」不
  完全一樣，找服務頁面裡列著一個 `.zeabur.app` 網址的那個分頁即可。

### 3.12 設定 code repo 的部署安全變數

code repo 的 GitHub Actions 有一個「deploy-safety」檢查，會確認正式環境的設定
安不安全，需要兩個值才能跑：跟 3.8 步產生的同一組 `DJANGO_SECRET_KEY`，和
3.11 步查到的 prod 網址（`DJANGO_ALLOWED_HOSTS`）。Claude 會用 `gh` 指令把這兩個
值設到 code repo 上，你不需要自己動手；沒設好的話，這個檢查會一直紅燈，錯誤訊息
會講清楚原因，不用緊張。

### 3.13 設定備份

1. 到 Zeabur 主控台，找 **Settings → API Keys**，點「Generate new API key」
   （新增一個 API 金鑰）。金鑰通常只在剛產生的那一刻完整顯示一次，記得先複製
   起來（可以先貼到一個安全的地方，例如密碼管理工具），再交給 Claude 去設定，
   不要事後還需要回頭找。
   - 這個位置是查 Zeabur 官方文件（
     https://zeabur.com/docs/en-US/developer/use-api-key ）確認的，同樣不是
     這份文件所在的專案實測拍下來的畫面，如果選單文字不完全一樣，找「API Keys」
     或「Settings」這類字樣即可。
2. 把這串金鑰交給 Claude。Claude 會把這個 plugin 附帶的備份工作流程檔放進你的
   **私有備份 repo** 的 `.github/workflows/` 資料夾，並且：
   - 設定一個叫 `ZEABUR_API_TOKEN` 的密鑰（secret），內容就是你剛複製的那串金鑰。
   - 設定三個變數：`ZEABUR_SERVICE_ID`、`ZEABUR_ENV_ID`（用第 3.10 步抄下來的
     那兩組 ID），和 `CODE_REPO`（你的程式碼 repo，格式是「帳號/repo 名稱」）。

### 3.14 跑一次環境健檢

Claude 會跑一輪環境健檢，**九項全部變綠才算裝完**。有紅燈的話，照 Claude 給的
說法一項一項處理，不要在還有紅燈的時候就覺得已經裝好了。詳細九項內容見下面
第 4 步。

## 第 4 步：健檢九項，各自看到什麼算過

| 項目 | 綠燈代表什麼 | 紅燈通常是什麼原因 |
|---|---|---|
| 執行環境 | 目前確實是 Cowork 的本機模式 | 雲端模式還開著，回第 1 步關掉 |
| 工具鏈 | Python、SQLite、git 的版本都夠新 | 環境裡裝的版本太舊，通常需要重裝或更新 |
| 測試 | 專案裡的自動測試全部通過，而且跑得夠快 | 有程式碼壞了，或測試還沒建立起來 |
| 三道保命繩 | 三個 hook（開場注入、測試綠才存檔、密鑰擋門）都真的觸發過一次 | plugin 沒裝好，或某個 hook 沒被 Cowork 觸發，需要回報 |
| 歷史版本 | 抽查過去某個版本，程式仍然跑得動 | 曾經有一次「測試綠才存檔」被繞過，留下一個壞掉的版本 |
| GitHub | repo 存在，且 Actions 最近一次成功執行過 | repo 還沒建，或 Actions 最近一次失敗 |
| Zeabur 操作路徑 | 已經確認走哪一條路（指令列／程式接口／瀏覽器），並且實際成功執行過一次操作 | 三條路都連不上，通常是網路政策問題，需要照第 3.5 步的方式排查 |
| 兩個環境 | staging 與 prod 網址都能連上，而且正式環境的安全設定正確（不是預設密鑰、不是開發模式） | 有一個環境還沒部署成功，或忘了改預設密鑰 |
| 資料安全 | 寫進正式環境的一筆測試資料，重新部署之後還在；備份也真的跑過、打得開、含這筆資料 | 忘了掛 volume（一塊固定掛在容器上的儲存空間，重開機、重新部署都不會清空；見下方的坑），或備份流程還沒跑過一次 |

## 常見坑速查表

以下全部是實際撞過的坑，照這裡處理，不用自己猜原因。

| 坑 | 會看到什麼 | 怎麼處理 |
|---|---|---|
| Windows 用 `.exe` 裝 Claude Desktop | 裝起來看起來正常，但沒有 Cowork，沒有任何錯誤訊息 | 一定要用 `.msix`，而且要有系統管理員權限重新安裝 |
| Zeabur 共享叢集已停用 | 找不到免費叢集的選項 | 一定要先租一台主機，沒有免費繞過的方式 |
| ZeaburOS 沒裝就建專案 | `An error occurred, please try again later`，沒有其他說明 | 順序不能換：先裝 ZeaburOS，才建立專案 |
| 主機規格選最小檔（約 2GB） | 裝到某一步悄悄卡住，沒有錯誤訊息 | 租主機時至少選 2 vCPU / 4GB |
| 沒掛 volume 就開始用 | 重新部署之後，之前寫的資料不見了 | volume 要在**第一次啟動前**掛好，事後補掛救不回已經不見的資料 |
| Zeabur 自訂網域不驗證所有權 | 綁了一個打錯字或根本不是自己的網域，當下不會報錯 | 綁完務必自己開瀏覽器連一次確認打得開，不要只看「綁定成功」的訊息 |
| 自訂網域白名單失效 | 把 Zeabur 的網域加進 Cowork 的網路白名單，仍然被擋 | 這是平台本身的問題，不是你設錯；改用三條路徑（指令列／程式接口／瀏覽器）裡連得上的那一條，不要卡在修白名單上 |
| Chat 的記憶不會帶進 Cowork | 之前在 Chat 跟 Claude 講過的事，Cowork 完全不知道 | 重要的事在 Cowork 裡重講一次；不要假設 Claude 記得 |
| Cowork 的記憶看不到也改不掉 | 想確認 Claude 記了什麼、想修正一個錯誤的記憶，但沒有介面能看或改 | 重要結論一律寫進 `CONTEXT.md`、`docs/adr/`、`CLAUDE.md` 這三個檔案，那才是真正能查、能改、進 git 版控的真相來源，不要依賴記憶 |

## 這份文件用到的資料來源

**已經在這份文件所在的專案裡實測過的部分**（
`docs/superpowers/specs/2026-08-08-starter-kit-design.md` 的「實測數據來源」
與「已知限制」章節，含對應的 Anthropic 官方 issue 追蹤編號）：

- Windows `.msix` / `.exe` 差異、系統管理員權限
- Zeabur 共享叢集停用、ZeaburOS 安裝順序、`An error occurred` 錯誤訊息
- 主機規格（2 vCPU / 4GB、$4/月，Tencent Cloud Tokyo）與記憶體占用數字
- volume 必須在第一次啟動前掛好
- 自訂網域不驗證所有權
- 自訂網域白名單失效
- Chat 與 Cowork 記憶互不相通、Cowork 記憶看不到也改不掉

**這次（Task 18）另外查證、但沒有在這份文件所在的專案裡實際操作過一次的部分**
——來源是 Anthropic 與 Zeabur 目前公開的官方文件，不是憑印象或猜測寫的，但也
沒有本機實測畫面能對照，如果畫面用詞跟這裡寫的不完全一樣，以官方文件連結為準：

- readiness check 的下載位置（claude.com/download 與 support.claude.com 的
  Cowork 說明文章）
- Zeabur 主控台網址帶著服務 ID 與環境 ID 的結構（`projects/<id>/services/<id>?envID=<id>`）
- `ZEABUR_API_TOKEN` 的取得位置（Zeabur 主控台 Settings → API Keys）
- staging／prod 網址在 Zeabur 介面的哪裡看（該服務頁面的 Domains 分頁）
- Windows `.msix` 的直接下載連結，以及沒有系統管理員權限會裝出不含 Cowork 版本
  這件事——查 Anthropic 官方的 Windows 部署文章（
  https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows ）
  確認的，該文章原文是：「For individual installations with full feature
  support including Claude Cowork, administrator privileges are required.
  Users without admin access can still install Claude, but Cowork on desktop
  will not be available.」

如果你走查這份文件時，發現上面這五項其中之一跟真實畫面不一樣，那正是這份文件
目前最該補強的地方——記下來，別自己在心裡默默修正過去。
