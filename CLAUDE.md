# CLAUDE.md — ai-product-scene-generator

給 Claude 的專案工作說明。

## 專案目標

使用者提供一張已去背的產品 PNG 與場景描述，透過 ComfyUI 生成一張沒有產品的
9:16 商業情境背景，再把真實產品合成進去，輸出適合後續 Image-to-Video 的
產品情境圖。

## V1 流程

`產品 PNG + 場景設定 → ComfyUI 生成空背景 → 合成真實產品 → 輸出最終圖片`

## 目錄用途

- `config/product.json` — 產品資訊與合成位置 / 比例
- `config/scene.json` — 場景、風格、光線、鏡頭、保留空間
- `config/generation.json` — 生成參數（尺寸、seed、steps、cfg、sampler、輸出路徑）
- `prompts/scene_prompt_template.txt` — 空場景 prompt 模板（可帶入 scene.json）
- `prompts/negative_prompt.txt` — V1 negative prompt
- `inputs/products/` — 產品原圖（去背 PNG），預設 `product.png`
- `inputs/references/` — 參考圖 / 風格參考
- `outputs/backgrounds/` — 生成的空背景
- `outputs/composites/` — 合成中間稿
- `outputs/final/` — 最終成品
- `workflows/comfyui_ui/` — ComfyUI 介面用 workflow
- `workflows/comfyui_api/` — ComfyUI API 呼叫用 workflow
- `scripts/` — 執行腳本

## 長期規則（務必遵守）

1. **產品本體優先使用原始 PNG。** 最終圖中的產品必須來自使用者提供的真實
   產品圖，不是重新生成的。
2. **不可以讓 AI 任意重新設計產品。** 產品的外觀、造型、材質一律以原圖為準。
3. **不可以修改 Logo、包裝文字與產品結構。** 合成時完整保留，不重繪、不變形、
   不改字。
4. **Workflow 必須保持模組化。** 生成背景、合成、輸出各步驟分離，方便單獨替換。
5. **第一版以穩定運行優先，不追求過度複雜。** 先能穩定跑完整流程再談優化。
6. **在使用者尚未提供成功運行的 ComfyUI API Workflow 前，不要自行猜測或生成
   完整的 Workflow JSON。** 需要 workflow 時先向使用者索取，不要臆造。

## V1 明確排除（先不要做）

自動去背、IP-Adapter、ControlNet、AI 影片生成、n8n、自動發布、
多鏡頭一致性、自訂 ComfyUI Node。

## 開發紀律

- 動程式前先與使用者確認方向；本階段只建立規格，不寫 Python、不呼叫 ComfyUI。
