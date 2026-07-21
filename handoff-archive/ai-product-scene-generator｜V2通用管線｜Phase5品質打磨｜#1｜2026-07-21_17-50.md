# Handoff — ai-product-scene-generator｜V2通用管線｜Phase5品質打磨｜#1 — 2026-07-21 17:50

> 檔案: `ai-product-scene-generator｜V2通用管線｜Phase5品質打磨｜#1｜2026-07-21_17-50.md`
> 前一份同單元 handoff: （無、這是「Phase5品質打磨」子單元第一份；母單元見「…V2通用管線｜#1…」與同層「…Phase3深度接地｜#1…」「…ComfyUI節點包｜#1…」）

## The Goal
把 V2 成品「去背圖貼生成背景」的貼圖感降下來——這一輪吃三項：漸層接觸陰影（含 AO）、難例選面加固、接觸線 K 自適應。核心約束不變：產品像素 100% 不改。反射（畫產品沒有的倒影像素）明確排除 V2。

## 本次推進（This Session's Progress）
- **Phase 5 完成並 live 驗證（8/8 task 打勾）**，roadmap 現 V1 + Phase 1–5 全綠。走完整 grill → plan-it → auto mode 流程，落 `plans/phase5-quality-polish.md`。
- **`scripts/shadow.py`（新檔）**：純 PIL 生成橢圓徑向漸層 RGBA 陰影貼圖（中心深、往外單調衰減到 0、外圈為 0、含 core plateau）。取代舊的 ComfyUI 矩形色塊+blur（方邊來源）。
- **陰影改由 Python 端 bake**：`generate.py` 新增 `bake_shadow()`，用 PIL 把陰影貼圖合成進背景（產品前）；`composite_api.json` 從 22 節點砍到 6（80→69→9，只貼產品）。避開 ComfyUI LoadImage mask 反相坑、陰影邏輯全在可離線測試的 Python 端。
- **`geometry.py` 重構**：陰影輸出從雙層 spread/core → 單張漸層貼圖的尺寸/位置/衰減參數；四鈕行為保留。
- **`detect_surface.py` 加固 + 自適應**：`runner_up_ratio`（次大面≥70%主導面→曖昧走 fallback）；`adaptive_front_k(span)=clip(0.5+0.6·span,0.5,0.8)` 取代寫死 0.6，`front_k=None` 走自適應。
- **陰影參數 live 校準**（兩輪 sweep）：定案 `op0.58 / core0.28 / falloff1.4 / flatten0.24 / width_mult1.35`，寫進 `geometry.py` 預設，清掉 config 舊 `shadow_opacity/shadow_blur`。
- **測試**：`tests/test_shadow.py`（新，13 過）、`tests/test_detect_surface.py`（+4 新項共 18 過）、`test_manual_overrides.py`（9 過未動）。
- **驗收 artifact**：https://claude.ai/code/artifact/18a3652c-5aa7-45dc-bf2c-102942974cbf（最終圖＋陰影 sweep＋三高度接地＋測試表）。`outputs/phase5_validation/report.html` 本地同源。

## Where We Are
- **陰影管線**：`shadow.radial_shadow(w,h,opacity,falloff,core_frac,feather)` → `generate.bake_shadow(bg,g,out)` 合成進背景 → 上傳 → composite graph 只貼產品。合成序：背景→陰影→產品。
- **選面**：`detect_surface` 除既有 tilt/低信心/近純色 fallback，新增 `runner_up_ratio≥0.70` 曖昧 fallback。`front_k` 預設 None＝自適應（CLI `--front-k` 與 generate 都不傳→自適應）；手動仍可覆蓋。
- **陰影幾何**（`geometry.compute`）：`shadow_w=product_w·1.35`、`shadow_h=shadow_w·0.24`、中心對齊接觸線並隨光向水平微移 6%。四鈕（`--surface-line-frac/--offset-x/--offset-y/--scale-mult`）優先序 manual>fixed>auto 未動。
- **live 驗證數據**：fresh 全自動接地（k=0.62 auto, conf0.85）；three-height 三桌高全自動接地（k 0.53–0.61）；9 張回歸 fixtures = 7 auto（k 0.56–0.80，span 大→k 大印證設計）/ 2 tilt-fallback，無一因新判斷誤觸。
- **執行環境**：務必用含 torch/PIL 的 `"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`。全自動端到端需 ComfyUI (1) 開在 127.0.0.1:8188。
- **git**：branch main、HEAD `c3ef7ae`（Phase 5，已 commit）。工作區乾淨，只剩 `outputs/phase{3,5}_validation/`（gitignore 的驗證產物，未追蹤）。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| #4 反射+AO 當一整項 | 拆開：AO＝接觸陰影物理正名併入 #1；反射要畫產品沒有的像素、逼近紅線、需材質資訊 | ✅ AO 併 #1、反射排除 |
| 陰影 in-graph LoadImage 貼圖（原 plan） | ComfyUI LoadImage mask 有 1-alpha 反相坑、無 UI 難反覆試 | ❌ 改 Python bake |
| 陰影 Python `bake_shadow` 合成進背景 | PIL 對漸層 alpha 完美、可離線測+可視化、graph 從 22→6 節點 | ✅ kept |
| 陰影歸一化半軸用 `dim/2` | 最外圈像素 r≈0.9975<1 殘留微量 alpha，邊緣測試 FAIL | ❌ |
| 半軸改 `(dim-1)/2` | 最外圈落在 r=1、alpha 嚴格 0，13 測試全過 | ✅ kept |
| 陰影濃度 sweep op0.3/0.5/0.62/0.72 | op0.3(舊)浮空、op0.72 橢圓斑塊外露偏假；濃度落 C(~0.58) | ✅ 定濃度 |
| 陰影扁平度 sweep flat0.42→0.18 | flat0.42 拖太長、flat0.24 緊貼籃底往前短促淡出無斑塊 | ✅ 定 flatten0.24 |
| 選面曖昧靠 `runner_up_ratio≥0.70` | 相近雙面 0.87→fallback、小 sliver 0.18→不誤觸；9 真圖無回歸 | ✅ kept |
| front_k 自適應 `clip(0.5+0.6·span,0.5,0.8)` | live 印證 span0.06→k0.53、span0.58→k0.80，三高度全接地 | ✅ kept |

## Key Decisions
- **AO 併入 #1、反射排除 V2**：反射要畫產品沒有的像素、逼近「不改產品」紅線且需材質資訊；AO 就是接觸陰影的物理正名。
- **陰影 Python bake 而非 in-graph**：避 ComfyUI mask 反相坑；陰影全在可離線測試+可視化的 Python 端，graph 更乾淨。
- **單張徑向漸層取代雙層 spread/core**：徑向漸層＝中心深往外淡的連續版，少一層、好調（core_frac 還原濃接觸核）。
- **難例加固而非硬解物理**：玻璃桌看穿是深度模型本質限制，靠信心門檻+fallback+人工鈕兜底，斜面不擴 geometry（屬新 phase）。
- **陰影參數落 geometry 預設、清 config 舊值**：config 只留產品四鈕中性值，陰影用校準預設。

## User Feedback / Preferences
- 「直接把這一階段完整跑完、測試、修正並驗證，除非重大分歧否則不要中途詢問，最後只整理完成結果/測試/仍存在問題給我」→ 自主跑完 8 task 才回報。
- 沿用 grill(Plan Mode) → plan-it 落 PLAN.md → auto mode 開發紀律；grill 時要口語。
- 結果要主動做成可視產物（artifact）給使用者看（延續前 session 偏好）。
- 一貫規則：不改產品本體。

## Git State
- Branch: `main`
- Uncommitted: 無程式碼變更（只剩 `outputs/phase3_validation/`、`outputs/phase5_validation/` 未追蹤——gitignore 的驗證產物，含 report.html 亦刻意不進版控，與 phase3 一致）
- Last commits:
  - `c3ef7ae` Phase 5 complete: composite realism polish (live-verified)
  - `0bb97f8` Phase 3 complete: depth-based surface auto-detection + manual override
  - `35d21d6` Phase 4 complete: ComfyUI custom-node pack (live-verified)

## Where We're Going (Next Steps)
1. **使用者目視驗收**：看 artifact / `outputs/phase5_validation/report.html`，確認接觸感 OK。不滿意可調 `geometry.py` 陰影預設或用四鈕。
2. **殘留（未來）**：玻璃桌看穿/多層堆疊/強傾斜靠 fallback+人工鈕兜底；K clip 到 [0.5,0.8]，極端景深 `--front-k` 手調。
3. **驗證證據頁存放**：`report.html` 目前不進版控（gitignore），若要留檔另議（可移出 outputs/ 或加白名單）。
4. **Phase 4 發佈遺留**（別條軌）：`LICENSE:3` 版權人仍 "contributors" 待換 zeczec；建 GitHub public repo 實推；Manager registry（Phase 4.1 順延）。

## Quick Start for Next Session
「接續 ai-product-scene-generator：V2 roadmap V1 + Phase 1–5 全完成並 live 驗證（HEAD `c3ef7ae`）。Phase 5＝合成擬真度打磨：#1 漸層接觸陰影（`scripts/shadow.py` 生成橢圓徑向漸層貼圖，`generate.py` 的 `bake_shadow` 用 PIL 合成進背景，composite graph 簡化成只貼產品）＋ #2 選面曖昧 fallback（`detect_surface` `runner_up_ratio≥0.70`）＋ #3 `adaptive_front_k(span)=clip(0.5+0.6·span,0.5,0.8)`。陰影校準值 op0.58/core0.28/falloff1.4/flatten0.24 在 `geometry.py` 預設。測試：`<venv-py> tests/test_shadow.py`(13)/`test_detect_surface.py`(18)/`test_manual_overrides.py`(9)。執行務必用 `"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`、ComfyUI (1) 開 8188。殘留：玻璃桌/強傾斜靠人工鈕、反射不做、LICENSE 版權人待改、發佈未推。開發紀律照 PLAN.md。」
