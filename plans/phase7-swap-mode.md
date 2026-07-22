# Phase 7 swap 後端 — Plan
> 用 GPT 生的完整場景當模板，把場景裡 AI 假產品的位置刷回使用者真產品，繼承場景的自然陰影/光、同時產品像素 100% 真實。
> 狀態：done（9/9 task，2 例 live 驗證）
> 最後更新：2026-07-22

## 為什麼做
Phase 5 的橢圓烘陰影接觸感不夠，使用者驗收「不自然」。GPT 整張生成的場景陰影/光/接地極自然，但產品是 AI 重畫的、違反「不改產品」立案紅線。swap 兩全：GPT 生完整場景（含產品）當模板 → 對齊後把真產品刷回 → 陰影/光繼承 GPT、產品像素真實。PoC（`outputs/swap_poc.png`）已驗證此路明顯優於現有管線。

## 改什麼／範圍
- 新增第三後端 `backend: swap`，與 `comfyui`/`manual` 並存；合成沿用現有 ComfyUI `composite_api.json`。
- swap 分支**跳過** depth 深度偵測（`detect_surface`）、`bake_shadow`、Phase 2 配光（`analyze_product_light`）——陰影與光都來自 GPT 場景。
- 新 `align` 模組取代 depth/surface 決定產品位置；產出現有 `Geometry` 直接餵 composite。
- 碰到的檔案：`scripts/generate.py`（backend 分支）、新 `scripts/align.py`、`scripts/geometry.py`（defringe/force-cover util）、`workflows/comfyui_api/composite_api.json`（B 光包裹）、`config/generation.json`、`README.md`、`tests/`。

## 任務
- [x] 1. 加 `opencv-python` 到 ComfyUI venv（`"…/ComfyUI (1)/ComfyUI/.venv/bin/python" -m pip install opencv-python`），更新 `requirements.txt`。
- [x] 2. config + CLI 接線：`generation.json` 加 `backend:swap` + `scene_path`；`generate.py` 新 `--scene <path>`（implies swap，比照 `--bg`）；`resolve_backend` 加 swap 分支；swap 模式 `--shadow-dir` 忽略並警告。
- [x] 3. 新 `scripts/align.py`：多尺度 opencv `matchTemplate`（真產品去背圖當模板 vs GPT 場景）→ 位置+尺寸；四鈕 `--offset-x/y`/`--scale-mult` override 疊上；輸出組成現有 `Geometry`。（用 `TM_CCOEFF_NORMED`+透明區均值填，非 masked `CCORR`——後者尺度偏差誤鎖）
- [x] 4. `geometry.py` 加 defringe（alpha 內縮，預設 2px、可調，殺去背 halo）+ force-cover 微放大（2–4%，保證蓋過 GPT 假產品），套在 swap 產品裁切。（defringe 在 geometry.py；force-cover 放 `build_swap_geometry` 的 `cover_margin` 預設 0.03——尺寸決定處）
- [x] 5. `generate.py` main 接 swap 分支：跳過 depth/`bake_shadow`/配光；改用 `align`→`Geometry`；沿用 `composite_api.json` 貼合。（合成步驟順手抽成三後端共用；dry-run 也支援 swap）
- [x] 6. B 刷回：邊緣羽化 + 光包裹（場景光包進產品最外圈；產品內部不動）；強度 live 校準。
  - **卡點已解（使用者選 A）**：原「在 composite 圖插節點」與 `CLAUDE.md` 規則 6（不得臆造 workflow JSON）衝突 → 改**在 PIL 做**（`generate.py` 新 `bake_light_wrap`，比照 `bake_shadow`；ComfyUI 仍負責最終合成貼合）。
  - live 校準：`SWAP_DEFRINGE_PX=3`、`SWAP_LW_STRENGTH=0.28`、`SWAP_LW_RIM_PX=7`、`SWAP_LW_FEATHER_PX=0.0`。發現亮邊 halo 來自「羽化把半透明邊透出強背景」，非光包裹 → 關羽化 + defringe 加到 3px 解掉。screen 混合只碰 rim band，產品內部零改動。
- [x] 7. `README.md`：新增 swap 後端段（三後端對照表）+ GPT 前提（生成時餵真產品當參考、產完整場景、丟 inputs；不接 API）。
- [x] 8. 測試：加 `tests/test_align.py`（合成場景 locate + 四鈕 override + defringe + light-wrap 內部不動，16 項）+ `test_backend` 加 4 swap resolve 案；既有 shadow13/detect18/manual9 全綠、零回歸。
- [x] 9. live 端到端驗證：用 `inputs/references/ChatGPT…11_02_03.png` + 真 `product.png` 跑 swap，肉眼驗收接地/邊緣/真實性。產出存 `outputs/phase7_swap_final.png`（接地繼承 GPT 陰影、無 halo、無假產品露邊、產品內部零改動）。**待使用者最終驗收。**

## 驗收條件
- 情境（task 2）：當跑 `--scene x.png`，就走 swap 後端、log 印 `backend: swap`；若同時傳 `--shadow-dir`，印忽略警告。
- 情境（task 3）：當餵 GPT 場景 + 真產品，`align` 自動鎖定 GPT 產品（非誤鎖他物），接地錨點（左/上/底）與 PoC 手量框 `(118,555)-(790,1210)` 誤差 ≤ ~30px，貼上去視覺對齊、蓋過 GPT 假產品；四鈕能覆蓋自動結果。
  - 註：右緣不列入 ~30px（PoC 手量框偏窄，真產品毛巾本就垂得更寬——那是真實內容差、非抓錯）。實測 scale=1.02、L13/T7/B11px，視覺鎖定準。
- 情境（task 5）：當跑 swap 端到端，log **不出現** depth/bake_shadow 那幾行，且產出合成圖。
- 情境（task 6）：成品產品邊緣無去背 halo、無 GPT 假產品露邊，光包裹讓邊緣與場景自然銜接。
- 情境（task 8）：`test_align` + swap 分支測試綠；既有全套測試不回歸。
- 情境（task 9）：live 產出一張 swap 圖——接地感繼承 GPT 場景陰影、產品像素未被改（除最外圈光包裹）、整體比 `outputs/swap_poc.png` 更服（多了光包裹）。

## 決策紀錄
| # | 決策點 | 選了 | 理由 |
|---|---|---|---|
| 1 | 整體解法 | GPT 完整場景模板 + 刷回真產品 | 繼承 GPT 自然陰影/光 + 產品 100% 真實，兩全其美 |
| 2 | 架構框架 | 第三後端 `swap` 並存 | 三後端各定位（生成/自帶空背景/自帶完整場景），不砍全自動與 manual |
| 3 | 合成引擎 | 沿用 ComfyUI `composite_api.json` | 尊重使用者要「ComfyUI 刷回」；現有圖已在做貼合，複用最省 |
| 4 | 刷回機制 | B 邊緣融合 + 光包裹（內部像素不動） | 守「不改產品」真實性；明確排除 C 重打光（改全像素踩紅線） |
| 5 | 對齊策略 | 混合：auto template match + 四鈕手動 | 沿用 Phase 3「自動 ~70-80% + 人工兜底」哲學；兩顆近同一顆、超好對 |
| 6 | 對齊實作 | 加 `opencv-python` | 使用者選；`matchTemplate` 成熟少 code。**破例** Phase 3「零新套件」傳統 |
| 7 | 覆蓋/露邊 | 分段：v1 微放大力保覆蓋 + 光包裹；除抹+inpaint 兜底列後續 | 穩定優先；PoC 顯示近同輪廓罕露邊 |
| 8 | 光包裹參數 | 延後 build 時對真圖 live 校準 | 比照 Phase 5 陰影參數的校法 |
| 9 | 對齊尺度上限 | `scale_max` 1.5→2.5 + 頂到上限印警告 | 第二例（slingback 鞋）逼出：產品裁切相對場景偏小時需 scale>1.5，卡 1.5 會誤鎖（score .51 vs 正解 1.75/.72），造成細帶雙影。細長 silhouette 對齊誤差會顯著露雙影——難例仍靠四鈕或後續除抹+inpaint |

## 架構
GPT 生成 [L]（外部手動·前提步驟，不在管線內：使用者在 GPT 產完整場景、餵真產品當參考）
  → `generate.py` main [C] · backend 分支（+swap）
      → **swap 路徑**：
         `align.py` [C]（opencv `matchTemplate` [C]，真產品 vs GPT 場景 → 位置尺寸）
           → `geometry.py` [C]（defringe + force-cover）→ `Geometry`
           → `composite_api.json`（ComfyUI [C]）貼合 + B 邊緣羽化/光包裹
      → **swap 全不走**：`detect_surface` [C]/depth model、`shadow.py` bake_shadow [C]、`analyze_product_light` [C]
  config：`generation.json`（`backend:swap`+`scene_path`）[D]、`product.json`（target_box/overrides）[D]
  輸入：GPT 完整場景（`inputs/references/`）+ 真產品去背 PNG（`inputs/products/`）
