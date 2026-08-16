# ai-project-starter

用 Claude 做出你的第一個專案 —— 寫給完全沒有技術背景的人。

## 這是什麼

一份手把手的教學，帶你從「什麼都還沒裝」走到「做出一個真的能用的小專案」。

過程中你不需要先學會寫程式。你要學的是怎麼把想做的事情講清楚、怎麼讓 AI 幫你把它做出來、以及做出來之後怎麼確認它是對的。

## 給誰看

沒寫過程式、沒用過命令列、看到終端機黑畫面會緊張的人。

不預設你懂任何技術名詞。每個工具第一次出現時都會先講「它在幹嘛」，再講怎麼用。如果你已經是工程師，這份教學對你來說會太慢。

## 範圍

- 環境怎麼裝：需要裝什麼、裝在哪、怎麼確認裝好了
- 第一個專案怎麼開：從一句話的想法，到一個跑得起來的東西
- 怎麼跟 AI 講話：把模糊的想法變成 AI 接得住的需求
- 非技術者也能用的工具與觀念：有哪些現成的東西可以直接用，不用自己做

## 不做什麼

- 不教程式語言語法。這裡不會有「什麼是 for 迴圈」這種章節
- 不是 Claude API 的技術文件。要查 API 請看官方文件
- 不談進階 agent 架構、多 agent 協作、或 prompt engineering 的理論

## 這個 repo 同時是什麼

這個 repo 有兩個身分：

1. **一份教學**（上面「這是什麼」講的內容）。
2. **一個 Claude plugin marketplace** —— `.claude-plugin/marketplace.json` 底下
   掛了一個叫 `starter-kit` 的 plugin，貼一段開場白、裝上這個 plugin，就能讓
   Claude 帶你把本機環境（git、行為三支柱、測試綠了才存檔的安全網、一個最小
   骨架）裝起來，這是預設路徑。GitHub、Zeabur、Django 專案骨架是加購項目，只有
   你之後真的需要備份、分享、或把東西放上網給別人用時才裝，不是預設會做的事。
   plugin 本身在 `plugins/starter-kit/`。

## 從這裡開始

- **要開始裝環境（預設路徑，本機優先）**：先照
  `docs/onboarding/walkthrough.md` 的第 0 步（裝對版本的 Claude Desktop）、
  第 1 步（切到 Cowork、確認本機模式）把前置作業做完——這兩步不管走哪條路都要
  做。接著打開 `docs/onboarding/kickoff-prompt-local.md`，複製貼給 Claude 的那段
  話就在裡面。這條路只裝到「能在自己電腦上改程式、跑測試、本機自動存檔」為止，
  不碰 GitHub、Zeabur、Django。
- **之後要備份、分享、或把東西放上網給別人用（加購，非必須）**：改用
  `docs/onboarding/kickoff-prompt.md`，並照 `docs/onboarding/walkthrough.md`
  第 3 步（安裝嚮導）之後的內容一步步做，會多裝 GitHub repo、Django 樣板、
  Zeabur 部署。
- **想知道這整套東西為什麼是這樣設計**：
  `docs/superpowers/specs/2026-08-08-starter-kit-design.md` 是完整的設計 spec，
  含已知限制清單與每個技術決策的取捨紀錄（ADR）。

## Roadmap

環境包（plugin 骨架、三個保命繩 hook、本機優先的最小骨架、Django 樣板與
GitHub／Zeabur 部署備份的加購路徑、開場白與走查文件）已經完成，見上面
「從這裡開始」。之後的方向：

- [ ] 未開始 — 拿環境包做出第一個真的服務（例如排班系統），驗證「環境備妥」
  之後接下來怎麼跟 Claude 把模糊的想法變成能用的東西
- [ ] 未開始 — 更多非技術者能直接用的工具（Excel 報表 skill 等，目前列在 v1.1）
