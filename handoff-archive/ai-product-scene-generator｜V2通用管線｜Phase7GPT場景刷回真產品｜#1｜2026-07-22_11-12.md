# Handoff — ai-product-scene-generator｜V2通用管線｜Phase7GPT場景刷回真產品｜#1 — 2026-07-22 11:12

> 檔案: `ai-product-scene-generator｜V2通用管線｜Phase7GPT場景刷回真產品｜#1｜2026-07-22_11-12.md`
> 前一份同單元 handoff: （無、這是「Phase7GPT場景刷回真產品」子單元第一份；同層見「…Phase6自帶背景多後端｜#1…」「…Phase5品質打磨｜#1…」）

## The Goal
使用者驗收現有管線的橢圓烘陰影「不自然」；GPT 整張生成的場景陰影/光/接地極自然但產品是 AI 重畫的（違反「不改產品」）。解法：GPT 生**完整場景**（含產品）當模板 → 對齊後把場景裡 AI 假產品的位置「刷回」真產品 → 繼承 GPT 自然陰影/光、同時產品像素 100% 真實。

## 本次推進（This Session's Progress）
- **Phase 7 完成並 2 例 live 驗證（9/9 task）**，roadmap 現 V1 + Phase 1–7 全綠。走完整 grill(6 決策) → plan-it → auto mode，落 `plans/phase7-swap-mode.md`。
- **新第三後端 `backend: swap`**（並存 comfyui/manual）：`--scene <path>` implies swap；`generation.json` 加 `scene_path`。
- **新 `scripts/align.py`**：opencv 多尺度 template match（`TM_CCOEFF_NORMED` + 透明區均值填），自動抓 GPT 產品位置/尺寸 → `build_swap_geometry`（四鈕 override + force-cover 3%）→ 現有 `Geometry`。
- **`geometry.defringe`**（alpha 內縮殺去背 halo）+ **`generate.bake_light_wrap`**（PIL 邊緣光包裹，B 案：產品內部 byte-for-byte 不動，只碰最外圈 rim band；ComfyUI 仍負責合成貼合）。
- **`generate.py` main swap 分支**：跳過 depth/`bake_shadow`/配光（都來自 GPT 場景），合成步驟抽成三後端共用；dry-run 也支援 swap。
- **測試**：`tests/test_align.py`（16，新）+ `test_backend` 加 4 swap resolve 案；shadow13/detect18/manual9 全綠、零回歸。
- **2 例 live**：籃子（`outputs/phase7_swap_final.png`，scale 1.02）+ slingback 鞋（`outputs/final/final.png`，scale 1.75）。
- README 補 swap 段（三後端表 + GPT 前提）；`requirements.txt` 加 `opencv-python`。

## Where We Are
- **swap 流程**（`generate.py` main）：`resolve_backend`(--scene>--bg>config) → swap 走 `frame_from_background`(場景實際尺寸) → `tight_crop`+`defringe(3px)` → `swap_geometry`(align→locate_product→build_swap_geometry) → `bake_light_wrap`(最終尺寸，覆蓋上傳的 cropped) → ComfyUI `composite_api.json` 貼合。
- **對齊參數**（`align.py`）：`locate_product` 兩段掃 scale [0.3, 2.5]（粗 0.05 → 細 0.01），`TM_CCOEFF_NORMED`；頂到 scale_max 會印警告。
- **B 光包裹參數**（`generate.py` 常數，live 校準）：`SWAP_DEFRINGE_PX=3`、`SWAP_LW_STRENGTH=0.28`、`SWAP_LW_RIM_PX=7`、`SWAP_LW_FEATHER_PX=0.0`（羽化開了會把半透明邊透出強背景 → 亮邊 halo，故關）。
- **執行**：`"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python" scripts/generate.py --scene <full_scene> [--product <png>] [--scale-mult/--offset-x/y]`；合成仍需 ComfyUI server 開 8188。
- **git**：branch main、HEAD 仍在 `041d85c`(Phase 6)。**Phase 7 全部 uncommitted**（見 Git State）——尚未 commit。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| 對齊用 masked `TM_CCORR_NORMED` | 尺度偏差、偏愛小尺度+亮區 → 誤鎖右下草帽區(scale 0.3, 假高分 0.97) | ❌ abandoned |
| 改 `TM_CCOEFF_NORMED` + 透明區均值填(非 mask) | 減均值對亮度/尺度穩健、透明區均值填貢獻近零 → 籃子鎖定準(L13/T7/B11px) | ✅ kept |
| 光包裹在 composite 圖插 ComfyUI 節點 | 撞 CLAUDE.md 規則 6（不得臆造 workflow JSON）+ 香草無現成節點 | ❌ abandoned |
| 光包裹改 PIL `bake_light_wrap`(使用者選) | 比照 bake_shadow；ComfyUI 仍合成；產品內部零改動 | ✅ kept |
| 亮邊 halo：以為是光包裹過強 → 調 strength | strength=0 仍有亮邊；根因是羽化把半透明邊透出強背景 | 🟡 診斷 |
| 關羽化(feather 0) + defringe 加到 3px | 亮邊消失、邊緣乾淨 | ✅ kept |
| 覆蓋露邊：force-cover 微放大 3% + 光包裹 | 實心物(籃子)夠；細長物(鞋帶)放大只位移、蓋不住 → 需準對齊 | 🟡 partial |
| 鞋例雙帶影：scale_max 卡 1.5 | 真匹配在 1.75(score .72)、卡 1.5 誤鎖(.51) → 細帶雙影 | ❌ 是 bug |
| scale_max 1.5→2.5 + 頂上限警告 | 鞋 scale 抓回 1.75、雙影消失、buckle 保留 | ✅ kept |
| 合成搬純 PIL（我原推薦） | 使用者要 ComfyUI 刷回 → 沿用現有 composite 圖，複用更省 | ❌ 未採（尊重使用者） |

## Key Decisions
- **swap 當第三後端並存**：三後端各定位（生成/自帶空背景/自帶完整場景），不砍全自動與 manual。
- **合成走 ComfyUI（沿用 `composite_api.json`）**：使用者明確要「ComfyUI 刷回」；現有圖已在做貼合。
- **刷回 = B 邊緣融合+光包裹**：產品內部像素不動；明確拒 C 重打光（改全像素踩紅線）。
- **對齊 = 混合**：opencv 自動 + 四鈕手動兜底（沿用 Phase 3 哲學）。
- **加 `opencv-python`**：使用者選，`matchTemplate` 成熟少 code；**破例** Phase 3「零新套件」傳統。
- **覆蓋分段**：v1 defringe+微放大力保覆蓋；除抹+inpaint 難例兜底列後續（尚未做）。
- **光包裹/對齊參數 live 校準**：比照 Phase 5 陰影校法（值進 `generate.py`/`align.py` 常數）。

## User Feedback / Preferences
- 路徑：嫌橢圓陰影「不自然」→ 自己提「丟 gpt 生的產品加背景圖、把產品除抹回去」（本 phase 的種子）→「由 gpt 產合成圖、用 ComfyUI 刷回原本產品保持真實性」。
- 一貫規則：不改產品本體（本 phase 延伸為「只碰最外圈邊緣、內部 byte-for-byte 不動」）。
- 沿用 grill(Plan Mode) → plan-it 落 PLAN.md → auto mode 開發紀律；收斂後主動提醒 handoff（點頭才動）。
- 安全：API 金鑰類不代輸入（故不接 MJ/GPT API、手動生場景）。
- 驗收「目前看還可以」，主動再丟第二例（鞋）壓測 → 逼出 scale bug。

## Git State
- Branch: `main`
- Uncommitted（**Phase 7 尚未 commit**）：
  - Modified: `PLAN.md`、`README.md`、`config/generation.json`、`requirements.txt`、`scripts/generate.py`、`scripts/geometry.py`、`tests/test_backend.py`
  - Untracked: `scripts/align.py`、`tests/test_align.py`、`plans/phase7-swap-mode.md`、Phase 6 handoff、`outputs/phase{3,5}_validation/`（gitignore 驗證產物）
- Last commits:
  - `041d85c` Phase 6: bring-your-own-background / multi-backend (live-verified)
  - `c3ef7ae` Phase 5 complete: composite realism polish (live-verified)
  - `0bb97f8` Phase 3 complete: depth-based surface auto-detection + manual override

## Where We're Going (Next Steps)
1. **commit Phase 7**（使用者尚未指示 commit；建議訊息 `Phase 7: GPT-scene swap backend — align + light-wrap real product (live-verified)`，順帶補 commit 漏掉的 Phase 6 handoff）。
2. **殘留難例**：細長 silhouette（帶/細跟）對齊誤差易露雙影 → 可做當初 grill 列的**除抹 + inpaint**（Q3 兜底，用真產品輪廓略脹當遮罩擦 GPT 假產品、inpaint 補景再貼）；姿態差太多（正面 vs 側面）自動抓不準。
3. **別條軌（沿 Phase 6 遺留）**：manual 後端完全離線（合成搬 PIL）；背景光自動偵測；Phase 4 發佈遺留（LICENSE 版權人換 zeczec、GitHub public repo、Manager registry）。
4. 使用者可能再丟更多例壓測 swap（不同產品/場景）。

## Quick Start for Next Session
「接續 ai-product-scene-generator：V2 roadmap V1 + Phase 1–7 全完成 live 驗證。Phase 7＝GPT 場景刷回真產品（`backend: swap`）：`--scene <full_scene>` → `align.py`（opencv `TM_CCOEFF_NORMED` 多尺度 [0.3,2.5] template match 抓 GPT 產品）→ `build_swap_geometry`（四鈕+force-cover 3%）→ `geometry.defringe(3px)` → `bake_light_wrap`（PIL 邊緣光包裹、內部不動）→ ComfyUI `composite_api.json` 合成；swap 跳過 depth/bake_shadow/配光。光包裹常數在 `generate.py`（DEFRINGE 3/STRENGTH .28/RIM 7/FEATHER 0）。測試 `<venv-py> tests/test_align.py`(16)+test_backend(18)+shadow13/detect18/manual9。2 例驗過（籃子/鞋）。**Phase 7 全部 uncommitted，HEAD 仍 041d85c**——接手先確認要不要 commit。執行用 `"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`，合成需 server 8188。殘留：細長物易露雙影（可上除抹+inpaint）、姿態差太多抓不準。開發紀律照 PLAN.md。」
