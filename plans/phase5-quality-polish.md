# Phase 5 — 品質打磨（合成擬真度）— Plan

> 把「去背圖貼生成背景」的貼圖感降下來：漸層接觸陰影（含 AO）、難例選面加固、K 自適應。
> 狀態：done（8/8 task，live 驗證）
> 最後更新：2026-07-21

## 為什麼做

V2 四 Phase 全綠、能端到端跑，但成品仍有三個可見缺口：接觸陰影是矩形色塊 blur
（略帶方邊、無漸層、接觸感不足）；難例（玻璃桌看穿→主導面變地板、多層堆疊）會硬選
錯面；`front_k=0.6` 全域常數不隨景深調。反射（畫產品倒影）逼近「不改產品」紅線且需
材質資訊，明確排除 V2。

## 改什麼／範圍

- 新增 PIL 陰影生成（橢圓徑向漸層 RGBA 貼圖，取代 ComfyUI 端矩形色塊）
- 改 `workflows/comfyui_api/composite_api.json`：陰影層從「生成色塊」→「載入上傳貼圖」
- `scripts/generate.py`：生成+上傳陰影貼圖；`geometry.py`：陰影輸出改為漸層貼圖的
  尺寸/位置/衰減參數（保四鈕行為）
- `scripts/detect_surface.py`：加固曖昧判斷 + `front_k` 自適應
- `tests/`：陰影剖面測試、難例 fixtures、K 自適應測試

## 任務

- [x] 1. 新增 `scripts/shadow.py`：純 PIL 生成橢圓徑向漸層 RGBA 陰影貼圖（中心深、往外
      平滑衰減到 0；參數：尺寸、深度/opacity、衰減曲線、羽化）。無 ComfyUI 依賴。
- [x] 2. 重構 `geometry.py` 陰影輸出：雙層 spread/core → 單張漸層貼圖的尺寸/位置/衰減
      參數；保 `--surface-line-frac`/`--offset-x`/`--offset-y`/`--scale-mult` 四鈕行為。
- [x] 3. 改 `composite_api.json` + `generate.py`：陰影在 Python 端（`bake_shadow`）用 PIL
      合成進背景（產品前），composite graph 簡化為只貼產品（80→69→9）。
      〔實作偏離：原訂 in-graph LoadImage 貼圖，改 Python bake — 避開 ComfyUI mask 反相坑、
      陰影全在可離線測試的 Python 端；視覺已驗證徑向漸層落地正確〕
- [x] 4. 陰影單元測試：驗生成貼圖 alpha 剖面中心→邊緣單調遞減、外圍為 0、輪廓橢圓非矩形。
      （`tests/test_shadow.py`，13 項全 PASS）
- [x] 5. 加固 `detect_surface.py` 曖昧判斷：次大 band ≥70% 主導 band → 判堆疊/看穿曖昧
      走 fallback（`runner_up_ratio` 訊號），不硬選錯面。既有 11 測試不回歸。
- [x] 6. 難例合成 depth（相近大小雙面＝堆疊/玻璃看穿）+ 測試：runner-up 0.87 觸發 fallback、
      reason 提 ambiguous；sliver 0.18 不誤觸；既有 20 測試（11+9）全綠不回歸。
- [x] 7. `front_k` 自適應：`adaptive_front_k(span)=clip(0.5+0.6·span,0.5,0.8)`，深景前移多、
      淺景少；`front_k=None` 走自適應（CLI/generate 預設），保留手動覆蓋。單元測試驗單調+範圍。
      three-height 實地接地校準併入 task 8 live。
- [x] 8. Live 端到端全自動跑通（fresh 接地 + 徑向漸層陰影），three-height 全自動接地、
      9 張回歸 fixtures 無誤觸、陰影參數 live 校準定案。可視化驗收報告 artifact 已產出。

## 驗收條件

- 情境（task 4）：跑陰影單元測試時，生成貼圖 alpha 從中心到邊緣單調遞減、最外圈為 0、
  bbox 內為橢圓分佈 → 測試綠。
- 情境（task 3+8）：live 全自動跑完，final 圖接觸陰影呈徑向漸層、無方邊，產品接地不飄。
- 情境（task 6）：堆疊/玻璃桌 fixtures 觸發 fallback（`used_fallback=True`）；
  `test_detect_surface`(11)+`test_manual_overrides`(9) 全綠不回歸。
- 情境（task 7）：three-height fixtures 接觸線落在合理帶內，fresh 背景全自動接地。
- 情境（全部）：可視化 artifact 呈現在對話中，使用者目視確認接觸感優於 Phase 2.5。

## 決策紀錄

| # | 決策點 | 選了 | 理由 |
|---|---|---|---|
| 1 | #4 大坑去留 | AO 併入 #1、反射排除 V2 | 反射要畫產品沒有的像素、逼近「不改產品」紅線且需材質資訊；AO 就是接觸陰影的物理正名 |
| 2 | 漸層陰影做法 | Python/PIL 生成橢圓徑向漸層貼圖 | 取代 ComfyUI 矩形色塊 blur（方邊來源）；純 PIL 可離線單元測試+可視化，契合現有架構 |
| 3 | 雙層 vs 單張漸層 | 單張徑向漸層取代雙層 | 徑向漸層＝中心深(core)往外淡(spread)的連續版，少一層合成、更好調 |
| 4 | 難例策略 | 加固誤判防線走 fallback，不硬解物理 | 玻璃桌看穿是深度模型本質限制；務實靠信心門檻+fallback+既有人工鈕兜底，斜面不擴 geometry |
| 5 | K 自適應 | front_k 隨 band span 調 | 全域 0.6 不同景深最佳前移量有差，用既有 fixtures 校準 |
| 6 | 陰影合成落點 | Python `bake_shadow` 貼進背景，非 in-graph LoadImage | 避 ComfyUI LoadImage mask 反相坑；陰影邏輯全在可離線測試+可視化的 Python 端，graph 更乾淨（僅 80→69→9） |

## 架構

```
[C] shadow.py 生成橢圓徑向漸層貼圖(新) ──上傳──▶ [T·ComfyUI] composite graph(LoadImage 陰影)
[D] detect_surface 選面 ── 加固曖昧→fallback ★#2 ── [C] front_k 自適應 ★#3
[C] geometry 陰影參數(重構:雙層→單張漸層,保四鈕) ★#1
```

規則不變：產品像素 100% 不改；斜面/看穿走 fallback+人工鈕，不擴 geometry（那是新 phase）。
執行環境務必用含 torch 的 ComfyUI venv：
`"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`。
