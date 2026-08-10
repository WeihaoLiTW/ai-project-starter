---
name: health-check
description: 跑一輪環境健檢，吐一張九項綠燈報告。使用者說「檢查環境」「看看有沒有問題」「裝好了嗎」，或安裝流程走到最後時使用。
---

# 環境健檢

九項檢查。**每一項都獨立**，一項紅了其他項照常給結果 —— 一份產不出來的報告
等於什麼都沒檢查。

## 你要先探測的事

shell 看不到這些，所以你要自己探完，寫進 facts 檔。有幾項是操作，不是讀一個
現成的值——表格裡會直接寫「這是操作」，跟下面 `proven` 那一列是同一種意思。

| 要探的 | 怎麼探 |
|---|---|
| 現在是不是本機模式 | 看設定，或問使用者確認「Run new tasks in the cloud」是關的 |
| 三個 hook 有沒有真的跑過 | 寫一個檔案、結束一輪，看 `facts["hooks_fired"]` 裡有沒有出現這三個字串（`safety_net` 探針就是照這三個字比對，缺一個就紅）：`SessionStart`、`PreToolUse`、`Stop` |
| GitHub 上有沒有這個 repo | 在工作資料夾跑 `git ls-remote origin`——repo 是公開的，不用認證，GitHub 本身也不在網路白名單限制內，這條最省事。把查到的 `帳號/repo 名稱` 寫進 `facts["github"]["repo"]` |
| GitHub Actions 最近一次結果 | 用 GitHub connector 讀這個 repo 最新一次 workflow run，或者（repo 是公開的）直接 `curl` GitHub 的公開 API `https://api.github.com/repos/<帳號>/<repo>/actions/runs?branch=main&per_page=1`，取回應裡第一個 run 的 `conclusion` 欄位。寫進 `facts["github"]["last_conclusion"]` |
| Zeabur 三條路 | CLI：跑一次 `zeabur project list`。MCP：呼叫一次它的唯讀工具。瀏覽器：確認 Chrome 擴充功能能開 Zeabur 的畫面 |
| Zeabur 那條路實際跑成功過沒有 | 用選中的那條跑一次唯讀操作，成功才把 `proven` 設成 true |
| staging／prod 網址回不回 200 | 這兩個網址（`*.zeabur.app` 的子網域）是安裝時自己取的名字，這個專案目前沒有任何地方會記下來，我也找不到能穩定列出它的 CLI 指令——先試著用已驗證的 Zeabur 路徑打開服務頁面找網域，找不到就直接問使用者這兩個網址，他自己天天在用，問他最快。查到後對每個網址各跑一次 `curl -s -o /dev/null -w '%{http_code}' <網址>`，把回傳碼寫進 `facts["endpoints"]["staging"]` / `["prod"]` |
| prod 的三個安全設定 | 用已驗證的 Zeabur 路徑對 prod 服務跑一次唯讀操作讀環境變數。CLI 是 `zeabur service exec --service-id <prod 服務 ID> --env-id <prod 環境 ID> -- env`——這個指令這個專案自己的備份 workflow（`backup-repo/backup.yml`）就在用，已經證實連得上。從輸出裡挑出 `DJANGO_DEBUG`、`DJANGO_SECRET_KEY`、`DJANGO_ALLOWED_HOSTS` 三行，寫進 `facts["prod_env"]` |
| 資料撐不撐得過重新部署 | **這是操作**：用 Zeabur 路徑對 prod 寫一筆帶得出識別文字的測試資料，把這段文字記下來寫進 `facts["backup"]["marker"]`；接著推一個空 commit 到 `main`（這個專案本身的部署就是這樣觸發的）讓它重新部署；部署完再用同一條路徑讀一次那筆資料還在不在，寫進 `facts["backup"]["survived_redeploy"]` |
| 備份真的跑過、打得開、含剛才那筆資料 | **這也是操作**，而且要排在上一項寫完 marker 之後，不然這次備份根本不會含那筆資料。對私有備份 repo 觸發一次 `backup-repo/backup.yml`（它開了 `workflow_dispatch`，`gh workflow run backup.yml --repo <帳號>/<備份 repo>` 就能手動跑，不用等每天的排程）。跑完用 `gh release list --repo <帳號>/<備份 repo> --limit 1 --json tagName` 拿最新的 tag 寫進 `facts["backup"]["release_tag"]`；`gh release download <tag> --repo <帳號>/<備份 repo>` 下載那個 release 的 `.sqlite3` 檔，用這個專案已經有的 `python3 scripts/backup_snapshot.py verify <檔案>` 確認打得開，結果寫進 `snapshot_opens`；打得開的話用內建的 `sqlite3` 開檔讀出資料列，把讀到的內容寫進 `snapshot_rows`，交給探針去比對 marker 有沒有在裡面 |

**這些是你要做的，不是探針要做的。** 探針只讀 facts 檔裡的值下判斷，
它們不會自己連網路、不會自己開瀏覽器。`zeabur` 探針尤其如此：它只看
`facts["zeabur"]` 裡的 `cli`、`mcp`、`browser`、`proven` 四個值。探得到一條路
只代表「connectivity 在」，不代表「這條路真的能用」——**只有實際跑成功一次
唯讀操作（例如列出專案），才可以把 `proven` 寫成 `true`**。連得上但沒跑過、
跑過但失敗、或忘了寫這個欄位，都要當作沒證明過，不要因為看起來可以連就先
填 true。同樣的道理套用在「資料撐不撐得過重新部署」與「備份真的跑過」這兩項
上：紅燈代表「這件事沒被驗證過」，不等於「這件事壞了」——但兩者都必須被當
作沒過，不能因為看起來大概沒問題就先填成過。

## 然後

把探到的東西寫成 facts JSON，跑：

    cd plugins/starter-kit
    python3 -m checks.collect facts.json reports/

（模組內用的是相對匯入，一定要用 `-m checks.collect` 這種模組寫法跑，
直接 `python3 checks/collect.py` 會匯入失敗。）

報告在 `reports/health-check.html`。**用他看得懂的話講紅的那幾項**，
不要把 JSON 貼給他。

## 講結果的方式

綠的一句話帶過。紅的要講三件事：哪裡不對、會有什麼後果、下一步做什麼。
不要用「請檢查您的設定」這種話 —— 他不知道要檢查什麼。
