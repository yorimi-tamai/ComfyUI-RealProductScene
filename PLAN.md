# AI Product Scene Generator — Master Roadmap

> 通用可客製產品情境合成管線：一張去背 PNG + 背景提示詞 → 自動產出場景合成產品照
> 狀態：in-progress
> 最後更新：2026-07-21

## 大方向

V1（已完成）：手動 ComfyUI workflow，把特定產品去背 PNG 合成到 AI 背景 + 接觸陰影。
V2（本 roadmap）：加一層 Python 編排 + 幾何自適應，讓**任意比例產品**都能自動縮放、擺位、接地，並可用 config 微調。

完整設計見 `plans/`。決策脈絡見 `~/.claude/plans/sparkling-knitting-wombat.md`（plan mode 核准版）。

## 進度

- ✅ **V1 — 手動合成 workflow + 接觸陰影**（已驗證，見 `handoff-archive/…接觸陰影｜#1…`）
- ✅ **Phase 1 — 確定性幾何管線**（`plans/phase1-geometry.md`，done）
  - Python 編排 + 拆兩個 API workflow + alpha 緊裁/塞目標框/擺位/陰影自適應 + config 微調鈕
  - 平面接觸線先用 config 可調固定值；已 live 驗證端到端（藤籃產品接地成功）
  - ⚠️ 已知限制：隨機 seed 下背景桌面位置會變，固定 `surface_line_frac` 需手動對——正是 Phase 2 要自動化的
- ✅ **Phase 2 — 產品主導配光（product-led lighting）**（`plans/phase2-product-led-lighting.md`，done）
  - 反轉思路：產品固定，背景遷就產品的光。讀產品照的色溫/明暗/柔硬度/光向 → 寫進背景 prompt，讓生成場景與產品同調（守「不改產品」規則）
  - 光向分析也驅動陰影落向。已 live 驗證：藤籃 auto 配光後背景明顯轉暖/亮/柔、與產品同調
  - ⚠️ 未解：接地陰影仍為方塊柔霧、無漸層（接觸感不足）；擺位仍靠固定 surface line
- ✅ **Phase 2.5 — 陰影接觸核（雙層陰影）**（done，小型自足改進）
  - 在柔散陰影下疊緊實深色低模糊接觸核，合成序：背景→柔散→接觸核→產品
  - 已 live 驗證（同 seed 對比）：基座接觸感明顯優於單層均勻霧
  - ⚠️ 仍非完美：柔散層邊緣略帶方形、整體仍是「去背圖貼生成背景」本質
- ⬜ **Phase 3 — 深度圖自動偵測水平面**（`plans/phase3-depth-detection.md`，draft）
  - 把接觸線從 config 固定值換成每張生成圖自動偵測；失敗 fallback 回固定值

## 階段依賴

- Phase 2/3 都**依賴** Phase 1（管線骨架）。
- Phase 2（配光）插點在「背景生成**前**」（先分析產品再生成背景）；Phase 3（擺位偵測）插點在「背景生成**後**、幾何前」。兩者互不衝突，可先後做。

## 為什麼調整方向（2026-07-21 Phase 1 驗收後）

Phase 1 live 驗收暴露兩問題：產品浮空（接地差）＋產品與背景光線不一致。使用者反轉思路——**以讀入的產品照為主、去生成適合的背景**——同時解光線一致與陰影方向，且不牴觸「不改產品」。故插隊為 Phase 2，深度偵測擺位順延 Phase 3。

## 守住邊界（V1/V2 共同排除）

自動去背、IP-Adapter、ControlNet 風格控制、AI 影片生成、n8n、自動發布、多鏡頭一致性、自訂合成節點。輸入必須是具 alpha 的去背 PNG（JPG 擋下報錯）。
