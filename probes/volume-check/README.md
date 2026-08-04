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

## Zeabur 上的實測結果（2026-08-04）— 已完成

實際租了一台 Tencent Tokyo 2 vCPU / 4 GB 跑完，**結論與本機 Docker 一致**。

最後沒有用上面那支 HTTP 程式，改用更簡單的做法：`alpine` + `sleep infinity`
兩個服務（一個掛 volume、一個不掛），用 `zeabur service exec` 直接讀寫檔案。
不用開 port、不用公開網址、不用 GitHub，而且看得比網頁清楚。模板見
`zeabur-no-volume.yaml` 和 `zeabur-with-volume.yaml`。

| | `/data` 掛載狀態 | 重啟後 marker |
|---|---|---|
| 對照組（無 volume） | 無獨立掛載 | **GONE** |
| 實驗組（有 volume） | `/dev/vda2 on /data type ext4` | **PRESENT** |

**template YAML 的 `volumes` 宣告確實生效** —— 實驗組的 `/data` 是真的 ext4
掛載點。所以部署設定（含 volume）可以整份寫在 repo 裡，不必存在某個人的
瀏覽器操作記憶裡。

### 過程中撞到的平台限制

- **PREBUILT（Docker image）服務不能 in-place redeploy**，會回
  `You must bind a GitHub repository to the service to allow redeploying in-place`。
  改用 `service restart`，效果一樣（容器重建）。
- **`service exec` 需要 `--env-id`，但 CLI 沒有任何指令能列出環境。**
  只能開網頁從 URL 的 `?envID=` 撈。
- **記憶體**：ZeaburOS + K3s + 兩個 trivial 容器就吃掉 1503 MB / 3659 MB。
  這代表 2 GB 的機器跑不動實際架構。

完整分析見

    docs/research/2026-08-03-starter-kit-infra-selection.html

## 本機自己跑

```
docker build -t volume-probe .
docker run --rm -p 8080:8080 -v probe-vol:/data volume-probe
```

然後開 http://localhost:8080
