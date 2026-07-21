# Phase 6 — 自帶背景 / 多後端 — Plan

> 把管線從「綁 ComfyUI 生成」解成可切後端，新增 manual 後端吃任意來源（MJ/GPT/自拍）的現成背景。
> 狀態：done（7/7 task，live 驗證）
> 最後更新：2026-07-21

## 為什麼做

MJ 無官方 API、GPT image 要 key＋付費，逐一接各家 API 不划算。改在 Stage 1 加「自帶背景」
入口：手動生好背景丟進來、跳過生成、跑後半段。一勞永逸支援任意生成來源，零 API/ToS 麻煩。

## 改什麼／範圍

- `config/generation.json`：+`backend` +`manual_bg_path`
- `generate.py`：+`--bg` +`--shadow-dir`、backend 分支、實際尺寸畫框、軟警告、shadow_dir 來源
- `README.md`：雙後端用法
- `tests/`：backend／優先序／尺寸／shadow_dir

## 任務

- [x] 1. `config/generation.json` 加 `backend`（預設 comfyui、向後相容）+ `manual_bg_path`；generate 讀取。
- [x] 2. CLI `--bg` / `--shadow-dir` + backend 解析（優先序 `--bg` > config；manual 缺圖明確報錯）。
- [x] 3. Stage 1 分支：`manual` 後端跳過配光分析＋ComfyUI 生成，直接載入給定背景。
- [x] 4. 畫框改讀背景**實際尺寸**；非 9:16 印軟警告；不裁。
- [x] 5. `shadow_dir` 來源：manual 用 `--shadow-dir`（預設 right）；comfyui 模式 `--shadow-dir` 覆蓋產品分析、否則沿用。
- [x] 6. 單元測試（`tests/test_backend.py`，13 過）：backend 選擇／`--bg` 優先序／實際尺寸讀取／
      `shadow_dir` 優先序；shadow13+detect18+manual9 既有全綠不回歸。
- [x] 7. live：手動背景（1:1，1024²）端到端接地成功 + comfyui 全自動回歸正常（576×1024）
      + README 補雙後端段。

## 驗收條件

- 情境（task 2）：給 `--bg <路徑>` 走 manual 用該圖；config `backend:manual` 無圖 → 報錯訊息清楚；
  不給 `--bg` 且 config comfyui → 現狀不變。
- 情境（task 3+4）：`--bg` 一張非 9:16 手動背景 → 印軟警告、用實際尺寸、深度偵測＋陰影＋合成
  產出、產品接地。
- 情境（task 5）：`--shadow-dir left/right/none` 陰影落向對應；comfyui 模式不給時沿用產品分析。
- 情境（task 6）：新單元測試綠；`test_shadow`(13)/`test_detect_surface`(18)/`test_manual_overrides`(9) 不回歸。
- 情境（task 7）：comfyui 全自動端到端仍接地（不回歸）；手動背景 live 接地；README 有雙後端說明。

## 決策紀錄

| # | 決策點 | 選了 | 理由 |
|---|---|---|---|
| 1 | 後端模式 | 雙後端並存 comfyui\|manual | 全自動是既有能力不砍；按場景選；後半段共用 |
| 2 | 指定方式 | `--bg` > config backend/manual_bg_path | 臨時手動一句 `--bg` 最順；沿用四鈕 CLI>config 哲學 |
| 3 | 尺寸把關 | 吃實際尺寸＋軟警告＋不裁 | 不強迫 9:16、不擅改精心構圖的背景（延伸「不改」克制） |
| 4 | 配光/落向 | manual 跳配光、`--shadow-dir` 指定(預設 right) | 產品光向未必配 MJ 背景；背景光偵測屬新功能 out-of-scope；肉眼指定最可靠 |
| 5 | MJ/GPT 官方 API | 不接 | MJ 無 API；手動背景就是繞過此需求的解，零 ToS/key 麻煩 |

## 架構

```
[C] backend 分支(新) ─┬─ comfyui: [C]配光分析→prompt → [L]ComfyUI 生成背景（現狀）
                      └─ manual : 載入 --bg 圖、跳配光、實際尺寸畫框、軟警告
共用後半段 → [D]深度偵測選面 → [C]幾何(shadow_dir: manual=--shadow-dir／comfyui=產品分析可被--shadow-dir覆蓋)
           → [C]漸層陰影 bake → [T·ComfyUI]合成貼產品
```

⚠️ 已知限制：**合成貼產品仍走 ComfyUI**，故 manual 後端仍需 ComfyUI server 開著（只為合成、不生成）。
未來可把合成也搬 PIL 讓 manual 完全脫離 ComfyUI——不在本 phase scope。
規則不變：產品去背 PNG fail-fast；不擅改背景；難例靠 fallback＋四鈕。
執行環境：`"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`。
