---
name: deploy
description: 把改好的東西送上線 —— 先上測試環境看，確認沒問題再上正式版。使用者說「上線」「發布」「讓大家可以用」時使用。
---

# 上線

## 流程

1. 測試綠了嗎？不綠就先修，不要問他要不要硬上。
2. 跑 `python3 scripts/check_deploy.py`（檢查 `DEBUG`、`SECRET_KEY`、
   `ALLOWED_HOSTS` 這三個正式環境設定安不安全）。有問題就修，別上。
3. 確認站在 `develop` 分支上（沒有就照下面「分支不是他要處理的事」處理），
   push → 自動上 staging。
4. **給他 staging 的網址，請他自己看一眼。**
5. 他說對了，才 merge 到 `main` → 上正式版。

## 分支不是他要處理的事

他不知道什麼是分支，也不會發現自己「站錯」了。這件事你自己處理，
**不要**問他「你現在在 main 還是 develop」——這種問題他答不出來，
問了也白問。

先跑 `git branch --show-current` 看現在在哪，`git branch --list develop`
看 `develop` 存不存在——這兩件事只在這裡確認一次，後面提到「切到
develop」都照這個結果走：不存在就 `git checkout -b develop`，已經存在
就 `git checkout develop`，不再重新判斷一次。確認完再照情況處理：

- **`develop` 不存在，且 `main` 上沒有其他待處理的改動或 commit**：切到
  develop（`git checkout -b develop`，從現在的位置分出去）。之後每次上線
  都用這條，不用再建第二次。
- **已經站在 `develop`**：不用動，直接往下走流程第 3 步。
- **站在 `main` 上，且有還沒 commit 的改動**：這些改動是要先上 staging
  看的，不能直接留在 `main` 上。`git stash` 存起來 → 切到 develop（依照
  上面的判斷） → `git stash pop` 把改動接回來 → 在 `develop` 上 commit。
  **不要在 `main` 上 commit** —— `main` 只留給「已經上過 staging、使用者
  確認過」的版本。
- **改動已經 commit 在 `main` 上，但還沒 push 到遠端**：這個 commit 要搬
  到 `develop`，但 `main` 上很可能還有更新的、還沒 commit 的改動——他不
  會特別講「這是下一批」，commit 一次之後接著往下改、沒有再 commit，是
  很常見的狀態。如果不先檢查就直接 `git reset --hard origin/main`，這些
  沒 commit 的東西會被整個清空、救不回來，而且他不會知道發生了什麼事。
  所以動 `main` 之前一定要先確認乾不乾淨：
  1. `git status --porcelain` 看有沒有還沒 commit 的東西，有就先
     `git stash` 存起來。
  2. 切到 develop（依照上面的判斷） → `git merge main` 把這個 commit
     接上去。
  3. `git checkout main` 切回來，`git reset --hard origin/main` 把
     `main` 退回上一個遠端已知的位置。這樣 `main` 不會提早帶著還沒被
     使用者看過的改動跑出去。
  4. 如果第 1 步有 stash，`git stash pop` 接回來——這批改動比剛才搬到
     develop 的那個 commit 更新，是要留在 `main` 上繼續改的，不能跟著
     被清掉。
- **改動已經 commit 也 push 到遠端 `main` 了**：這已經算是上了正式版，
  不是「站錯分支」能補救的範圍——不要假裝沒發生過、也不要事後偷偷改
  `main` 的歷史。跟他說清楚現在正式版已經帶著這個改動，接下來要做的是
  照流程補跑一次 staging 確認（如果 staging 也一起看過沒問題就講清楚
  「這次流程順序反了，但內容已經確認過」），而不是重新問一次「要上線
  嗎」。

處理完這些，回到流程第 3 步繼續，不用再跟他確認分支的事。

## 上正式版一定要問

他不會用 pull request，所以 merge 由你代做。但「上正式版」屬於對外
發布——跟刪除一樣，是這個 plugin 裡少數兩件**一定要停下來問**的事
（見 `behavior/pillars.md`），不是「順便提一下」就算數。

問法：

> staging 看起來對嗎？對的話我就把它變成正式版了。

**他還沒回答之前，不要 merge。** 不要用「我先 merge，如果有問題再改」
這種說法帶過去——上正式版是單向的，錯了不是「改回來」那麼簡單，一定要
等他明確說「對」或「可以」才動手。他沉默、答非所問、或只回覆 staging
本身的內容而沒有講「可以上」，都不算同意，再問一次。

## Zeabur 怎麼碰

先看健檢報告說走哪一條路（CLI／MCP／瀏覽器）——健檢 skill 已經探測過，
不用自己重新猜。**不要假設哪條可用**：被擋掉的 `npx zeabur` 或 `curl`
的錯誤訊息不會提到網路白名單限制，查不出原因，會浪費時間在錯的方向上
除錯。

如果要重新部署：**MCP 做不到**，這是它 26 個工具裡沒有的其中一項。要
重新部署得走 CLI 或瀏覽器，照健檢報告指的那條走。

## 資料庫改動

`manage.py migrate` 在容器啟動的時候自己會跑（entrypoint 裡寫好的），
**不要放進 GitHub Actions**——Actions 碰不到容器裡的 SQLite 檔案，那個
檔案活在 Zeabur 的 volume 上，不在 Actions 的執行環境裡。

## log 只留 48 小時

Zeabur 的 log 預設只留 48 小時（Dev 方案，一個月 5 美元，可以延到 7 天）。
他週五出問題、週一才跟你講，log 早就沒了。遇到這種情況直接跟他說「這段
時間已經查不到了」，**不要假裝在查**、也不要編一個查詢結果出來。
