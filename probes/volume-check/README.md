# volume-check 探針

一個丟完即棄的小程式，用來確認容器平台上「資料什麼時候會不見」。

驗證結果會決定部署流程裡 volume 那一步該排在哪，以及環境健檢要檢查什麼。
驗完可以整個資料夾刪掉。

## 它做什麼

啟動時往 `DATA_DIR/events.log` 寫一行 `BOOT`，並提供兩個網址：

| 網址 | 作用 |
|---|---|
| `/` | 顯示整份 log |
| `/write?msg=xxx` | 追加一行，然後顯示整份 log |

零依賴，只用 Python 標準庫，所以 build 很快、不會有套件問題。

## 本機已驗證的結果（Docker，2026-08-03）

| 步驟 | 動作 | 結果 |
|---|---|---|
| 1 | 不掛 volume，寫入 `before-volume` | 寫進去了 |
| 2 | 重新部署，**仍然不掛 volume** | **資料消失**，只剩新的 BOOT |
| 3 | 第一次掛 volume，寫入 `after-volume` | 寫進去了 |
| 4 | 重新部署，掛同一個 volume | **兩筆都在** |

**結論：資料消失的原因不是「掛載 volume 會清空目錄」，而是「沒掛 volume
的期間，寫進去的東西本來就活不過下一次部署」。**

第 2 步證明了這點 —— 根本沒有掛載動作，資料就已經沒了，因為它們待在容器的
臨時層，容器一換就沒。

實務規則因此是：**volume 必須在第一次啟動前掛好。**

## 在 Zeabur 上重跑一次

Zeabur 的實作可能與標準 Docker 不同，所以要在平台上再驗一次。

1. 從 GitHub 部署本 repo，**Root Directory 設成 `probes/volume-check`**，
   port 填 `8080`
2. **先不掛 volume** → 開 `/write?msg=before-volume` → 再開 `/` 確認看得到
3. **重新部署（仍不掛 volume）** → 開 `/` → 預期只剩新的 BOOT
4. **掛 volume 到 `/data`** → 開 `/write?msg=after-volume`
5. **再重新部署** → 開 `/` → **預期 `after-volume` 那行還在**

第 5 步是重點，它同時驗證核心成功條件（資料跨重新部署存活）。

第 3 步若結果與本機不同（資料還在），代表 Zeabur 預設就有某種持久化，
那是好消息，要記錄下來。

## 本機自己跑

```
docker build -t volume-probe .
docker run --rm -p 8080:8080 -v probe-vol:/data volume-probe
```

然後開 http://localhost:8080
