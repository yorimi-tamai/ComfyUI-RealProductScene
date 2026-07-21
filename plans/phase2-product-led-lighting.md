# Phase 2 — 產品主導配光（product-led lighting）— Plan

> 讀產品照的光特徵 → 驅動背景生成 prompt 與陰影落向，讓場景遷就產品（不改產品）
> 狀態：done
> 最後更新：2026-07-21

## 為什麼做

Phase 1 驗收暴露：產品浮空 + 產品與背景光線不一致（產品自帶打光，背景各生各的）。改產品去配背景會牴觸「不改產品」規則。反轉：**產品是固定錨，背景是可變的那個**——分析產品照的光，讓 AI 生成同調的背景；同一份光向分析也決定陰影往哪落，改善接地。產品像素 100% 不動。

## 改什麼／範圍

- 新增 `scripts/analyze_product_light.py`（純 PIL，離線可驗）
- `prompt_builder` / `generate.py`：`scene.json.lighting == "auto"` 時，用產品分析推出的 lighting 子句填入背景 prompt
- `geometry.py`：陰影水平落向由分析的 `shadow_dir` 決定（取代寫死往右）
- `scene.json`：`lighting` 預設改 `"auto"`（仍可填明確文字覆蓋）

## 任務

- [x] 1. `analyze_product_light.py`：從產品 alpha 內像素估 色溫(warm/neutral/cool)、明暗(high/natural/low-key)、柔硬(soft/moderate/hard)、光向(左/右/上/均勻)；輸出 lighting 子句 + `shadow_dir`
- [x] 2. `prompt_builder`：支援用「給定的 scene_cfg」渲染（lighting 可被 auto 子句取代）
- [x] 3. `geometry.compute`：加 `shadow_dir` 參數，陰影水平 offset 依它決定正負
- [x] 4. `generate.py`：分析產品 → 填 lighting → 生成背景；並把 `shadow_dir` 傳入幾何
- [x] 5. `scene.json` lighting 改 `"auto"`（保留手動覆蓋）
- [x] 6. live 驗證：同一張產品，比較 auto 配光前後背景是否更貼合產品色溫/明暗；陰影落向正確

## 驗收條件

- 情境（task 1）：對藤籃（暖色、偏均勻光）分析 → 色溫判為 warm、光向判為均勻或上方；對人工造的左亮右暗圖 → 光向判為「左」。
- 情境（task 4-6）：`lighting="auto"` 跑一次，背景 prompt 內含產品推出的光描述；產出背景的整體色溫/明暗明顯比 Phase 1 更接近產品（目視）。
- 情境（task 3）：`shadow_dir` 改變 → 陰影水平落向跟著改變（左右）。
- 情境（覆蓋）：`scene.json.lighting` 填明確文字 → 用該文字、不套 auto（手動鈕仍有效）。

## 決策紀錄

| # | 決策點 | 選了 | 理由 |
|---|---|---|---|
| 1 | 光線不一致怎麼解 | 產品主導：背景遷就產品 | 守「不改產品」；背景本來就是生成的、是可變項 |
| 2 | 分析可靠度邊界 | 色溫/明暗/柔硬可靠；光向為 best-effort、可覆蓋 | 方向從單張照片估計本就 noisy，不假裝精準 |
| 3 | 與 Phase 3 關係 | 先配光(Phase 2)、後擺位偵測(Phase 3) | 使用者當前痛點是光線一致；擺位偵測獨立、順延不衝突 |

## 架構

```
[C] generate.py
 ├─[C] analyze_product_light ── PIL 統計產品 alpha 內像素 → {溫度,明暗,柔硬,光向, shadow_dir, lighting子句}
 ├─[C] prompt_builder ── scene.json(lighting=auto→子句) + template → 背景 prompt
 ├─[T] ComfyUI 背景 graph（現在光描述隨產品）→ 背景
 ├─[C] geometry（shadow_dir 決定陰影落向）
 └─[T] ComfyUI 合成 graph → 最終圖
```
（全 [C]程式碼 + [T]ComfyUI；分析是規則式統計、無 [L]LLM。）
