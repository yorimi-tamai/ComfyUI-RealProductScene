# Phase 1 — 確定性幾何管線 — Plan

> Python 編排 ComfyUI，任意去背 PNG 自動緊裁/縮放/擺位/接地，config 可微調；接觸線先用固定值
> 狀態：in-progress
> 最後更新：2026-07-21

## 為什麼做

V1 的產品縮放與位置全為那箱面紙手調，換比例不同的產品就得重調、陰影還會變形。Phase 1 把「幾何自適應 + 管線編排」打通：Python 讀去背 PNG 的實際輪廓，自動縮進目標框、擺到接觸線上、陰影隨產品派生，讓使用者只需準備 PNG + 打提示詞。接觸線此階段先用 config 可調固定值（自動偵測留給 Phase 2），先快拿到可用的 V2。

## 改什麼／範圍

- 新增 `scripts/` 下的 Python 編排層（client / geometry / prompt_builder / generate）
- 把現有單一 workflow 拆成兩個 API graph（背景生成、合成），供 Python 注入參數
- 擴充 `config/*.json` schema（目標框、微調鈕、固定接觸線）
- 不動 V1 的 UI workflow；不裝任何非內建 ComfyUI 節點

## 任務

- [x] 1. `git init` + 首次 commit（現有 V1 規格、workflow v2、PLAN 檔），建立可回溯基線
- [x] 2. 擴充 config schema：`product.json` 加 `target_box`(width_frac/height_frac) 與 `overrides`(scale_mult/offset_x/offset_y/shadow_opacity/shadow_blur/shadow_offset_y)；`scene.json` 加 `surface_line_frac`
- [ ] 3. 從 `product_scene_composite_v2_api.json` 拆出 `workflows/comfyui_api/bg_generate_api.json`（只背景生成 + 輸出）
- [ ] 4. 拆出 `workflows/comfyui_api/composite_api.json`（LoadImage 背景 + 產品 + 陰影鏈 72–79 + 產品合成 69 + Save）
- [ ] 5. `scripts/comfy_client.py`：POST /prompt、poll /history/{id}、GET /view 取圖
- [x] 6. `scripts/prompt_builder.py`：讀 scene.json 填 `prompts/scene_prompt_template.txt` 變數，組背景 prompt
- [x] 7. `scripts/geometry.py`：alpha `getbbox()` 緊裁 → 等比塞目標框(×scale_mult) → 算產品 x/y（底部貼 surface_y + offset）
- [x] 8. `scripts/geometry.py` 陰影：寬度隨產品、以實際底部為錨、壓扁、opacity/blur/offset_y 可調（取代 V1 固定座標陰影）
- [ ] 9. `scripts/generate.py`：主編排器（讀 config → 驗證 PNG alpha，JPG/無 alpha 報明確錯 → 背景 graph → 幾何 → 合成 graph → 存最終圖）；CLI `python scripts/generate.py`
- [ ] 10. 端到端驗證（見驗收條件）

## 驗收條件

- 情境（task 2）：改 config 欄位後，JSON 仍合法可被 Python 讀入；產品識別欄位（name/type/image）保留；V1 手動 `scale`/`position_x`/`position_y` 由 `target_box`+`overrides` 取代（單一 scale 來源，避免衝突）。
- 情境（task 3–4）：兩份拆出的 API graph 各自能被 ComfyUI `/prompt` 接受並跑完（背景 graph 出空背景；合成 graph 給定背景+產品出合成圖）。
- 情境（task 5）：以 client 送一份 workflow，能取回輸出圖 bytes。
- 情境（task 7–8）：丟寬箱、高瘦瓶、方形三種去背 PNG，各自都被縮進目標框不爆框、底部貼在 `surface_line_frac` 線上、陰影寬度隨產品且接地不飄。
- 情境（task 9）：丟一張 JPG 或無 alpha PNG → 程式擋下並印出明確錯誤、不崩、不產出壞圖。
- 情境（task 10）：調 `overrides.scale_mult`／`offset_x/y` → 產出圖的大小/位置對應改變（微調鈕生效）。

## 決策紀錄

| # | 決策點 | 選了 | 理由 |
|---|---|---|---|
| 1 | 幾何自適應放哪 | Python 前處理 + 打 API | ComfyUI 無原生 alpha bbox 裁切；Python 算幾何、ComfyUI 只收數字，維持全內建節點 |
| 2 | 產品尺寸規則 | 等比塞進目標框 | 對超寬/超高產品都不爆框，比「依單邊佔比」穩 |
| 3 | workflow 結構 | 拆背景生成 / 合成兩個 graph | 讓 Python 能在生成背景後、擺產品前介入；Phase 2 偵測才有插點，避免重工 |
| 4 | 接觸線來源（本階段） | config 可調固定值 | 自動偵測是最高風險項，隔離到 Phase 2；先用固定值快打通管線 |
| 5 | 容錯邊界 | 好預設 + config 微調鈕 | 承認自動非萬能，極端比例產品可手動覆蓋 |
| 6 | JPG/無 alpha | 擋下報錯 | 合成鏈靠 alpha 產 mask；自動去背延續 V1 排除，不在範圍 |

## 架構

```
[C] generate.py 主編排
 ├─[C] config loader ── 讀 config/*.json（[D] 檔案）
 ├─[C] 驗證 alpha（JPG/無 alpha → 報錯中止）
 ├─[C] prompt_builder ── scene.json + template → 背景 prompt
 ├─[T] comfy_client → [T] ComfyUI /prompt（背景 graph bg_generate_api.json）→ 空背景圖
 ├─[C] geometry ── PIL getbbox 緊裁 → 塞目標框 → 產品 x/y → 陰影參數（純數學）
 │       接觸線 surface_y ← [D] scene.json.surface_line_frac（Phase 1）
 └─[T] comfy_client → [T] ComfyUI /prompt（合成 graph composite_api.json 注入數字）→ 最終圖
```
（Phase 1 全程無 [L]LLM 決策、無 [A]子代理；ComfyUI 內仍是擴散模型生圖，但由固定 workflow 承載。）
