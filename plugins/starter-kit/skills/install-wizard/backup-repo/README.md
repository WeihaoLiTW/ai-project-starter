# 備份

這個 repo 是私有的，因為裡面有使用者帳號和密碼。

每天自動從正式環境抓一份資料庫快照，存成這個 repo 的 Release，保留三個月。

## 要設定的東西

| 名稱 | 種類 | 內容 |
|---|---|---|
| `ZEABUR_API_TOKEN` | secret | Zeabur 的 API token |
| `ZEABUR_SERVICE_ID` | variable | 正式環境那個服務的 ID |
| `ZEABUR_ENV_ID` | variable | 正式環境的環境 ID |
| `CODE_REPO` | variable | 程式碼 repo，格式 `帳號/repo 名稱` |

服務 ID 與環境 ID 要從 Zeabur 網站的網址列抓 —— CLI 沒有任何指令列得出來。
安裝嚮導會帶你做這一步。

## 要還原的時候

到 Releases 下載那天的 `.sqlite3` 檔，交給 Claude，跟它說你要還原到哪一天。
