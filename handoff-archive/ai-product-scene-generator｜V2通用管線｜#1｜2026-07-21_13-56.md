# Handoff — ai-product-scene-generator｜V2通用管線｜#1 — 2026-07-21 13:56

> 檔案: `ai-product-scene-generator｜V2通用管線｜#1｜2026-07-21_13-56.md`
> 前一份同單元 handoff: （無、這是該單元第一份；姊妹單元見「…接觸陰影｜#1…」）

## The Goal
把「特定產品手調」的 V1 合成，升級成**通用可客製管線**：使用者只準備一張去背 PNG + 一段場景描述，就自動去背緊裁、縮放擺位、產出與產品光線一致的合成情境圖。核心約束：產品像素 100% 不改。

## 本次推進（This Session's Progress）
- **V2 Phase 1（幾何管線）完成並 live 驗證**：Python 編排 ComfyUI（拆成 bg_generate / composite 兩個 API graph），自動 alpha 緊裁 → 等比塞目標框 → 產品底部貼接觸線 → 自適應接觸陰影。藤籃產品實跑接地成功。
- **V2 Phase 2（產品主導配光）完成並 live 驗證**：反轉思路——讀產品照的色溫/明暗/柔硬/光向，寫進背景 prompt，讓 AI 生成的場景遷就產品的光（守「不改產品」）。藤籃 → 背景明顯轉暖/亮/柔、與產品同調。同一份光向分析也驅動陰影落向。
- **V2 Phase 2.5（雙層接觸核陰影）完成並 live 驗證**：在柔散陰影下疊一層緊實深色低模糊的接觸核，接地感明顯優於單層均勻霧。
- **git 納管**：專案 `git init` + 6 個 commit，全程可回溯。
- **roadmap 兩次調整**：依 Phase 1 驗收回饋，把「深度偵測擺位」順延為 Phase 3、插入 Phase 2；依使用者「要發佈給別人」新增 Phase 4（打包成 ComfyUI 自訂節點包）。

## Where We Are
- **架構**：Python 當大腦（`scripts/`）、ComfyUI 當生成/合成引擎（經 HTTP API）。入口 `python scripts/generate.py --server 127.0.0.1:8188`。
- **scripts/**：`comfy_client.py`(stdlib urllib：upload/prompt/history/view)、`geometry.py`(緊裁/塞框/擺位/雙層陰影)、`analyze_product_light.py`(色溫/明暗/柔硬/光向→lighting子句+shadow_dir)、`prompt_builder.py`(scene.json 填模板，lighting=auto 時套產品分析)、`generate.py`(主編排)。
- **workflows/comfyui_api/**：`bg_generate_api.json`(背景)、`composite_api.json`(21 節點：LoadImage 背景/產品 + 柔散陰影 79 + 接觸核 81–87 + 產品 69 + Save)。合成序：背景→柔散→接觸核→產品。
- **config**：`product.json`(target_box width_frac 0.6/height_frac 0.42 + overrides scale_mult/offset_x/offset_y/shadow_opacity 0.3/shadow_blur 8/shadow_offset_y)；`scene.json`(scene/style/lighting="auto"/camera/reserved_space/surface_line_frac 0.78)；`generation.json`(576×1024, seed -1, steps 8, cfg 1, res_multistep/simple —— 已改成 z-image-turbo 實際值)。
- **執行環境**：腳本需 Pillow。本機預設 python3 無 PIL；驗證時用 scratchpad venv 當純 HTTP 客戶端打 ComfyUI（不需 ComfyUI 的 venv）。生產可用 ComfyUI venv 跑。
- **測試產品**：`inputs/products/product.png`（藤編提籃，960×960，來自 Downloads/removebackground1784609357563.png）。
- **git**：branch main、HEAD `b918347`、working tree 乾淨。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| 手動逐條 Edit 改 workflow JSON | 檔案在操作中消失兩次、易錯 | ❌ abandoned |
| 改用 Python 程式化 mutate JSON + 自動驗證(無斷點) | 穩定可靠 | ✅ kept |
| 產品緊裁後再上傳(而非傳整張含留白) | 讓「產品底部=接觸線」變確定，擺位/陰影可精算 | ✅ kept（關鍵設計）|
| Phase 1 固定 surface_line_frac | 幾何正確，但隨機 seed 下桌面位置變、產品浮空 | 🟡 partial（Phase 3 要自動化）|
| 用產品分析驅動背景 prompt（產品主導配光） | 背景色溫/明暗明顯貼合產品，解光線不一致 | ✅ kept |
| 光向自動偵測 | best-effort、noisy（藤籃判為均勻/暖，合理）；已標明可覆蓋 | ✅ kept（附但書）|
| 單層均勻陰影 | 方塊柔霧、無漸層、接觸感不足 | ❌ 改進 |
| 雙層（柔散 + 緊實接觸核） | 同 seed A/B 對比，接地明顯更實 | ✅ kept |
| generation.json 用 V1 通用 sampler(euler/cfg6.5/30步) | 與 z-image-turbo 不合、會壞背景 | ❌ 改為 turbo 實際值 |

## Key Decisions
- **產品主導配光**：選「背景遷就產品的光」，拒「調產品配背景」。理由：守「不改產品」規則，背景本就是可變的生成物。
- **雙層陰影**：柔散 + 接觸核，取代單層。理由：接觸核提供「貼合處深色」的接地線索，單層做不到。
- **緊裁後上傳**：產品底部＝接觸線，讓擺位與陰影確定化。
- **generation.json 修正為 turbo 值**：單一來源、不弄壞 proven 背景。
- **Phase 排序調整**：配光(Phase 2)優先於擺位偵測(Phase 3)，因當前痛點是光線一致。
- **Phase 4 打包發佈 = 翻轉「不用自訂節點」原則**：為讓別人裝來用而刻意為之。

## User Feedback / Preferences
- 「以我讀入的產品照為主，去生成適合的背景」——產品是錨、背景遷就它（催生 Phase 2）。
- 「接地很差、光線不一致」——對品質敏感，願意為此加工。
- 「這工作流之後可以打包在 ComfyUI 使用嗎」→「發佈給別人用」——最終要做成可發佈的自訂節點包（Phase 4）。
- 一貫規則：不改產品本體/Logo/文字/結構、儘量內建節點（Phase 4 例外）、穩定優先。

## Git State
- Branch: `main`
- Uncommitted: 無（working tree 乾淨）
- Last commits:
  - `b918347` roadmap: add Phase 4 (package as ComfyUI custom-node pack)
  - `f79248b` Phase 2.5: two-layer contact-core shadow
  - `27e30ce` Phase 2 complete: product-led lighting
  - `7181933` Phase 1 complete: live end-to-end verified
  - `330d3dc` Phase 1: config schema + Python pipeline (offline-verified)
  - `49d1cb1` Initial commit: V1 spec + composite workflow v2 + V2 plans

## Where We're Going (Next Steps)
1. **Phase 4（使用者當前想要，需先 grill/plan-it）**：打包成 ComfyUI 自訂節點包發佈。要 grill 的岔路：節點切幾顆/邊界、PIL→tensor 改寫範圍、範例 .json 綁不綁特定模型、保不保留 Python CLI、Phase 3 深度偵測要不要進第一版、LICENSE 選型、ComfyUI Manager 登錄。**此 Phase 翻轉「不用自訂節點」原則**。
2. **Phase 3（順延）**：深度圖自動偵測水平面，解「surface_line_frac 要手調」。
3. **收尾微調（可選）**：柔散陰影邊緣略方；整體仍是「去背圖貼生成背景」本質——觀感問題。
4. 提醒：`surface_line_frac` 目前 0.78 是為某張背景手調的；隨機 seed 換背景需重調（Phase 3 前的已知限制）。

## Quick Start for Next Session
「接續 ai-product-scene-generator V2：Phase 1(幾何管線)+ Phase 2(產品主導配光)+ Phase 2.5(雙層接觸核陰影)都完成並 live 驗證，git HEAD b918347。管線 = Python(scripts/) 驅動 ComfyUI(兩個 API graph)，入口 `python scripts/generate.py --server 127.0.0.1:8188`（需 Pillow 環境）。今天要做 Phase 4：把它打包成 ComfyUI 自訂節點包發佈給別人用——請先進 Plan Mode grill 一輪(節點切法/tensor 改寫/範例綁模型/授權/Phase 3 要不要一起發)，再 plan-it 落 Phase 4 的 Plan。」
