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
- 🔄 **Phase 1 — 確定性幾何管線**（`plans/phase1-geometry.md`，in-progress）
  - Python 編排 + 拆兩個 API workflow + alpha 緊裁/塞目標框/擺位/陰影自適應 + config 微調鈕
  - 平面接觸線先用 config 可調固定值
- ⬜ **Phase 2 — 深度圖自動偵測水平面**（`plans/phase2-depth-detection.md`，draft）
  - 把接觸線從 config 固定值換成每張生成圖自動偵測；失敗 fallback 回 Phase 1 固定值

## 階段依賴

- Phase 2 **依賴** Phase 1 完成（偵測只是把 Phase 1 的 `surface_y` 來源從固定值換成自動求得，管線其餘不動）。
- 兩階段不可並行——Phase 2 插點就在 Phase 1 打通的「背景生成後、幾何計算前」。

## 守住邊界（V1/V2 共同排除）

自動去背、IP-Adapter、ControlNet 風格控制、AI 影片生成、n8n、自動發布、多鏡頭一致性、自訂合成節點。輸入必須是具 alpha 的去背 PNG（JPG 擋下報錯）。
