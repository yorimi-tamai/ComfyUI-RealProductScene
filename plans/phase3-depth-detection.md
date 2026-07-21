# Phase 3 — 深度圖自動偵測水平面 — Plan

> 把接觸線 surface_y 從 config 固定值換成每張生成圖用深度圖自動求得；失敗 fallback
> 狀態：done（全 5 task 完成並驗證；自動偵測 + 前緣接地 + 人工修正介面）
> 最後更新：2026-07-21

## 為什麼做

Phase 1 的接觸線是 config 固定值——換一個桌面高低不同的背景 prompt，產品就不再接地。Phase 3 讓 `surface_y` 每張生成圖自動偵測，真正做到「換任意背景也接地」。用深度圖找下方水平面（比 classic CV 對各種場景更穩，又不需語意分割那麼重）。

## 改什麼／範圍

- 新增 `scripts/detect_surface.py`
- `scripts/generate.py` 在「背景生成後、幾何計算前」插入一次偵測呼叫
- **深度模型 = transformers `depth-anything/Depth-Anything-V2-Small-hf`**（Task 1 spike 定案，見決策 #3）
- **環境約束**：管線須跑在含 torch 的 Python（ComfyUI 的 `.venv`，已備 torch 2.10 + transformers 5.8 + MPS）；系統 python 3.9 無 torch 不可用。generate.py 執行說明已寫「跑在 ComfyUI venv」，Phase 3 把這變成硬性
- **scope 邊界（決策 #4）**：只保證**正面/微俯**的水平面自動偵測；強傾斜/俯視角、多層難分或信心低 → fallback 回 config 固定值
- 其餘管線（geometry / 合成 graph / config 微調鈕）不動

## 任務

- [x] 1. 定案深度模型取得方式 — **完成（spike）**：ComfyUI 內深度節點(`comfyui_controlnet_aux`) vs Python transformers Depth-Anything 各評估。結論選 Option B（transformers），理由見決策 #3 與下方「Task 1 Spike 結果」
- [x] 2. `scripts/detect_surface.py` — **完成**：背景圖 → 深度圖 → 找**主導（最大縱向延伸）水平面**上緣 → `SurfaceResult(frac, confidence, used_fallback, width_frac, detected_frac, reason)`
  - 多層堆疊：取「主導大面」而非「第一個」，避開較近較高的沙發座/木階
  - 掃到「起點極高又占滿畫面、無可用前緣」（強傾斜/俯視 or 曖昧多層 ramp）或信心低 → 回報低信心 + `used_fallback`
  - torch/模型缺失或推論失敗 → 不崩、回 fallback（lazy import + try/except）
  - **驗證**：9 張 fixtures live 跑 = 7 偵測全落合理接觸緣 + 2 正確 fallback（rug 曖昧、tilted 俯視）；`tests/test_detect_surface.py` 離線單元 8 項全過
- [x] 3. 接進 `generate.py` — **完成**：管線重排為「crop 早做 → 生成背景 → `resolve_surface(bg)` → geometry → composite」；`prepare_product` 拆成底層 `tight_crop`+`compute`（`geometry.prepare_product` 保留給節點用）
  - 新增 helper `resolve_surface` / `build_geometry` / `print_geometry`；CLI 加 `--fixed-surface`（跳過偵測用 config）與 `--surface-min-conf`
  - fallback 全路徑 log 清楚：低信心 / 傾斜 / **近純色輸入（用輸入影像 variance 擋，因深度模型對純色會幻覺出漸層）** / 無模型
  - **驗證**：live 端到端跑成功（自動偵測 0.641、產品接地於偵測面，非 config 0.78）；純色→fallback、tilted→fallback、`--fixed-surface`→config 皆驗證；單元測試擴為 11 項全過
- [x] 4. 驗證 — **完成（先 FAIL 後修好）**
  - ⚠️ 首次驗證 FAIL（使用者目視）：3 種桌面高度全部「產品飄在空中」。
  - 根因（受控實驗證實）：同背景合成在 frac 0.44/0.60/0.74/0.85，只有 **0.85（近端/前緣）接地**。`detect_surface` 原本回傳「主導面上緣=遠端」→ 產品擺到桌子最後面 → 飄。陰影是次因。
  - **修法（決策 #6）**：接觸線改抓「面的近端/前緣」`contact = band_top + K·span`（K=0.6）。修正後重測 low/mid/high **三張全接地**（frac 0.74→0.85、0.44→0.54、0.53→0.56）；fresh 全自動跑也接地（0.773）。
  - 證據頁：`outputs/phase3_validation/report.html`（前後對照）。
- [x] 5. 人工修正介面 — **完成（使用者要求；自動只 ~70-80% 準，需兜底）**
  - `generate.py` CLI 四鈕：`--surface-line-frac`（覆蓋自動偵測）、`--offset-x`、`--offset-y`、`--scale-mult`（覆蓋 `product.json` overrides）
  - 優先序：manual > `--fixed-surface`(config) > auto(fallback config)。offset/scale：CLI 疊在 config 之上、不丟 config-only 鍵
  - 驗證：dry-run 四鈕全反映；`tests/test_manual_overrides.py` 9 項全過；live demo（同背景 auto vs 手動 0.60/scale1.12/offx15）可見產品位移+縮放

## 驗收條件

- 情境（task 2）：給一張含明顯桌面的生成背景 → 回傳的 `surface_y` 落在桌面上緣附近（目視誤差可接受）。
- 情境（task 2，堆疊）：低茶几 / 地毯層次那種「多個水平面堆疊」的背景 → 選到的是**前下的接觸面**（茶几面 / 前方低台），不是後上的沙發座 / 木階。
- 情境（task 3，fallback）：偵測模組故意失敗（丟純色圖）或丟強傾斜俯視面 → 管線不崩、自動用固定值 fallback、有 log 提示。
- 情境（task 4）：同幾張產品換 3 種桌面高低不同的背景 prompt（正面視角）→ 產品都自動接地，不用手改 config。

## 決策紀錄

| # | 決策點 | 選了 | 理由 |
|---|---|---|---|
| 1 | 偵測方法 | 深度圖找水平面 | 比 classic CV 對各種場景穩；比語意分割(SAM)輕、不需切乾淨的桌面 mask |
| 2 | 偵測失敗處置 | fallback 回 Phase 1 固定值 | 承接「好預設 + 微調鈕」邊界；自動非萬能時不讓整條管線崩 |
| 3 | 深度模型來源 | **transformers Depth-Anything-V2-Small（Option B）** | spike 定案：ComfyUI `.venv` 已備 torch+transformers+MPS，Option B 零新套件、純 Python 契合 CLI（在兩次 API 呼叫間跑）；Option A 要另裝 `comfyui_controlnet_aux` 整包又得繞 in-graph。且兩者底層同一個 Depth-Anything V2、品質等價，決策純看安裝負擔+契合度 → B 完勝 |
| 4 | 傾斜/俯視面 scope | **限定正面/微俯，斜面走 fallback** | 單一水平 `surface_y` 描述不了斜面（Phase 1 幾何模型的假設限制）；擴充 geometry 支援斜面是新 phase、拖慢 Phase 3。符合「好預設+微調鈕」哲學 |
| 5 | 執行環境 | ComfyUI `.venv`（含 torch） | 系統 python 3.9 無 torch；標準化在 ComfyUI venv 跑，模型權重走 HF cache |
| 6 | 接觸線落點 | 面的**近端/前緣** `band_top + K·span`（K=0.6） | 取遠端上緣→產品擺桌子最後面→飄空（Task 4 首驗 FAIL）。受控實驗證明近端才接地 |
| 7 | 自動不準的兜底 | **人工修正介面**（4 個 CLI 鈕） | 自動只 ~70-80% 準；提供 surface_line_frac/offset_x/offset_y/scale_mult 手動覆蓋,不改 config 就能微調 |

## Task 1 Spike 結果（2026-07-21）

在 ComfyUI (1) 的 `.venv`（torch 2.10 / transformers 5.8 / MPS=True）實跑 `Depth-Anything-V2-Small-hf`（權重 ~100MB，一次性下載 35s；單張推論 0.14–1.65s）：

- 對 9 張生成背景（正面沙發+木底座、高吧台、地面、玻璃桌、戶外木平台、低茶几、圓桌、地毯層次、傾斜俯視）產深度圖，**品質 9/9 全優**——各水平面輪廓分明，玻璃被當不透明實心面（對「產品擺玻璃面上」反而正確）。
- 用暫時啟發式（找下方深度漸層起點）驗證選面：正面單層場景準（吧台/地面/玻璃/戶外/原圖）；**多層堆疊會誤抓較近較高的面**（低茶几→沙發、地毯層次→後方木階）；**傾斜俯視**單一 y 值本質描述不了。
- 兩個發現落成 Task 2 硬需求（選前下大面、處理堆疊）與決策 #4（斜面 scope 邊界）。
- 回歸測試集：`tests/fixtures/phase3-surface/` 9 張背景已入 repo。已知正解速記：high_kitchen≈0.53、floor≈0.49、outdoor≈0.41、glass≈0.45；low_coffee=沙發**下方**茶几面、rug_layers=前方低台（非後方木階）、tilted=判低信心走 fallback。
- spike 腳本（可複用）：scratchpad `spike_depth.py`（單張偵測+疊圖）、`gen_varied_bg.py` / `gen_tricky_bg.py`（生成測試背景）。

## 架構

```
[C] generate.py（Phase 1 管線）
        │ 背景圖產生後
        ▼
[C] detect_surface ── [L] Depth-Anything-V2-Small（transformers，跑在 .venv/MPS）→ 深度圖
        │ 選最靠前/下的大水平面上緣 → surface_y + 信心
        │ （信心低 / 強傾斜 / 失敗 → fallback [D] scene.json.surface_line_frac）
        ▼
[C] geometry（其餘同 Phase 1，surface_y 來源改為此偵測結果）
```
