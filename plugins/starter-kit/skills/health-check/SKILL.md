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

**這四件事是你要做的，不是探針要做的。** 探針只讀 facts 檔裡的值下判斷，
它們不會自己連網路、不會自己開瀏覽器。`zeabur` 探針尤其如此：它只看
`facts["zeabur"]` 裡的 `cli`、`mcp`、`browser`、`proven` 四個值。探得到一條路
只代表「connectivity 在」，不代表「這條路真的能用」——**只有實際跑成功一次
唯讀操作（例如列出專案），才可以把 `proven` 寫成 `true`**。連得上但沒跑過、
跑過但失敗、或忘了寫這個欄位，都要當作沒證明過，不要因為看起來可以連就先
填 true。

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
