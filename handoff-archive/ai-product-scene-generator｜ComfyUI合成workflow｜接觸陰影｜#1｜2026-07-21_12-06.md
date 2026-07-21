# Handoff — ai-product-scene-generator｜ComfyUI合成workflow｜接觸陰影｜#1 — 2026-07-21 12:06

> 檔案: `ai-product-scene-generator｜ComfyUI合成workflow｜接觸陰影｜#1｜2026-07-21_12-06.md`
> 前一份同單元 handoff: （無、這是該單元第一份）

## The Goal
在既有、可運行的 ComfyUI「Product Scene Composer V1」合成 workflow 上，加入「產品接觸陰影」，讓合成後的產品看起來真的放在桌面上、而非貼上去 —— 為後續 image-to-video 產出更可信的 keyframe。

## 本次推進（This Session's Progress）
- 建立 `ai-product-scene-generator` 專案骨架（config / prompts / inputs / outputs / workflows / scripts）＋ V1 規格檔（product/scene/generation.json、scene_prompt_template.txt、negative_prompt.txt、README、CLAUDE.md）。
- 在使用者提供的可運行 workflow 上，完成**接觸陰影升級**，全部使用 ComfyUI 內建節點、未動任何既有節點的功能：
  - 新增 8 個節點（ID 72–79）：MaskToImage→ImageScale(壓扁)→ImageBlur→ImageToMask→(SolidMask×MaskComposite 降透明)→ 深灰 EmptyImage → ImageCompositeMasked(陰影先合成)。
  - 唯一改動既有節點：產品合成節點 69 的 destination 從「背景」改接「背景+陰影」，產品本體/縮放/位置/儲存全保留。
- 產出兩種格式並保持同步：API 格式（`workflows/comfyui_api/product_scene_composite_v2_api.json`）＋ UI 格式（`workflows/comfyui_ui/product_scene_composite_v2.json`）。
- 陰影位置經 3 輪實跑校正，最終**接地成功、已驗證**（右上「任務已完成」，箱底出現柔和接地陰影）。

## Where We Are
- V1 規格 + 接觸陰影升級皆完成並驗證通過。
- **目前生效參數**（節點 79 陰影合成）：X=155、Y=640、resize_source=false；`SolidMask` 值=0.3（透明度）；`ImageBlur` blur_radius=8 / sigma=6；陰影壓扁尺寸 320×130；陰影色 EmptyImage=0x1A1A1A 深灰。
- 產品合成節點 69：X=130、Y=415，產品縮放 320×416（節點 65）。
- **檔案位置**：使用者實際載入的是 `~/Downloads/product_scene_composite_v2.json`；專案 `workflows/comfyui_ui/` 內為同版存底（兩份內容一致）。API 版在 `workflows/comfyui_api/`。原始 V1 UI 檔仍在 `~/Downloads/product_scene_composite_v1.json`。
- **已知限制（重要）**：陰影是「整個產品輪廓壓扁+模糊+降透明」的柔色塊，非物理正確接觸陰影 —— 無近實遠虛漸層、不隨透視傾斜、換成高瘦產品（瓶罐類）需重調壓扁高度。使用者與 Claude 已共識：這是方法天花板，列為**未來獨立升級項**，V1 不追。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| 先交付 API 格式 JSON 給使用者在 ComfyUI 介面載入 | 介面 Load 不吃 API 格式，畫布空白、看不到節點 | ❌ abandoned（API 版保留供 /prompt API 用，但介面編輯改用 UI 版）|
| 複製原始 UI JSON 後以外科式 Edit 加節點/改連線 | 成功，但檔案在使用者操作中兩度從專案資料夾消失 | 🟡 partial（改用程式化重建更穩）|
| 用 python 載入原 JSON、程式化 mutate 後寫出＋驗證 | 穩定，18 節點/18 連線、link 唯一、無斷點 | ✅ kept |
| 陰影 Y=700 | 陰影與箱底有空隙 → 飄在空中 | ❌ abandoned |
| 陰影 Y=560 | 陰影塞到箱身正下方 → 被不透明產品蓋掉、看不到 | ❌ abandoned |
| 陰影 X=155 / Y=640（往下往右探出產品輪廓） | 接地陰影正確顯示、看起來放在桌上 | ✅ kept |

## Key Decisions
- **交付 UI 格式為主**：選 UI JSON（可畫布顯示/編輯），API JSON 僅保留供程式呼叫。理由：使用者在介面工作，API 格式無法在畫布顯示。
- **程式化重建 workflow**：選 python mutate 原 JSON，拒絕繼續手動逐條 Edit。理由：手改易錯、且檔案會消失需重建，python 可一次到位並自動驗證連線。
- **陰影用內建節點的「壓扁輪廓」法**：選 MaskToImage→Scale→Blur→ToMask→降透明 這條全內建鏈，拒絕自訂節點/IP-Adapter/ControlNet。理由：符合 V1「只用內建、穩定優先、不過度複雜」紀律。
- **陰影瑕疵不再微調**：選擇收斂、列為已知限制，拒絕繼續拖 X/Y/透明度。理由：怪感來自方法天花板而非參數，微調報酬遞減；image-to-video 動起來會蓋過靜態瑕疵。

## User Feedback / Preferences
- 明確要求：不重建 workflow、不刪既有可運行節點、儘量用 ComfyUI 內建節點、不猜測不存在的節點名。
- CLAUDE.md 長期規則：產品本體優先用原始 PNG、不可 AI 重新設計產品、不改 Logo/文字/結構、workflow 模組化、V1 穩定優先、**未拿到可運行 workflow 前不臆造 JSON**。
- 對「照個陰影還是有點怪，有需要現在調整嗎」→ 接受「不需要現在調、列為已知限制往下走」的建議。

## Git State
- **非 git repo**（`ai-product-scene-generator` 未初始化 git）。無 branch / commit / diff 資訊。
- 若要納入版本控管，下個 session 可考慮 `git init` 後首次 commit 現有規格 + workflow v2。

## Where We're Going (Next Steps)
1. （可選微調，觀感問題）陰影想更「往前落桌面」→ 節點 79 Y 加到 ~670；想更實 → SolidMask 值 0.3→0.35。不動亦可用。
2. **下一個 workflow 升級**由使用者決定方向（尚未指定）。V1 明確排除清單仍有效：自動去背、IP-Adapter、ControlNet、AI 影片生成、n8n、自動發布、多鏡頭一致性、自訂節點。
3. 未來若要把陰影做真（獨立升級）：只從產品底部派生陰影、加透視傾斜、加漸層衰減 —— 值得單獨開一輪。
4. 建議：把 Downloads 的載入檔與專案存底的同步流程固定下來（目前靠手動 copy，易漏），或改成直接從專案資料夾載入。

## Quick Start for Next Session
「接續 ai-product-scene-generator：V1 規格 + ComfyUI 接觸陰影升級已完成並驗證（陰影參數 X155/Y640、透明0.3、模糊8，全內建節點）。載入檔在 ~/Downloads/product_scene_composite_v2.json，專案存底在 workflows/comfyui_ui/。陰影為壓扁輪廓、非物理正確，列為已知限制。今天想做 ___（下一個 workflow 升級 / 陰影做真 / git 初始化 / 其他）。」
