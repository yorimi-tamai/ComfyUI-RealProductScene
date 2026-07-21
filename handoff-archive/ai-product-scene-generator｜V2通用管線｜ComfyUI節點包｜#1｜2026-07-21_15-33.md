# Handoff — ai-product-scene-generator｜V2通用管線｜ComfyUI節點包｜#1 — 2026-07-21 15:33

> 檔案: `ai-product-scene-generator｜V2通用管線｜ComfyUI節點包｜#1｜2026-07-21_15-33.md`
> 前一份同單元 handoff: （無、這是「ComfyUI節點包」子單元第一份；母單元見「…V2通用管線｜#1…」）

## The Goal
把 V2 的 Python 管線（幾何/配光/組prompt/合成）打包成 ComfyUI 自訂節點包，公開到 GitHub 讓其他 ComfyUI 使用者 git-clone 裝來用——即 roadmap 的 Phase 4。核心約束不變：產品像素 100% 不改。

## 本次推進（This Session's Progress）
- **Phase 4 完成並 live 驗證**（7/7 task 全打勾）。做出可安裝的 ComfyUI 節點包：
  - 兩顆節點 `AnalyzeProductLighting`（生成前：產品→prompt+shadow_dir）、`CompositeProductScene`（生成後：背景+產品→最終合成，內部整包裁切/幾何/雙層陰影/合成）。
  - `comfyui_nodes/tensor_io.py`（tensor↔PIL 邊界轉換 + 無透明度守則）、repo-root `__init__.py`（ComfyUI 發現入口）。
  - 範例 workflow（API 格式，綁 z-image-turbo）、README（安裝/模型/換模型/節點 I/O）、MIT LICENSE、requirements.txt。
- **live 端到端驗證通過**：節點在 ComfyUI (1) 實例載入（category `product-scene`），範例跑成功，輸出 576×1024，藤籃接地 + 背景暖調與產品同調（`outputs/final/product_scene_v2_live.png`）。
- **grill → plan-it 全流程**：Phase 4 先 grill 7 條岔路達共識，落成 `plans/phase4-comfyui-node-pack.md`。

## Where We Are
- **節點包結構**：repo-root `__init__.py` → re-export `comfyui_nodes/__init__.py`（防禦式 `_register` 逐顆掛）→ `node_analyze.py` / `node_composite.py` / `tensor_io.py`。三者都 import `scripts/` 的共用大腦（geometry / analyze_product_light / prompt_builder），零邏輯重複。
- **關鍵設計**：tensor 只在節點進出口轉、內部 PIL 原封；產品走 `IMAGE`+`MASK` 進來拼回 RGBA（ComfyUI MASK = 1-alpha）；無透明度丟 `NoAlphaError`。Node B 的雙層陰影是把 `composite_api.json`（graph）用 PIL 重建（solid canvas / GaussianBlur / alpha paste），CLI 仍走 graph。
- **安裝現況（live 機器）**：節點包 symlink 進 `/Users/yoriwork/ComfyUI-Installs/ComfyUI (1)/ComfyUI/custom_nodes/ai-product-scene-generator`；`product.png` 在 `~/ComfyUI-Shared/input`。ComfyUI Desktop 有兩個實例——**節點裝在「ComfyUI (1)」**（無錯誤那個），另一個「ComfyUI」有既有錯誤標記、與本工作無關。
- **驗證資產**：離線單元測試在 scratchpad（tensor 守則 / Node A / Node B / 範例結構 4 支全過，用 numpy+Pillow venv，無 torch）。
- **git**：branch main、HEAD `17f661e`、Phase 4 檔全 uncommitted（見 Git State）。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| 節點切法：合成那顆「整包」vs 拆成原生子圖(~18 INT 扇出) | 整包讓 tested PIL 邏輯原封複用、畫布乾淨、改寫少 | ✅ kept |
| Node A 順便吸收 prompt_builder（吐完整 prompt 一條線） | prompt_builder 邏輯有家、使用者只接一條線進 CLIP | ✅ kept |
| Node B `shadow_dir` 用 combo | combo 在 ComfyUI 不能接線、接不到 Node A 輸出 | ❌ 改 STRING |
| Node B `shadow_dir` 改 STRING（未知值 fallback right） | 可從 Node A 接線、也可當 widget | ✅ kept（整合修正）|
| 節點只放 `comfyui_nodes/`（無 repo-root __init__） | ComfyUI 從 clone 資料夾頂層找 __init__，找不到節點 | ❌ 缺 entry |
| 補 repo-root `__init__.py` re-export | 模擬 ComfyUI load_custom_node（含 hyphen 名）驗證可發現 | ✅ kept（整合修正）|
| 範例用 API 格式（非 UI LiteGraph） | 守 CLAUDE.md #6 不臆造脆弱 UI JSON；重用 proven bg graph | ✅ kept |
| tensor_io 的 torch 用 lazy import | 讓守則邏輯能在無 torch 的 venv 單元測試 | ✅ kept |
| Manager HTTP reboot 端點觸發重啟 | `/api/manager/reboot` 等全 404（Desktop 擋/路由不同） | ❌ 改由使用者 GUI 重啟 |
| kill server PID 賭 Electron 重生 | 判定風險太高（掛了救不回）故不做 | ❌ 未採（安全考量）|

## Key Decisions
- **發佈野心 = C**：公開 GitHub、git-clone 可裝，Manager registry 順延。理由：可裝可跑可讀已是大跳，registry 是獨立審核+維護。
- **合成整包 + 邊界轉 tensor**：拒「拆成原生子圖」與「重寫成 torch」。理由：原封複用測過的 PIL，最健壯、改寫最少。
- **範例綁 z-image-turbo + README 換模型指南**：拒「湊通吃參數」（做不到）。節點本身模型無關（免費）。
- **Phase 3 深度偵測順延**：不進 v1。理由：深度模型來源未定案是研究非打包工作，混做兩邊拖。surface line 當節點鈕 + 好預設。
- **LICENSE = MIT**：ComfyUI 圈預設、相依只 Pillow 無衝突。
- **不 kill live server**：使用者授權「乾淨重啟」，但無安全程式化重啟手段時不賭 process kill（難復原）。

## User Feedback / Preferences
- grill 時要求「口語一點」——白話短句，別堆正式書面語（已存 memory `feedback_grill_tone_colloquial`）。
- 「我全包（含重啟）」——授權我安裝+重啟+驗證；但實際重啟因 Desktop 擋 reboot API 而交回使用者按 GUI（ComfyUI (1) 實例）。
- 一貫規則：不改產品本體/Logo/文字/結構、儘量內建節點（Phase 4 為發佈刻意例外）、穩定優先。

## Git State
- Branch: `main`
- Uncommitted（Phase 4，尚未 commit）:
  - M `PLAN.md`（Phase 4 → ✅ done）
  - M `README.md`（新增節點包章節）
  - ?? `LICENSE`（MIT；版權人暫寫 "contributors"，待使用者改名）
  - ?? `__init__.py`、`comfyui_nodes/`、`requirements.txt`
  - ?? `plans/phase4-comfyui-node-pack.md`
  - ?? `workflows/comfyui_api/product_scene_example_api.json`
- Last commits:
  - `17f661e` handoff: V2通用管線 #1 (Phase 1/2/2.5 done, next = Phase 4 packaging)
  - `b918347` roadmap: add Phase 4
  - `f79248b` Phase 2.5: two-layer contact-core shadow
  - `27e30ce` Phase 2 complete: product-led lighting
  - `7181933` Phase 1 complete: live end-to-end verified

## Where We're Going (Next Steps)
1. **commit Phase 4**（本 session 緊接著做）。
2. **LICENSE 版權人**：把 "ai-product-scene-generator contributors" 換成使用者名字/公司（zeczec）。
3. **Phase 3（順延中）**：深度圖自動偵測水平面，解「換背景要手調 `surface_line_frac`」；`plans/phase3-depth-detection.md` 已有 draft，開工前要先實測定深度模型來源。
4. **發佈相關（未來）**：建立 GitHub repo 實際推上去；Manager registry 登錄（Phase 4.1，順延）。
5. **觀感收尾（可選）**：柔散陰影邊緣略方、整體仍是「去背圖貼生成背景」本質。

## Quick Start for Next Session
「接續 ai-product-scene-generator：V2 Phase 1/2/2.5 + Phase 4（ComfyUI 節點包）都完成並 live 驗證。節點包 = repo-root `__init__.py` → `comfyui_nodes/`（node_analyze / node_composite / tensor_io），import `scripts/` 共用大腦；範例在 `workflows/comfyui_api/product_scene_example_api.json`（API 格式，綁 z-image-turbo）；README/LICENSE(MIT) 齊。live 機器上節點已 symlink 進 ComfyUI (1) 的 custom_nodes、product.png 在 ~/ComfyUI-Shared/input。roadmap 剩 Phase 3（深度偵測擺位，順延）。若要驗證節點：確認 ComfyUI (1) 實例開著，`python` 打 127.0.0.1:8188 POST 範例 workflow。開發紀律照 PLAN.md（目前 Phase 4 已 done）。」
