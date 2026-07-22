# Handoff — ai-product-scene-generator｜V2通用管線｜Phase6自帶背景多後端｜#1 — 2026-07-21 22:53

> 檔案: `ai-product-scene-generator｜V2通用管線｜Phase6自帶背景多後端｜#1｜2026-07-21_22-53.md`
> 前一份同單元 handoff: （無、這是「Phase6自帶背景多後端」子單元第一份；同層見「…Phase5品質打磨｜#1…」「…Phase3深度接地｜#1…」「…ComfyUI節點包｜#1…」）

## The Goal
使用者想用 Midjourney / GPT image 生更好的背景。但 MJ 無官方 API、GPT image 要金鑰＋付費——與其逐一接各家 API，不如把「生成背景」那步解成可切後端，新增 manual 後端吃任意來源的現成背景。一勞永逸支援任意生成來源，零 API/ToS 麻煩。核心約束不變：產品像素不改、也不擅改使用者給的背景。

## 本次推進（This Session's Progress）
- **Phase 6 完成並 live 驗證（7/7 task）**，roadmap 現 V1 + Phase 1–6 全綠。走完整 grill(5題) → plan-it → auto mode 流程，落 `plans/phase6-byo-background.md`。
- **雙後端**：`config/generation.json` 加 `backend: comfyui|manual`（預設 comfyui、向後相容）+ `manual_bg_path`。
- **`generate.py` 三個新 helper + main 重構**：`resolve_backend`（`--bg` > config、manual 缺圖 ValueError）、`frame_from_background`（manual 吃背景實際尺寸、非 9:16 軟警告、不裁）、`resolve_shadow_dir`（`--shadow-dir` 贏、manual 預設 right、comfyui 用產品分析）。manual 後端跳過配光分析＋ComfyUI 生成，後半段（深度接地/漸層陰影/幾何/合成）兩後端共用。
- **CLI 新旗標**：`--bg <path>`、`--shadow-dir left|right|none`。
- **測試**：`tests/test_backend.py`（新，13 過）；回歸 shadow13 + detect18 + manual9 全綠。
- **live 雙路徑驗證**：manual `--bg`（1024² 1:1 場景）端到端接地＋陰影＋合成；comfyui 全自動（576×1024）行為未變。
- **README** 補「Phase 6 背景後端」段（雙後端表、優先序、限制、MJ/GPT 說明）。

## Where We Are
- **後端分支**（`generate.py` main）：先 `resolve_backend` → comfyui 走原生成（配光→prompt→ComfyUI）；manual 用 `--bg`/config 的圖當 `bg_out`、`frame_w/h` 讀該圖實際尺寸。之後 `resolve_surface`(深度)→`build_geometry`→`bake_shadow`→ComfyUI 合成，兩後端共用。
- **shadow_dir 來源**：`resolve_shadow_dir(backend,args,profile)`。manual 模式 `profile=None`（配光整個跳過），故落向只能來自 `--shadow-dir`（預設 right）。
- **尺寸**：comfyui `frame=config w/h`；manual `frame=背景實際尺寸`，`frame_from_background` 印非 9:16 警告、不裁；原背景檔不被修改（bake_shadow 另存 `_bg_with_shadow.png`）。
- **git**：branch main、HEAD `041d85c`（Phase 6）。工作區乾淨，只剩 `outputs/phase{3,5}_validation/`（gitignore 驗證產物）。本次也補 commit 了先前漏掉的 Phase 5 handoff 檔。
- **執行環境**：`"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`；兩後端都需 ComfyUI (1) 開 8188（manual 只為合成）。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| 直接接 GPT image API | 要金鑰＋付費、憑證我不能碰、9:16 對不上(只有 1024×1536)、引入雲依賴 | ❌ 未選 |
| 接 Midjourney API | MJ **無官方 API**；自動化只剩違反 ToS 的 Discord bot/第三方代理 | ❌ 拒絕(不搭規避) |
| 「自帶背景」manual 後端 | 手動生好丟進來、跳生成跑後半段；任意來源通用、零 API/ToS | ✅ kept |
| 手動唯一 vs 雙後端 | 砍掉全自動是倒退；雙後端按場景選、後半共用、成本小 | ✅ 雙後端並存 |
| 尺寸嚴格 = config 否則報錯 / 自動裁 9:16 | 太硬 / 擅改精心構圖 | ❌ 改吃實際尺寸＋軟警告＋不裁 |
| shadow_dir 從產品照推(manual) | 產品光向未必配 MJ 背景、會打架 | ❌ 改 --shadow-dir 手動指定 |
| 從背景圖自動偵測光向 | 是新分析功能、範圍太大 | 🟡 列 out-of-scope 未來 |
| config generation.json 加 backend 鍵（首次 Edit） | **Edit 落在對話異常區沒真的寫入**；code 靠 get 預設仍跑、測試也過(傳 dict)，commit 前 git status 才發現漏 | ✅ 補寫成功 |

## Key Decisions
- **雙後端並存 `comfyui|manual`**：全自動是既有能力不砍；按場景選；後半段共用。
- **`--bg` > config 優先序**：沿用四鈕 CLI>config 哲學；臨時手動一句 `--bg` 最順。
- **吃實際尺寸＋軟警告＋不裁**：不強迫 9:16、不擅改背景（「不改產品」克制延伸到「不改背景」）。
- **manual 跳配光、`--shadow-dir` 指落向**：背景光偵測屬新功能 out-of-scope；肉眼指定最可靠。
- **不接 MJ/GPT 官方 API**：MJ 無 API、GPT 要 key＋付費；手動背景就是通用解。
- **合成仍留 ComfyUI**（manual 仍需 server）：未來可搬 PIL 讓 manual 全脫離，不在本 scope。

## User Feedback / Preferences
- 提問路徑：「前面生成圖片可以換其他模型嗎」→「用 gpt 的 image2」→「用 midjourney 呢」→ 接受「自帶背景」通用解。
- 沿用 grill(Plan Mode) → plan-it 落 PLAN.md → auto mode 開發紀律；收斂後主動提醒 handoff+commit（點頭才動 git）。
- 一貫規則：不改產品本體（本次延伸出「也不擅改使用者給的背景」）。
- 安全：API 金鑰類我不代為輸入/處理。

## Git State
- Branch: `main`
- Uncommitted: 無程式碼變更（只剩 `outputs/phase3_validation/`、`outputs/phase5_validation/` 未追蹤——gitignore 驗證產物）
- Last commits:
  - `041d85c` Phase 6: bring-your-own-background / multi-backend (live-verified)
  - `c3ef7ae` Phase 5 complete: composite realism polish (live-verified)
  - `0bb97f8` Phase 3 complete: depth-based surface auto-detection + manual override

## Where We're Going (Next Steps)
1. **使用者實用驗收**：拿真的 Midjourney 背景跑 `--bg`，確認接地/陰影/落向 OK（本次用 1:1 stand-in 驗過管線）。
2. **殘留**：manual 後端仍需 ComfyUI server（只為合成）——若想讓 manual 完全離線，把合成也搬 PIL（產品 paste，同 bake_shadow 手法）＝一個小 phase。
3. **未來（別條軌）**：從背景圖自動偵測光向（免手動 `--shadow-dir`）；玻璃桌/強傾斜難例；Phase 4 發佈遺留（LICENSE 版權人換 zeczec、建 GitHub public repo 實推、Manager registry）。

## Quick Start for Next Session
「接續 ai-product-scene-generator：V2 roadmap V1 + Phase 1–6 全完成並 live 驗證（HEAD `041d85c`）。Phase 6＝自帶背景/多後端：`config/generation.json` `backend: comfyui|manual`；`generate.py` 三 helper `resolve_backend`(--bg>config)/`frame_from_background`(manual 吃實際尺寸+非9:16軟警告+不裁)/`resolve_shadow_dir`(--shadow-dir>manual預設right>comfyui產品分析)；manual 跳配光+生成、後半段共用；CLI `--bg`/`--shadow-dir`。測試 `<venv-py> tests/test_backend.py`(13) + shadow13/detect18/manual9。合成仍走 ComfyUI 故 manual 仍需 server 開 8188。執行用 `"/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/.venv/bin/python"`。殘留：manual 完全離線需把合成搬 PIL、背景光自動偵測、難例、Phase4 發佈遺留。開發紀律照 PLAN.md。」
