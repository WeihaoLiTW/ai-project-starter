---
name: install-wizard
description: 首次安裝環境時使用（使用者明確要求安裝、說「幫我裝環境」「從頭開始」時）。預設只裝本機環境，不建外部帳號、不部署。
disable-model-invocation: true
---

# 安裝嚮導

你要帶的人不會寫程式。每一步都先講「這一步在幹嘛」，再講「你要點什麼」。
一次只給一件事做。他做完回報，你才給下一件。

**不要問他任何技術選擇。** 預設只裝本機環境，不碰資料庫、框架這些決定。
他要決定的只有名字、email，以及業務規則。

**貼一段話沒辦法全自動裝好。** 裝 plugin、改設定都是 UI 動作，
Anthropic 刻意鎖在使用者手動同意後面，你按不到那些按鈕。你能做的是一步步帶他點，
以及你自己能用工具做的部分（複製檔案、跑指令）直接幫他做掉。
不要跟他說「我幫你裝好了」——講清楚是「帶你裝」還是「我直接做完了」。

## 主線：六步裝好本機環境

預設只做到「能在自己電腦上改程式、跑測試、存檔」為止。不註冊 GitHub、
不碰 Zeabur，這些都是加購項目，見下面「什麼時候加什麼」。

1. **機器行不行** —— 跑官方 readiness check（一個小程式，不用安裝、不用登入，
   跑一次就會告訴你這台機器能不能跑 Cowork；實際下載位置寫在
   `docs/onboarding/walkthrough.md` 這份文件裡）。
   不通過就停在這裡，把原因講清楚，不要讓他裝到一半才發現。
2. **確認是本機模式** —— 設定裡關掉「Run new tasks in the cloud」。
   雲端模式會讀到舊的檔案內容，而且它回報的時間是對的，所以測試會驗到錯的東西。
3. **工作資料夾** —— Windows 必須在 `C:\Users\<他的名字>\` 底下。
   不能用網路磁碟、不能用被搬過位置的「文件」資料夾。
4. **Git 設定** —— 工作資料夾裡跑：

       git init

   （已經有 `.git` 就跳過這行）。再檢查身份有沒有設定過：

       git config user.name
       git config user.email

   兩個都有值就跳過。缺任何一個，直接用白話問他：「這台電腦要記錄每次存檔是誰、
   什麼時候存的，只有你自己看得到，不會公開——你想留什麼名字？email 呢？」
   拿到答案後跑：

       git config user.name "<他的名字>"
       git config user.email "<他的 email>"

5. **建立專案** —— 把這個 skill 目錄底下 `local-template/` 的東西複製到他的
   工作資料夾（不是 `template/`——那份是網頁樣板，屬於加購項目，見下一段）。
   這一步你直接用工具做，不用叫他手動複製。複製完跑：

       python3 -m pip install -r requirements-local.txt

   （這份清單只鎖了 pytest，裝起來很快。）
6. **裝好了** —— 跑一次 `scripts/run_tests.sh` 確認測試是綠的，確認第 4 步的
   git 身份真的設好了。都沒問題，就用白話跟他說「裝好了」，不用生報告、
   不用跑健檢——本機骨架就這幾件事，綠了就是好了。

## 什麼時候加什麼

本機環境裝好之後，看使用者實際說出來的需求，才加對應的東西——不要不問就
一次通通裝上去。

### 要做網頁 → 複製 Django 樣板

把這個 skill 目錄底下 `template/`（跟主線第 5 步的 `local-template/` 不同份）
複製到工作資料夾，覆蓋掉本機骨架。網頁怎麼設計、怎麼搭版面，交給
web-design skill 自動處理，這裡不用另外決定技術細節。

樣板需要的套件跟本機骨架不同，裝樣板自己鎖定版本的那份清單（跟 CI 用的是
同一份，裝出來的版本才會跟 CI 一致）：

    python3 -m pip install -r requirements.lock.txt

### 要備份 / 分享 / CI → 建 GitHub repo

註冊 GitHub、建立一個**公開**的程式碼 repo、push 上去。公開換來無限的 CI 額度。
GitHub 的 connector 要他自己在設定裡連，授權畫面會跳出來要他登入——那是正常的，
那個畫面是 GitHub 的，不是我們的。

如果之後還要上線（見下一段），另外建一個**私有**的備份 repo——裡面會放帳號和
密碼，不能公開。

### 要上線 → 用 Zeabur 部署

上線前先確認已經做過「要做網頁」（有 Django 樣板可以部署）跟「要備份 / 分享 /
CI」（有 GitHub repo 可以接部署）這兩步，Zeabur 部署的是 Django 樣板，不是
本機骨架。

不要假設任何一條路可用。直接用 `npx zeabur` 或 `curl` 打 Zeabur 的網址，
失敗訊息不會提到網路限制，沒有人查得出原因。

完整步驟，順序不能換——Zeabur 的錯誤訊息說不清楚原因，順序錯了他會卡死在一個
沒有下一步的畫面：

1. 註冊、儲值、租一台主機、裝 ZeaburOS（Zeabur 官方用來初始化主機的系統；
   安裝過程會把整台租來的主機清空重灌，所以一定要在還沒放任何東西上去之前做，
   這是它排在建專案之前、順序不能換的原因）、**然後才**建專案。
   ZeaburOS 沒裝好就建專案，只會得到一個沒有原因的錯誤。
   租主機時規格別選最小的那一檔（約 2GB 記憶體）——光 ZeaburOS 加上它自己需要的
   K3s 加兩個空容器就吃掉 1.5GB 左右，2GB 的機器會在後面步驟悄悄卡死，而且不會
   告訴你是記憶體不夠。至少要選 2 vCPU / 4GB 那一檔（Tencent Cloud Tokyo 上約
   $4/月），這是實測跑得動的規格。
2. **產生密鑰** —— 用 `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
   產一組 `DJANGO_SECRET_KEY`，設進 Zeabur 的環境變數。**不要寫進任何檔案。**
3. **接上部署** —— `develop` 分支接 staging，`main` 分支接 prod。
4. **抄下兩組 ID** —— 開啟正式環境那個服務的頁面，從網址列抄下服務 ID 與
   環境 ID。**CLI 沒有任何指令列得出環境 ID**，只能從網址抓，所以這一步不能跳。
5. **設定 code repo 的部署安全變數** —— code repo 的 GitHub Actions 裡有一個
   「deploy-safety」檢查，會確認正式環境的設定安不安全，需要兩個值才能跑：
   `DJANGO_SECRET_KEY`（跟第 2 步產生的是同一組，設成 secret，任何人都看不到）
   跟 `DJANGO_ALLOWED_HOSTS`（正式環境的網址，設成 variable，可以被看到）。
   網址是安裝時自己取的名字，這個專案沒有地方會記下來，問他自己最快。跑：

       gh secret set DJANGO_SECRET_KEY --repo <帳號>/<code repo> --body "<第 2 步產生的那組>"
       gh variable set DJANGO_ALLOWED_HOSTS --repo <帳號>/<code repo> --body "<正式環境網址>"

   沒設這兩個值，`deploy-safety` 那個檢查會一直紅燈——它的錯誤訊息會講清楚是
   這個原因，不用緊張，但也不要跟他說「裝好了」，先把這兩個值補上。
6. **備份** —— 把這個 skill 目錄底下 `backup-repo/backup.yml` 放進私有 repo 的
   `.github/workflows/`，設定 `ZEABUR_API_TOKEN` 這個 secret，以及
   `ZEABUR_SERVICE_ID`、`ZEABUR_ENV_ID`、`CODE_REPO` 三個變數（用第 4 步抄下來的
   兩組 ID）。`backup-repo/README.md` 也一起放進私有 repo。
