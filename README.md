# ai-product-scene-generator

AI 產品情境圖生成工具。

使用者提供一張**已去背、具透明背景的產品 PNG** 並輸入場景描述，系統透過 ComfyUI
生成一張沒有產品的商業情境背景，再把真實產品合成進去，輸出一張適合後續
Image-to-Video 的產品情境圖。

## V1 流程

```
產品 PNG + 場景設定
        │
        ▼
ComfyUI 生成「空的」9:16 商業情境背景（畫面無產品，保留乾淨放置平面）
        │
        ▼
將真實產品 PNG 合成到背景中（保留外觀、比例、Logo、文字）
        │
        ▼
輸出最終產品情境圖（適合後續 Image-to-Video）
```

## V1 範圍

會做：

1. 生成一張沒有產品的 9:16 商業情境背景
2. 將真實產品 PNG 合成到背景中
3. 保留產品原本的外觀、比例、Logo 與文字
4. 輸出一張適合後續 Image-to-Video 的產品情境圖

**V1 暫不處理**（刻意排除，保持單純）：

- 自動去背
- IP-Adapter
- ControlNet
- AI 影片生成
- n8n
- 自動發布
- 多鏡頭一致性
- 自訂 ComfyUI Node

## 目錄結構

```
ai-product-scene-generator/
├── config/
│   ├── product.json         # 產品資訊與合成位置 / 比例
│   ├── scene.json           # 場景、風格、光線、鏡頭、保留空間
│   └── generation.json      # 生成參數（尺寸、seed、steps、sampler…）
├── prompts/
│   ├── scene_prompt_template.txt   # 空場景 prompt 模板（可帶入 scene.json）
│   └── negative_prompt.txt         # V1 negative prompt
├── inputs/
│   ├── products/            # 產品原圖（去背 PNG），預設 product.png
│   └── references/          # 參考圖 / 風格參考
├── outputs/
│   ├── backgrounds/         # 生成的空背景
│   ├── composites/          # 合成中間稿
│   └── final/               # 最終成品
├── workflows/
│   ├── comfyui_ui/          # ComfyUI 介面用 workflow
│   └── comfyui_api/         # ComfyUI API 用 workflow
└── scripts/                 # 執行腳本
```

## 設定檔

- `config/product.json` — 產品名稱、類型、圖片路徑、合成比例與位置
  （`position_x` / `position_y` 為 0~1 的相對座標，預設放置於畫面下方中央）
- `config/scene.json` — 場景描述，欄位對應 prompt 模板中的替換變數
- `config/generation.json` — 生成尺寸與取樣參數。V1 尺寸為 576 × 1024（9:16）

## 狀態

規格初版建立完成，尚未撰寫程式，尚未接上 ComfyUI。
