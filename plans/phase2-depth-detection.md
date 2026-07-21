# Phase 2 — 深度圖自動偵測水平面 — Plan

> 把接觸線 surface_y 從 config 固定值換成每張生成圖用深度圖自動求得；失敗 fallback
> 狀態：draft（Phase 1 完成後才開工）
> 最後更新：2026-07-21

## 為什麼做

Phase 1 的接觸線是 config 固定值——換一個桌面高低不同的背景 prompt，產品就不再接地。Phase 2 讓 `surface_y` 每張生成圖自動偵測，真正做到「換任意背景也接地」。用深度圖找下方水平面（比 classic CV 對各種場景更穩，又不需語意分割那麼重）。

## 改什麼／範圍

- 新增 `scripts/detect_surface.py`
- `scripts/generate.py` 在「背景生成後、幾何計算前」插入一次偵測呼叫
- 可能引入深度模型依賴（ComfyUI 內或 Python transformers）——**開工前先實測定案**
- 其餘管線（geometry / 合成 graph / config 微調鈕）不動

## 任務

- [ ] 1. 定案深度模型取得方式：ComfyUI 內深度預處理（Depth Anything V2 / comfyui_controlnet_aux，非內建依賴需評估）vs Python transformers Depth-Anything——各跑一次比安裝負擔與輸出品質後選一
- [ ] 2. `scripts/detect_surface.py`：背景圖 → 深度圖 → 找下方水平面上緣 → 回傳 surface_y 與可用寬度
- [ ] 3. 接進 `generate.py`：背景後、幾何前呼叫；偵測失敗或信心低 → fallback 回 scene.json.surface_line_frac
- [ ] 4. 驗證（見驗收條件）

## 驗收條件

- 情境（task 2）：給一張含明顯桌面的生成背景 → 回傳的 surface_y 落在桌面上緣附近（目視誤差可接受）。
- 情境（task 3）：偵測模組故意失敗（如丟純色圖）→ 管線不崩、自動用固定值 fallback、有 log 提示。
- 情境（task 4）：同幾張產品換 3 種桌面高低不同的背景 prompt → 產品都自動接地，不用手改 config。

## 決策紀錄

| # | 決策點 | 選了 | 理由 |
|---|---|---|---|
| 1 | 偵測方法 | 深度圖找水平面 | 比 classic CV 對各種場景穩；比語意分割(SAM)輕、不需切乾淨的桌面 mask |
| 2 | 偵測失敗處置 | fallback 回 Phase 1 固定值 | 承接「好預設 + 微調鈕」邊界；自動非萬能時不讓整條管線崩 |
| 3 | 深度模型來源 | 待實測（ComfyUI 內 or Python） | 依賴與品質未知，Phase 1 不綁死；Phase 2 開工實測再定 |

## 架構

```
[C] generate.py（Phase 1 管線）
        │ 背景圖產生後
        ▼
[C] detect_surface ── [L/T] 深度模型（Depth Anything，來源待定）→ 深度圖
        │ 找下方水平面上緣 → surface_y（信心低 → fallback [D] scene.json）
        ▼
[C] geometry（其餘同 Phase 1，surface_y 來源改為此偵測結果）
```
