# AI Product Scene Generator — Master Roadmap

> 通用可客製產品情境合成管線：一張去背 PNG + 背景提示詞 → 自動產出場景合成產品照
> 狀態：in-progress（V1 + Phase 1–7 全完成並 live 驗證；Phase 4 節點包已公開發佈為 `ComfyUI-RealProductScene`）
> repo：<https://github.com/yorimi-tamai/ComfyUI-RealProductScene>（本地資料夾仍為 `ai-product-scene-generator`）
> 最後更新：2026-07-22

## 大方向

V1（已完成）：手動 ComfyUI workflow，把特定產品去背 PNG 合成到 AI 背景 + 接觸陰影。
V2（本 roadmap）：加一層 Python 編排 + 幾何自適應，讓**任意比例產品**都能自動縮放、擺位、接地，並可用 config 微調。

完整設計見 `plans/`。決策脈絡見 `~/.claude/plans/sparkling-knitting-wombat.md`（plan mode 核准版）。

## 進度

- ✅ **V1 — 手動合成 workflow + 接觸陰影**（已驗證，見 `handoff-archive/…接觸陰影｜#1…`）
- ✅ **Phase 1 — 確定性幾何管線**（`plans/phase1-geometry.md`，done）
  - Python 編排 + 拆兩個 API workflow + alpha 緊裁/塞目標框/擺位/陰影自適應 + config 微調鈕
  - 平面接觸線先用 config 可調固定值；已 live 驗證端到端（藤籃產品接地成功）
  - ⚠️ 已知限制：隨機 seed 下背景桌面位置會變，固定 `surface_line_frac` 需手動對——正是 Phase 2 要自動化的
- ✅ **Phase 2 — 產品主導配光（product-led lighting）**（`plans/phase2-product-led-lighting.md`，done）
  - 反轉思路：產品固定，背景遷就產品的光。讀產品照的色溫/明暗/柔硬度/光向 → 寫進背景 prompt，讓生成場景與產品同調（守「不改產品」規則）
  - 光向分析也驅動陰影落向。已 live 驗證：藤籃 auto 配光後背景明顯轉暖/亮/柔、與產品同調
  - ⚠️ 未解：接地陰影仍為方塊柔霧、無漸層（接觸感不足）；擺位仍靠固定 surface line
- ✅ **Phase 2.5 — 陰影接觸核（雙層陰影）**（done，小型自足改進）
  - 在柔散陰影下疊緊實深色低模糊接觸核，合成序：背景→柔散→接觸核→產品
  - 已 live 驗證（同 seed 對比）：基座接觸感明顯優於單層均勻霧
  - ⚠️ 仍非完美：柔散層邊緣略帶方形、整體仍是「去背圖貼生成背景」本質
- ✅ **Phase 3 — 深度圖自動偵測水平面 + 人工修正介面**（`plans/phase3-depth-detection.md`，done，live 驗證）
  - 接觸線從 config 固定值換成每張生成圖自動偵測（transformers `Depth-Anything-V2-Small`，跑 ComfyUI `.venv`/MPS，零新套件）；失敗/傾斜/低信心 fallback 回固定值
  - 選面：主導（最大縱向）水平面；接觸線取**近端/前緣** `band_top + K·span`（K=0.6）——修掉「取遠端上緣→產品飄空」的首驗 FAIL
  - **人工修正介面**（自動只 ~70-80% 準）：CLI 四鈕 `--surface-line-frac` / `--offset-x` / `--offset-y` / `--scale-mult`，優先序 manual > fixed > auto
  - 驗證：3 種桌面高度全接地 + fresh 全自動接地；`tests/` 兩支單元測試（detect 11 + manual 9）；scope 限正面/微俯，強傾斜面 fallback
  - ⚠️ 殘留：接觸陰影仍偏軟（淡灰暈，Phase 2.5 範疇）；玻璃/多層堆疊等難例靠 fallback + 人工鈕兜底
- ✅ **Phase 4 — 打包成 ComfyUI 自訂節點包並發佈**（`plans/phase4-comfyui-node-pack.md`，done，live 驗證；2026-07-22 **正式公開**）
  - 目標：公開 GitHub repo，讓其他 ComfyUI 使用者 git-clone 裝來用（UI 內一份可載入的範例工作流）；Manager registry 順延
  - 兩顆節點：`AnalyzeProductLighting`（生成前，產品→prompt+shadow_dir）＋ `CompositeProductScene`（生成後，整包裁切/幾何/雙層陰影/合成）；都 import 現有共用大腦
  - tensor 只在節點進出口轉、內部 PIL 原封；產品走 IMAGE+MASK 拼 RGBA；範例綁 z-image-turbo + README 換模型指南；MIT
  - ⚠️ **刻意翻轉下方「不用自訂節點」的排除項**——為發佈而為之的架構決定
  - Phase 3 深度偵測順延（不進 v1）；CLI 保留自用
  - ✅ **發佈收尾（2026-07-22，見 `handoff-archive/…Phase4發佈公開repo｜#1…`）**：改名 `ai-product-scene-generator` → **`ComfyUI-RealProductScene`**（合 registry `ComfyUI-` 慣例）、LICENSE 版權人 → `zeczec`、公開到 <https://github.com/yorimi-tamai/ComfyUI-RealProductScene>（個人帳號、Public、HEAD `cf83a13`）。本地資料夾仍叫 `ai-product-scene-generator`
  - ⬜ **B3 待辦：ComfyUI Manager registry 上架**——發佈最後一哩，獨立里程碑（需裝 `gh` + 補 registry metadata + 開 PR 過審核）
- ✅ **Phase 5 — 品質打磨（合成擬真度）**（`plans/phase5-quality-polish.md`，done，live 驗證）
  - 降貼圖感：#1 漸層接觸陰影（含 AO，`shadow.py` 生成橢圓徑向漸層貼圖，Python `bake_shadow`
    合成進背景取代 ComfyUI 矩形色塊）＋ #2 難例選面加固（次大面≥70%→曖昧走 fallback）
    ＋ #3 `front_k` 隨 band span 自適應（clip 0.5+0.6·span, [0.5,0.8]）
  - 陰影參數 live 校準：op0.58/core0.28/falloff1.4/flatten0.24；測試 shadow13+detect15+manual9 全綠、
    9 張回歸 fixtures 無誤觸；驗收報告 `outputs/phase5_validation/report.html`
  - #4 反射明確排除 V2（要畫產品沒有的像素、逼近「不改產品」紅線）；AO 併入 #1
  - ⚠️ 殘留：玻璃桌看穿/強傾斜靠人工鈕兜底；反射不做
- ✅ **Phase 6 — 自帶背景 / 多後端**（`plans/phase6-byo-background.md`，done，live 驗證）
  - 把管線從「綁 ComfyUI 生成」解成可切後端：`backend: comfyui | manual`（`--bg` > config）
  - manual 後端吃任意來源（MJ/GPT/自拍）現成背景、跳過生成＋配光、跑後半段；`--shadow-dir` 指落向
  - 吃背景實際尺寸＋非 9:16 軟警告＋不裁；MJ/GPT 官方 API 不接（手動背景即解）
  - 測試 `test_backend.py`(13) 全綠、既有不回歸；manual live 1024² 接地、comfyui 回歸正常
  - ⚠️ 合成仍走 ComfyUI，故 manual 仍需 server（只為合成）
- ✅ **Phase 7 — GPT 場景 → ComfyUI 刷回真產品（swap 後端）**（`plans/phase7-swap-mode.md`，done，live 驗證）
  - 新增第三後端 `backend: swap`：GPT 生**完整場景**（含產品）當模板 → 對齊後把真產品「刷回」場景裡假產品的位置 → 繼承 GPT 自然陰影/光、產品像素 100% 真實
  - 對齊＝混合（opencv `matchTemplate`／`TM_CCOEFF_NORMED`＋透明區均值填 + 四鈕手動）；刷回＝B 邊緣光包裹（`bake_light_wrap` PIL，內部不動，ComfyUI 合成）；覆蓋＝分段（v1 defringe+微放大力保覆蓋，除抹+inpaint 兜底後續）
  - swap 跳過 depth/bake_shadow/配光（都來自 GPT 場景）；合成沿用 `composite_api.json`
  - 2 例 live 驗證：籃子（`outputs/phase7_swap_final.png`）＋ slingback 鞋（後者逼出 `scale_max` 1.5→2.5 bug 並修）；破例加 `opencv-python`
  - ⚠️ 殘留：細長 silhouette（帶/細跟）對對齊誤差敏感、易露雙影，靠四鈕或後續除抹+inpaint；姿態差太多自動抓不準

## 階段依賴

- Phase 2/3 都**依賴** Phase 1（管線骨架）。
- Phase 2（配光）插點在「背景生成**前**」（先分析產品再生成背景）；Phase 3（擺位偵測）插點在「背景生成**後**、幾何前」。兩者互不衝突，可先後做。

## 為什麼調整方向（2026-07-21 Phase 1 驗收後）

Phase 1 live 驗收暴露兩問題：產品浮空（接地差）＋產品與背景光線不一致。使用者反轉思路——**以讀入的產品照為主、去生成適合的背景**——同時解光線一致與陰影方向，且不牴觸「不改產品」。故插隊為 Phase 2，深度偵測擺位順延 Phase 3。

## 守住邊界（V1/V2 共同排除）

自動去背、IP-Adapter、ControlNet 風格控制、AI 影片生成、n8n、自動發布、多鏡頭一致性、自訂合成節點。輸入必須是具 alpha 的去背 PNG（JPG 擋下報錯）。
