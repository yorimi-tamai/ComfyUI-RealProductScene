# Handoff — ai-product-scene-generator｜V2通用管線｜Phase3深度接地｜#1 — 2026-07-21 17:06

> 檔案: `ai-product-scene-generator｜V2通用管線｜Phase3深度接地｜#1｜2026-07-21_17-06.md`
> 前一份同單元 handoff: （無、這是「Phase3深度接地」子單元第一份；母單元見「…V2通用管線｜#1…」與「…ComfyUI節點包｜#1…」）

## The Goal
把 Phase 1/2 的「固定 `surface_line_frac` 接觸線」升級成**每張生成背景自動偵測接觸面**（換不同高度桌面 prompt 不必手改 config），並為自動不準的情況保留一個簡單人工修正介面。核心約束不變：產品像素 100% 不改。

## 本次推進（This Session's Progress）
- **Phase 3 完成並 live 驗證（全 5 task 打勾）**，roadmap 四個 Phase 全綠。
- **Task 1 spike**：深度模型選型定案 = transformers `Depth-Anything-V2-Small`（Option B）。關鍵發現：ComfyUI 的 `.venv` 已備 torch 2.10 + transformers 5.8 + MPS，零新套件；Option A（`comfyui_controlnet_aux`）底層同一個 Depth-Anything V2、品質等價但要另裝整包又得繞 in-graph。
- **`scripts/detect_surface.py`（新檔）**：深度圖 → 選主導（最大縱向）水平面 → 接觸線取近端/前緣 → `SurfaceResult(frac, confidence, used_fallback, width_frac, detected_frac, reason)`。傾斜/俯視、多層曖昧、低信心、近純色輸入、無模型全 fallback，永不崩。
- **`generate.py` 重排**：`crop 早做 → 生成背景 → resolve_surface(bg) → geometry → composite`。
- **人工修正介面**（使用者要求）：CLI 四鈕 `--surface-line-frac` / `--offset-x` / `--offset-y` / `--scale-mult`，優先序 manual > `--fixed-surface`(config) > auto。
- **兩支單元測試**：`tests/test_detect_surface.py`（11 過）、`tests/test_manual_overrides.py`（9 過）＋ 9 張回歸背景 `tests/fixtures/phase3-surface/`。
- **驗證資產**：`outputs/phase3_validation/`（3 高度前後對照 + 人工 demo + `report.html`）。

## Where We Are
- **接觸線公式（決策 #6）**：`contact = band_top + K·span`，K=0.6，寫死在 `detect_surface.py`（可 `--front-k` 覆蓋）。取「近端/前緣」是修掉首驗 FAIL 的關鍵。
- **選面邏輯**：`_analyze_depth` 找 per-row 深度遞近的 band、取最大縱向延伸那條為主導面；`top_frac<0.22 且 span>0.45` → 判傾斜/曖昧 fallback；輸入影像灰階 std<6 → 判近純色 fallback（深度模型對純色會幻覺漸層，故擋在輸入端）。
- **執行環境**：務必用含 torch 的 Python = `"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`。系統 py3.9 無 torch → 自動 fallback、不會自動偵測。
- **測試/驗證跑法**：`<venv-python> scripts/detect_surface.py tests/fixtures/phase3-surface/*.png`；全自動端到端 `<venv-python> scripts/generate.py --server 127.0.0.1:8188`（ComfyUI (1) 需開著）。
- **git**：branch main、HEAD `35d21d6`（Phase 4）、Phase 3 全部 uncommitted（見 Git State）。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| 深度模型 Option A(ComfyUI節點) vs B(transformers) | B 零新套件、純 Python 契合 CLI、底層同模型 | ✅ kept B |
| 選面「從上往下第一個受納面」(spike 暫時啟發式) | 多層堆疊誤抓較近較高的沙發座/木階 | ❌ 改主導面 |
| 選面「主導面 + 取上緣(遠端)」 | **首驗 FAIL：3 高度全飄空**（產品擺桌子最後面） | ❌ 改前緣 |
| 受控實驗:同背景合成 frac 0.44/0.60/0.74/0.85 | 只有 0.85(近端)接地,0.44–0.74 全飄 → 證明是擺位非陰影 | ✅ 定調修法 |
| 接觸線改 `band_top + K·span`(K=0.6) | 重測 low/mid/high 三張全接地 + fresh 自動接地 | ✅ kept |
| 純色圖 fallback 靠 `depth span` 判 | 深度模型對純色幻覺出漸層 → 沒擋住 | ❌ 改判輸入影像 std |
| 純色 fallback 改判輸入影像灰階 std<6 | 擋住、fixtures 不受影響 | ✅ kept |
| 人工修正介面用 CLI 四鈕(疊在 config overrides 上) | dry-run 四鈕全反映、9 單元測試過、live demo 可見位移縮放 | ✅ kept |

## Key Decisions
- **模型 = Depth-Anything-V2-Small / Option B**：零安裝負擔、契合 CLI；A/B 同模型品質等價。
- **scope 限正面/微俯**：單一水平 `surface_y` 描述不了強傾斜/俯視面（Phase 1 幾何假設限制）→ 斜面走 fallback，不擴 geometry（那是新 phase）。
- **接觸線取近端/前緣（K·span）**：拒「取遠端上緣」（會飄空）。
- **人工介面走 CLI 四鈕 + 優先序 manual>fixed>auto**：自動只 ~7-8 成準，保留不改 config 的快速兜底。
- **執行環境綁 ComfyUI .venv**：系統 py3.9 無 torch。

## User Feedback / Preferences
- 「我看不到結果」→ 提醒：我用 Read 看圖只有我看得到,**結果要主動做成可視產物**（artifact / 複製進專案）給使用者看。之後用 embedded-image artifact 呈現。
- 「完全不過關 都飄在空中的感覺」→ 使用者目視驗收凌駕我的判斷；我先前誤判 low/high 接地是錯的。**驗收以使用者眼睛為準**。
- 「保留一個很簡單的人工修正介面」列名四鈕 surface_line_frac/offset_x/offset_y/scale_mult。
- 「直接把這一階段完整跑完…除非重大分歧否則不要中途詢問」→ 這類明確一階段任務要**自主跑完再回報**。
- 一貫規則:不改產品本體;grill 時要口語（見 memory）。

## Git State
- Branch: `main`
- Uncommitted（Phase 3，尚未 commit）:
  - M `PLAN.md`（Phase 3 🔄→✅）
  - M `README.md`（Phase 3 CLI + 人工修正介面 + .venv 執行說明）
  - M `plans/phase3-depth-detection.md`（全 task done、決策 #6/#7、Task 4 FAIL→修好記錄）
  - M `scripts/generate.py`（管線重排 + resolve_surface/effective_overrides/build_geometry + 四鈕）
  - ?? `scripts/detect_surface.py`（新）
  - ?? `tests/`（test_detect_surface / test_manual_overrides / fixtures/phase3-surface 9 張）
  - ?? `outputs/phase3_validation/`（驗證圖 + report.html；outputs png 本被 gitignore）
- Last commits:
  - `35d21d6` Phase 4 complete: ComfyUI custom-node pack (live-verified)
  - `17f661e` handoff: V2通用管線 #1
  - `b918347` roadmap: add Phase 4

## Where We're Going (Next Steps)
1. **commit Phase 3**（本 session 緊接著做；使用者已同意）。注意 `outputs/**/*.png` 被 gitignore，report.html 與驗證 png 不會進版控——若要留證據頁需另議。
2. **殘留問題（未來）**：
   - 接觸陰影偏軟/略脫離（Phase 2.5 範疇，擺位已對故次要）。
   - 難例靠 fallback + 人工鈕兜底：玻璃桌（主導面變地板→產品落桌前地上）、多層堆疊、強傾斜。
   - K=0.6 是全域常數，不同景深最佳前移量有差（可 `--front-k` 或四鈕手調）。
3. **LICENSE 版權人**（Phase 4 遺留）：`LICENSE:3` 仍寫 "contributors"，待換成使用者實名/公司（zeczec）。使用者當前選擇「先擺著」。
4. **發佈相關（未來）**：建 GitHub repo 實際推、Manager registry（Phase 4.1，順延）。

## Quick Start for Next Session
「接續 ai-product-scene-generator：V2 Phase 1/2/2.5/3/4 全完成並 live 驗證。Phase 3 = 深度自動偵測接觸面（`scripts/detect_surface.py`，Depth-Anything-V2-Small，跑 ComfyUI `.venv`/MPS）+ 人工修正介面（`generate.py` 四鈕 `--surface-line-frac`/`--offset-x`/`--offset-y`/`--scale-mult`，優先序 manual>fixed>auto）。接觸線取近端前緣 `band_top+K·span`(K=0.6)。測試：`<venv-py> tests/test_detect_surface.py`(11)、`tests/test_manual_overrides.py`(9)；驗證圖在 `outputs/phase3_validation/`。執行務必用 `"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`。roadmap 四 Phase 全綠。殘留：接觸陰影偏軟(Phase 2.5)、難例靠 fallback+人工鈕、LICENSE 版權人待改。開發紀律照 PLAN.md。」
