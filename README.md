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

## ComfyUI 自訂節點包（V2）

V2 把管線包成兩顆 ComfyUI 自訂節點，讓你在 ComfyUI 介面裡直接跑。核心約束不變：
**產品像素 100% 不改**（不重繪、不改 Logo/文字/結構）。

### 兩顆節點

| 節點 | 時機 | 輸入 | 輸出 |
|---|---|---|---|
| **Analyze Product Lighting** | 生成背景**前** | 產品 `IMAGE`+`MASK`、場景描述欄位、`lighting_mode`（auto/manual） | `positive_prompt`、`negative_prompt`、`shadow_dir` |
| **Composite Product Scene** | 生成背景**後** | 背景 `IMAGE`、產品 `IMAGE`+`MASK`、`shadow_dir`、`surface_line_frac` 等微調鈕 | 最終合成 `IMAGE` |

「產品主導配光」：Analyze 讀產品照的色溫/明暗/柔硬/光向，寫進背景 prompt，讓 AI 生成的
場景**遷就產品的光**；同一分析也決定陰影落向。Composite 自動緊裁去背產品、等比塞進目標框、
把底部貼到接觸線，並鋪一層柔散 + 一層緊實接觸核的雙層陰影。

> ⚠️ 產品輸入**必須是已去背、具透明度的 PNG**（用 `LoadImage`，把它的 `IMAGE` 與 `MASK`
> 兩個輸出都接進節點）。接了沒有透明度的圖，節點會直接報錯（本專案不做自動去背）。

### 安裝

```bash
cd ComfyUI/custom_nodes
git clone <this-repo-url> ai-product-scene-generator
pip install -r ai-product-scene-generator/requirements.txt   # Pillow（ComfyUI 通常已內建）
# 重啟 ComfyUI
```

重啟後，節點選單的 `product-scene` 分類下會出現 **Analyze Product Lighting** 與
**Composite Product Scene**。

### 範例工作流

`workflows/comfyui_api/product_scene_example_api.json`（API 格式）串好整條：
`LoadImage(產品) → Analyze → CLIP Encode → KSampler → 空背景 → Composite → SaveImage`。
把產品去背 PNG 命名為 `product.png` 放進 ComfyUI 的 input 資料夾即可跑。

### 模型需求（範例綁 z-image-turbo）

範例的**生成段**是為 z-image-turbo 調的，需要這三個檔：

| 用途 | 檔名 | 節點 |
|---|---|---|
| 擴散模型 | `z_image_turbo_bf16.safetensors` | UNETLoader |
| CLIP | `qwen_3_4b.safetensors`（type `lumina2`） | CLIPLoader |
| VAE | `ae.safetensors` | VAELoader |

> 這些模型有各自的授權，請依其原始授權使用；本專案未打包模型、僅在範例中引用。

### 換成別的模型

兩顆自訂節點**與模型無關**——它們不管背景是誰生的。要換模型時，只改範例裡「生背景」那一段：

- **KSampler**：`steps` / `cfg` / `sampler_name` / `scheduler`（turbo 是 8 步、cfg 1、
  res_multistep/simple；一般 SDXL 類要改成各自合適值，否則會壞）
- **模型/CLIP/VAE 載入器**：換成你的 checkpoint（若是單檔 checkpoint，可用 `CheckpointLoaderSimple` 取代三顆載入器）
- **ModelSamplingAuraFlow**：非 AuraFlow/Lumina 類模型可移除
- **EmptySD3LatentImage**：依模型的 latent 需求替換

### CLI（自用，非發佈重點）

`python scripts/generate.py --server 127.0.0.1:8188` 走 HTTP 打 ComfyUI 的兩個 API graph。
開發/回歸測試用途，不對外承諾維護。

> **執行環境**：需 torch + transformers（Phase 3 深度偵測用）。用 ComfyUI 的 venv 最省事，例如
> `"…/ComfyUI/.venv/bin/python" scripts/generate.py`；系統 Python 若無 torch，深度偵測會自動 fallback 回固定值。

**Phase 3 — 自動接觸面偵測**：生成背景後，用深度圖（`Depth-Anything-V2-Small`）自動求接觸線，
產品自動接地，換不同高度的桌面 prompt 不必手改 config。傾斜/俯視、多層曖昧、低信心或無模型時，
自動 fallback 回 `scene.json.surface_line_frac`。

**人工修正介面**（自動約 7-8 成準，其餘用這些鈕兜底，優先於自動偵測）：

| 旗標 | 作用 |
|---|---|
| `--surface-line-frac 0.85` | 手動指定接觸線（0..1），覆蓋自動偵測 |
| `--offset-x 30` / `--offset-y -15` | 產品水平/垂直微調（px，+右 / +下） |
| `--scale-mult 1.2` | 產品縮放倍率 |
| `--fixed-surface` | 跳過偵測、直接用 `scene.json` 的值 |
| `--surface-min-conf 0.5` | 低於此信心就 fallback |

例：`python scripts/generate.py --surface-line-frac 0.82 --scale-mult 1.1 --offset-x 20`。
`offset_x/offset_y/scale_mult` 也可寫進 `config/product.json` 的 `overrides` 當持久預設（CLI 會蓋過它）。

**Phase 6 — 背景後端（自帶背景 / 多後端）**：背景那步可切兩種後端，後半段（深度接地、
漸層陰影、幾何、合成）兩者共用。

| 後端 | 怎麼觸發 | 行為 |
|---|---|---|
| `comfyui`（預設） | 不給 `--bg`、`generation.json` `backend:comfyui` | 讀產品配光 → 生成 9:16 空背景（現狀全自動） |
| `manual` | `--bg <path>`，或 `backend:manual` + `manual_bg_path` | 用你現成的背景（Midjourney / GPT / 自拍），**跳過生成** |

- 優先序：`--bg` > `config`。`manual` 缺圖會明確報錯。
- 手動背景**吃實際尺寸**當畫框（任意比例都能跑）；非 9:16 印軟警告、**不自動裁**（要 9:16 自己先裁好）。原圖不被修改。
- 手動模式的陰影落向用 `--shadow-dir left|right|none`（預設 `right`）——它在全自動模式也能覆蓋產品配光分析的落向。
- ⚠️ 合成貼產品仍走 ComfyUI，故 `manual` 後端**仍需 ComfyUI server 開著**（只為合成、不生成）。
- Midjourney 沒有官方 API、GPT image 要金鑰＋付費——`manual` 後端就是繞過這些的通用解：任何工具生的背景都能丟進來接。

例：`python scripts/generate.py --server 127.0.0.1:8188 --bg ~/mj_scene.png --shadow-dir left`。

## 授權

本專案採 **MIT**（見 `LICENSE`）。範例引用的模型有各自的授權，不在本授權範圍內。

## 狀態

V2 完成：Phase 1/2/2.5 管線 + Phase 3（深度自動接地 + 人工修正介面）+ Phase 4 節點包打包
+ Phase 5（漸層接觸陰影 + 難例選面加固 + K 自適應）+ Phase 6（自帶背景 / 多後端）。
詳見 `PLAN.md` 與 `plans/`。
