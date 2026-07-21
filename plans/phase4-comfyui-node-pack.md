# Phase 4 — 打包成 ComfyUI 自訂節點包 — Plan

> 把 V2 的 Python 大腦(裁切/幾何/配光分析/組prompt)包成兩顆 ComfyUI 自訂節點 + 範例 workflow,公開到 GitHub 讓別人 git-clone 裝來用。
> 狀態:done
> 最後更新:2026-07-21

## 為什麼做

現在只能在單機用 `python scripts/generate.py` 手調跑。使用者要把它發佈給其他 ComfyUI 使用者裝來用——這需要把 Python 邏輯包成 ComfyUI 節點、附可載入的範例工作流與文件。這是產品化跳躍,且**刻意翻轉專案一貫「不用自訂節點」的排除原則**(為發佈而為之)。

## 改什麼／範圍

- 新增節點包資料夾 `comfyui_nodes/`(與 CLI 同 repo,不開新 repo),兩顆節點:
  - `AnalyzeProductLighting`(生成前):場景描述 + 產品(IMAGE+MASK) → 完整 positive prompt(已織入光線子句) + shadow_dir
  - `CompositeProductScene`(生成後,最重):背景 + 產品(IMAGE+MASK) + shadow_dir + 桌面高度鈕 + 微調鈕 → 最終合成圖。**內部整包**:tight-crop → 幾何 → 雙層陰影 → 合成,全在 PIL。
- 兩顆節點都 **import 現有共用模組**(`scripts/geometry.py`、`analyze_product_light.py`、`prompt_builder.py`),不複製邏輯。
- tensor↔PIL 只在節點進出口轉;產品走 IMAGE+MASK 進來、內部拼回 RGBA;無透明度(MASK 全不透明/缺失)→ 丟明確錯誤。
- ⚠️ **新 code 重點**:Node B 的雙層陰影+合成現在是靠 `composite_api.json`(ComfyUI graph)做的;「整包」= 把那段合成邏輯用 PIL 重建(solid canvas / GaussianBlur / alpha paste)。geometry.py 只給數字,實際貼圖是新寫的 PIL。
- 範例 `workflows/comfyui_ui/product_scene_example.json`:綁 z-image-turbo。
- `README`(安裝/模型需求/換模型調哪些鈕/節點 I/O)、`LICENSE`(MIT)、`requirements.txt`(Pillow)。
- CLI(`scripts/generate.py` + `composite_api.json`)保留自用、不對外承諾維護。

## 任務

- [x] 1. 節點包骨架:建 `comfyui_nodes/__init__.py`(NODE_CLASS_MAPPINGS + DISPLAY_NAME 掛兩顆)、`requirements.txt` 加 Pillow(內部步驟)
- [x] 2. tensor↔PIL helper `comfyui_nodes/tensor_io.py`:IMAGE(BHWC float)+MASK → RGBA PIL;PIL → IMAGE tensor;含「MASK 全不透明/缺失 → raise 明確錯誤」守則(內部步驟)
- [x] 3. Node A `AnalyzeProductLighting`:import analyze_product_light + prompt_builder;輸入場景描述字串 + 產品 IMAGE+MASK → 輸出 positive prompt 字串 + shadow_dir 字串
- [x] 4. Node B `CompositeProductScene`(最重):import geometry 算幾何 + **PIL 重建雙層陰影與合成**;輸入背景 IMAGE + 產品 IMAGE+MASK + shadow_dir + surface_line_frac 鈕 + 微調鈕 → 輸出最終 IMAGE
- [x] 5. 範例 workflow.json(綁 z-image-turbo):LoadImage(產品)→ A → CLIP Encode → KSampler → 空背景 → B → SaveImage
- [x] 6. README(安裝/模型需求/換模型調哪些鈕/兩顆節點 I/O)+ LICENSE(MIT)
- [x] 7. live 端到端驗證:ComfyUI 載入範例跑一次

## 驗收條件

- 情境(task 3):在 ComfyUI 放 Node A、接產品圖執行 → 輸出 prompt 字串含光線子句,shadow_dir 為 left/right/none 之一;丟無透明度圖 → 節點紅框報明確錯誤。
- 情境(task 4):放 Node B、接背景+產品執行 → 輸出圖產品緊貼桌面線、底下有雙層陰影;動 surface line 鈕 → 產品上下移動;無透明度 → 報錯。
- 情境(task 5):ComfyUI「Load」該 .json → 已裝 z-image-turbo 時圖成功載入、無缺節點。
- 情境(task 6):照 README 步驟能把節點包裝起來並在 ComfyUI 選單看到兩顆節點;LICENSE 檔存在且為 MIT。
- 情境(task 7):整條範例跑完,`outputs/` 出現最終圖,目視產品接地且與背景光線同調。

## 決策紀錄

| # | 決策點 | 選了 | 理由 |
|---|---|---|---|
| 1 | 發佈野心 | 公開 GitHub、git-clone 可裝,registry 順延 | 「可裝可跑可讀」已是大跳;registry 是獨立審核+維護,當後續里程碑 |
| 2 | 節點切法 | 兩顆(A 生成前/B 生成後),B 合成整包,A 順便組 prompt | 分析必須在生成前、合成在生成後→至少兩顆;整包讓 tested PIL 邏輯原封複用,免脆弱的 INT 扇出子圖;A 吸收 prompt_builder 讓該段邏輯有家、使用者只接一條線 |
| 3 | tensor 策略 | 進出口轉 tensor↔PIL、內部 PIL 原封;產品走 IMAGE+MASK 拼 RGBA;無 alpha 報錯 | ComfyUI IMAGE 不帶透明度、alpha 走 MASK;整套邏輯靠 alpha,故收兩輸入自拼;fail-loud 與現有 CLI 一致 |
| 4 | Python CLI | 留著自用、不對外承諾維護 | 一路靠 CLI 驗證,砍了可惜;對外多養一條路不值得。大腦共用、內部 PIL 未動→幾乎免費繼續能跑 |
| 5 | 範例模型 | 綁 z-image-turbo + README 文件化換模型調哪些鈕 | 節點本身模型無關(免費);只有生背景參數綁模型;湊「通吃參數」做不到,故給可重現範例+換模型指南 |
| 6 | Phase 3 深度偵測 | 順延(不進 v1);surface line 當節點鈕+好預設 | Phase 4 已大;深度模型來源未定案是研究非打包工作,混做兩邊拖 |
| 7 | 授權 | MIT | ComfyUI 圈預設、最寬鬆;相依只 Pillow 無衝突;z-image-turbo 模型未打包只引用,README 提一句其自有授權 |

## 架構

```
custom-node pack（同一 repo，新增 comfyui_nodes/）
 ├ [C] Node A「AnalyzeProductLighting」  ← 生成前
 │     in: 場景描述(STR) + 產品(IMAGE+MASK)
 │     └ import analyze_product_light（色溫/明暗/柔硬/光向）+ prompt_builder（填模板）
 │     out: positive prompt(STR) + shadow_dir(STR)
 ├ [T] 原生 ComfyUI：CLIP Text Encode → KSampler(turbo 參數) → 空背景     ← 生成
 ├ [C] Node B「CompositeProductScene」  ← 生成後（最重）
 │     in: 背景(IMAGE) + 產品(IMAGE+MASK) + shadow_dir + surface_line_frac + 微調鈕
 │     ├ import geometry（緊裁 + 塞框 + 擺位 + 雙層陰影規格）
 │     └ PIL 重建合成（solid canvas / GaussianBlur / alpha paste；取代 composite_api.json graph）
 │     out: 最終合成圖(IMAGE)
 └ 共用大腦 [D]：scripts/geometry.py、analyze_product_light.py、prompt_builder.py（節點與 CLI 都 import）
    附：範例 workflow.json（綁 turbo）、README、requirements.txt(Pillow)、LICENSE(MIT)

備註：CLI 仍走 composite_api.json（HTTP graph）；Node B 走 PIL 合成——雙層陰影觀感可能微幅漂移，可接受（CLI 僅自用）。
```
