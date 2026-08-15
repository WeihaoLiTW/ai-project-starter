# 學員專案 × Starter Kit 適配比較

2026-08-15

一句話目的:告訴你這 6 個學員專案,哪些能用現有 kit 的 infra/env 做出來、哪些不能、
訓練要怎麼調、以及要不要為此擴充 kit。

來源:kit 能力範圍取自
`docs/superpowers/specs/2026-08-08-starter-kit-design.md`
與
`docs/superpowers/specs/2026-08-14-sunday-101-training-readiness-design.md`;
學員需求取自本次訊息提供的清單。

## 頭條

Kit 是「**server-rendered Django 網頁 app + SQLite + Zeabur 部署**」。這 6 個專案橫跨
**三種 paradigm**:網頁工具、原生手機 app、資料自動化。**清楚合身的只有花(兩個)與
狗狗;朵拉部分合身;米奇(手機)與 Bee(自動化)是不同 paradigm,kit 不是對的載體。**

## Kit 能力範圍(比較基準)

- **是什麼**:server-rendered Django(伺服器直接吐 HTML,無 API 層)+ SQLite 檔案資料庫,
  跑在 Zeabur 容器,GitHub 管程式碼/CI/備份,附 Django admin(可視資料後台)、使用者
  系統、行為/安全層。
- **擅長**:內部網頁工具 —— 表單、CRUD(增刪查改)、計算、簡單圖表、資料儲存,幾十人
  內部規模。
- **不做**:原生手機 app(App Store 上架、IAP 內購、手寫筆刷、完整離線)、重前端互動、
  外部市場資料抓取、把現成報表自動整理後填入雲端試算表/簡報。

## 比較矩陣

| 專案 | 主要 paradigm | 適配 | 關鍵 gap(kit 做不到的) |
|---|---|---|---|
| 花 #1 排班系統 | 內部網頁工具 | ✅ 合身 | 無 —— 這正是 kit 的招牌範例 |
| 花 #2 開店評估 | 網頁工具(計算表單) | ✅ 合身 | 無 |
| 狗狗 App | 網頁工具(CRUD+計算+圖表) | ✅ 合身(有但書) | 「完整離線」server-rendered 做不到;圖表要一點前端 |
| 朵拉 訂單/採購 | 網頁工具 + 外部資料 + Sheets | 🟡 部分 | 比價(外部市場價格,kit 無資料來源);下單表格自動更新(Sheets 自動化) |
| Bee 報表自動化 | 資料自動化(非 web app) | ❌ 不合 | 讀現成報表→轉換→填雲端試算表/簡報,不是網頁 app,kit 是錯載體 |
| 米奇 The Cathedral | 原生手機 app | ❌ 不合 | 手寫筆刷、IAP 點燭/贊助、完整離線、App Store 上架 = iOS app |

## 逐案

**花 #1 排班 / #2 開店評估** —— 兩個都是「輸入 → 計算 → 存/看」的內部網頁工具。排班是
kit spec 一路拿來當範例的那個;開店評估是一張計算表單(租金/坪數/人力 → 月花費/營收)。
kit 直接做,零 gap。

**狗狗 App** —— 11 個功能(檔案、飼料計算、提醒、洗澡美容、記帳、鮮食指南、體重追蹤、
用藥日誌、健康日誌、醫療護照、過敏黑名單)全是 CRUD + 計算 + 圖表,跑在 SQLite 上,
Django admin 剛好當資料後台。兩個但書:(1)「完整離線可用」—— server-rendered 網頁是
連線的,要離線得做 PWA 或 native(超出 kit);(2) 圖表(SVG 折線、圓餅)要一點前端,
可由伺服器產 SVG 解決。整體合身,適合逐個功能 build。

**朵拉** —— 核心計算合身:超交/缺交率、rebate 計算、預估下單量,都是資料進來算一算。
兩塊超出範圍:**相似品項市場價格比價**要外部市場資料,kit 沒有資料來源、抓取也不在簡單
envelope 裡;**下單表格自動更新**是 Google Sheets 自動化。所以 kit 能做骨架(內部下單
分析工具),但比價與表格自動化要另外納入能力。

**Bee** —— 五項都是「讀公司現成報表 → 整理成想要的數據(大類貢獻/ABC/客群/客單/時段)
→ 自動填進雲端表格與簡報 → 跨月比較」。這是**資料自動化**,不是網頁 app。用 Django 部署
一個網站解決不了它,載體錯了。它真正對應的是「Claude + Google Sheets/Slides + skill」的
自動化助手 —— 正是 kit spec 裡 deferred 到 v1.1 的「Excel 報表 skill」方向。

**米奇 The Cathedral** —— 手寫抄經(筆刷 canvas)、環境音效、IAP 小額贊助/點燭、朝聖
數位護照、明信片生成、完整離線。這是一個 **iOS / 原生手機 app**。Django + Zeabur 產出的是
一台網頁伺服器,不是 App Store 上架的 app。即使砍成網頁版,手寫筆刷 + 離線 + 內購三塊
仍不在 kit(也不在 101 範圍)。

## 訓練 slides / 概念覆蓋評估

**5 個概念(git、model 每次重新開始、dev→staging→prod、行為層、真服務要有哪些東西)
是 paradigm 無關的 —— 對 6 個學員全都適用,不用改。**

**demo(Django 部署 loop)+ 學員動手(改測綠 commit push)是網頁 app 專屬的。** 它示範的
「安全開發流程」可以轉移到任何 paradigm,但**具體那套 Django/Zeabur 只對得上花、狗狗、
朵拉核心;對不上米奇(手機)與 Bee(自動化)**。

要調整的三處:
1. **設定期望**:這場教的是「安心開發的流程 + 一個網頁 app demo」,不是當天做完每個人的
   app。流程轉移得過去,但具體技術棧只對上約一半的人。
2. **對米奇/Bee 誠實給不同路**:網頁 app 的 demo 對他們是「看得懂流程,但這不是我的路」。
   要嘛當場說明他們的路不同,要嘛把他們的專案重框成 kit 能做的形狀(見下方決策點)。
3. **朵拉/Bee 需要 Google Sheets**,但目前 spec 的 ADR-C 明訂**學員路徑不碰 Google**。
   這是直接衝突,要決定。

## 納入清單(要不要擴 kit / 訓練)

| 要納入的能力 | 為誰 | 現況 |
|---|---|---|
| 圖表共用範例(SVG 折線 / 圓餅) | 狗狗、朵拉、Bee | kit template 目前無現成圖表範例 |
| 資料自動化 / Sheets 路徑 | Bee、朵拉(表格更新) | = spec deferred 到 v1.1 的 Excel 報表 skill 方向 |
| 外部資料來源(市場比價) | 朵拉 | 不在 kit 的簡單 envelope,需另評估 |
| 手機 app 立場 | 米奇 | kit 不做 native;需重框成 web MVP 或明講超範圍 |
| 學員 Google connector | 朵拉、Bee | 與 ADR-C(學員不碰 Google)衝突,需先解 |

## 給你的決策點

1. **米奇**:重框成 web MVP(線上讀經 + 進度統計,砍手寫/IAP/離線),還是明講「原生 app
   超出這套的範圍」?
2. **Bee**:承認 kit 不是它的載體,改給「Claude + Sheets/Slides 自動化」的路(v1.1 方向),
   還是這次先不收 Bee 的真專案、只帶他走流程?
3. **朵拉/Bee 的 Google Sheets**:要不要為他們把 Google connector 納回學員路徑(改 ADR-C),
   還是維持「學員不碰 Google」、Sheets 部分留到課後?
4. **圖表**:要不要在 template 加一個 SVG 圖表共用範例(狗狗/朵拉/Bee 都用得到)?
5. **slides 範圍**:這份比較要做成幾張投影片放進訓練材料(例如「你的專案適不適合這套」
   一張總覽 + 逐案一頁),還是只做總覽一張?
