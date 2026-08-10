---
name: install-wizard
description: 帶使用者從零裝好整套環境 —— 檢查機器、註冊三個服務、建立專案、部署兩個環境。使用者第一次開始、或說「幫我設定環境」「從頭開始」時使用。
---

# 安裝嚮導

你要帶的人不會寫程式。每一步都先講「這一步在幹嘛」，再講「你要點什麼」。
一次只給一件事做。他做完回報，你才給下一件。

**不要問他任何技術選擇。** 技術棧已經定了：Django、SQLite、GitHub、Zeabur。
他要決定的只有名字、帳號、以及業務規則。

**貼一段話沒辦法全自動裝好。** 裝 plugin、裝 connector、改設定都是 UI 動作，
Anthropic 刻意鎖在使用者手動同意後面，你按不到那些按鈕。你能做的是一步步帶他點，
以及你自己能用工具做的部分（複製檔案、跑指令、產密鑰）直接幫他做掉。
不要跟他說「我幫你裝好了」——講清楚是「帶你裝」還是「我直接做完了」。

## 順序不能換

Zeabur 的錯誤訊息說不清楚原因，所以順序錯了他會卡死在一個沒有下一步的畫面。

1. **機器行不行** —— 跑官方 readiness check（一個小程式，不用安裝、不用登入，
   跑一次就會告訴你這台機器能不能跑 Cowork；實際下載位置寫在
   `docs/onboarding/walkthrough.md` 這份文件裡）。
   不通過就停在這裡，把原因講清楚，不要讓他裝到一半才發現。
2. **確認是本機模式** —— 設定裡關掉「Run new tasks in the cloud」。
   雲端模式會讀到舊的檔案內容，而且它回報的時間是對的，所以測試會驗到錯的東西。
3. **工作資料夾** —— Windows 必須在 `C:\Users\<他的名字>\` 底下。
   不能用網路磁碟、不能用被搬過位置的「文件」資料夾。
4. **GitHub** —— 註冊、建立一個**公開**的程式碼 repo、再建一個**私有**的備份 repo。
   公開換來無限的 CI 額度；備份放私有的，因為裡面有帳號和密碼。
5. **Zeabur** —— 註冊、儲值、租一台主機、裝 ZeaburOS（Zeabur 官方用來初始化
   主機的系統；安裝過程會把整台租來的主機清空重灌，所以一定要在還沒放任何東西
   上去之前做，這是它排在建專案之前、順序不能換的原因）、**然後才**建專案。
   ZeaburOS 沒裝好就建專案，只會得到一個沒有原因的錯誤。
   租主機時規格別選最小的那一檔（約 2GB 記憶體）—— 光 ZeaburOS 加上它自己需要的
   K3s 加兩個空容器就吃掉 1.5GB 左右，2GB 的機器會在後面步驟悄悄卡死，而且不會
   告訴你是記憶體不夠。至少要選 2 vCPU / 4GB 那一檔（Tencent Cloud Tokyo 上約
   $4/月），這是實測跑得動的規格。
6. **建立專案** —— 把這個 skill 目錄底下 `template/` 的東西複製到他的工作資料夾。
   這一步你直接用工具做，不用叫他手動複製。
7. **裝相依套件** —— 樣板需要的程式庫（Django 等）還沒裝，這台機器上不會自動裝好。
   沒裝這一步，之後每一輪對話結束測試都會失敗——但失敗原因是「套件沒裝」，不是
   程式碼真的壞了，看起來卻一樣是紅燈，會讓人誤以為剛剛的改動出了問題。在專案
   資料夾裡跑 `python3 -m pip install -r requirements.lock.txt`（鎖定版本的那份
   清單，跟 CI 用的是同一份，裝出來的版本才會跟 CI 一致）。
8. **產生密鑰** —— 用 `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
   產一組 `DJANGO_SECRET_KEY`，設進 Zeabur 的環境變數。**不要寫進任何檔案。**
9. **接上部署** —— `develop` 分支接 staging，`main` 分支接 prod。
10. **抄下兩組 ID** —— 開啟正式環境那個服務的頁面，從網址列抄下服務 ID 與
    環境 ID。**CLI 沒有任何指令列得出環境 ID**，只能從網址抓，所以這一步不能跳。
11. **設定 code repo 的部署安全變數** —— code repo 的 GitHub Actions 裡有一個
    「deploy-safety」檢查，會確認正式環境的設定安不安全，需要兩個值才能跑：
    `DJANGO_SECRET_KEY`（跟第 8 步產生的是同一組，設成 secret，任何人都看不到）
    跟 `DJANGO_ALLOWED_HOSTS`（正式環境的網址，設成 variable，可以被看到）。
    網址是安裝時自己取的名字，這個專案沒有地方會記下來，問他自己最快。跑：

        gh secret set DJANGO_SECRET_KEY --repo <帳號>/<code repo> --body "<第 8 步產生的那組>"
        gh variable set DJANGO_ALLOWED_HOSTS --repo <帳號>/<code repo> --body "<正式環境網址>"

    沒設這兩個值，`deploy-safety` 那個檢查會一直紅燈——它的錯誤訊息會講清楚是
    這個原因，不用緊張，但也不要跟他說「裝好了」，先把這兩個值補上。
12. **備份** —— 把這個 skill 目錄底下 `backup-repo/backup.yml` 放進私有 repo 的
    `.github/workflows/`，設定 `ZEABUR_API_TOKEN` 這個 secret，以及
    `ZEABUR_SERVICE_ID`、`ZEABUR_ENV_ID`、`CODE_REPO` 三個變數（用第 10 步抄下來的
    兩組 ID）。`backup-repo/README.md` 也一起放進私有 repo。
13. **跑一次環境健檢** —— 用 health-check skill，九項全綠才算裝完。
    沒綠的項目照它給的說法處理，不要在還有紅燈的時候就跟他說裝好了。

## Zeabur 怎麼操作

不要假設任何一條路可用。先讓 health-check skill 探測，它會告訴你走 CLI、
MCP 還是瀏覽器。**直接用 `npx zeabur` 或 `curl` 打 Zeabur 的網址，失敗訊息
不會提到網路限制，沒有人查得出原因。**

## connector

GitHub 與 Google 的 connector 要他自己在設定裡連。授權畫面會跳出來要他登入 ——
那是正常的，那個畫面是 GitHub 或 Google 的，不是我們的。
