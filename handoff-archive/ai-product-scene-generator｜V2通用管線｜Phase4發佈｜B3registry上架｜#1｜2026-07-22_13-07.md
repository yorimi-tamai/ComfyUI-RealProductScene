# Handoff — ai-product-scene-generator｜V2通用管線｜Phase4發佈｜B3registry上架｜#1 — 2026-07-22 13:07

> 檔案: `ai-product-scene-generator｜V2通用管線｜Phase4發佈｜B3registry上架｜#1｜2026-07-22_13-07.md`
> 前一份同單元 handoff: （無、B3registry上架子單元第一份；相關前身＝「…V2通用管線｜Phase4發佈公開repo｜#1…」＝GitHub repo 對外公開，本份是同一 Phase 4 發佈努力的 **registry 上架最後一哩**）

## The Goal
把當初順延的發佈最後一哩 **B3＝ComfyUI Registry 上架** 做掉，讓其他人能在 ComfyUI Manager 裡直接搜到、一鍵安裝這個節點包（不必手動 git clone）。

## 本次推進（This Session's Progress）
- **節點正式上架 ComfyUI Registry 並 live**：<https://registry.comfy.org/nodes/comfyui-realproductscene>（API 實測 `status: NodeStatusActive`、publisher `yorimi` active、description/repository 都正確帶上）。
- **建置發佈工具鏈（本機從零）**：裝 Homebrew 6.0.12 → `gh` 2.96.0 → `gh auth login`（瀏覽器 OAuth，帳號 `yorimi-tamai`，scopes 含 `repo`/`workflow`）。
- **建 publisher `yorimi`**（registry.comfy.org，PublisherId 永久不可改）+ 產 Registry API key → 存成 repo secret `REGISTRY_ACCESS_TOKEN`。
- **新增兩個發佈檔並 push**：`pyproject.toml`（`[project]` name=`comfyui-realproductscene`/version `1.0.0`/deps Pillow+opencv/license=LICENSE；`[tool.comfy]` PublisherId=`yorimi`/DisplayName/Repository）＋ `.github/workflows/publish_action.yml`（`Comfy-Org/publish-node-action@main`，push `pyproject.toml` 版本號→自動 publish）。
- **GitHub Action 首跑全綠**（36s，run 29892706872），節點即上架。
- **PLAN.md 收尾**：B3 標 ✅、狀態改「主線收斂」、附 registry 網址。

## Where We Are
- **repo**：`main`、HEAD `44817de`、working tree 乾淨（除本次新 handoff，見下）。
- **registry**：`comfyui-realproductscene` live、Active，v1.0.0。
- **自動重發機制已就位**：日後改版只要 bump `pyproject.toml` 的 `version` 再 push 到 main，Action 自動重新 publish，無需手動。
- **工具鏈**：Homebrew 裝在 `/opt/homebrew`（`/etc/paths.d/homebrew` 已建，新開 Terminal 自動有 `brew`/`gh` 於 PATH；`~/.zprofile` 未加 shellenv 行、非必要）；`gh` 已認證存 keyring。
- **roadmap 全數里程碑打勾**：V1 + Phase 1–7 + Phase 4 發佈（repo 公開 + registry 上架）全完成 live 驗證。剩下皆「選做」。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| `brew install gh`（先查 brew） | 本機無 Homebrew（arm64、`/opt/homebrew` 空） | 🟡 需先裝 brew |
| 由我這端跑 Homebrew 官方 install script | 需 sudo 密碼、非互動 shell 無法輸入 → 改由使用者自己 Terminal 跑 | ❌ 此環境不可行 |
| 使用者第一次跑 brew 安裝 | 卡在「Press RETURN to continue」時**用打字打 return 字母**→ R 被當「其他鍵」→ 安裝中止（`/opt/homebrew` 只建空目錄骨架、bin/Cellar 空） | ❌ 誤取消 |
| 重跑 brew 安裝、明確提示「按實體 Return 鍵、別打字」 | `brew --version` = 6.0.12，成功 | ✅ kept |
| 我這端 `brew install gh`（全路徑 `/opt/homebrew/bin/brew`） | gh 2.96.0 裝好（非 sudo，可代跑） | ✅ kept |
| `gh auth login`（互動、開瀏覽器） | 由使用者自己 Terminal 跑；`gh auth status` 確認 logged in `yorimi-tamai` | ✅ kept |
| 查 B3 真實流程（WebFetch docs.comfy.org） | 現行＝registry.comfy.org + `pyproject.toml` metadata + `comfy node publish`／GitHub Action，**不用開 PR**（推翻 handoff 舊記的「開 PR 過審核」） | ✅ 校正認知 |
| 選 publish 方式 | 選 GitHub Action（set-once secret、push 自動重發），非本機 comfy-cli | ✅ kept |
| commit+push pyproject+workflow → 觸發 Action | run 29892706872 全綠 36s；`api.comfy.org/nodes/...` 實測 Active | ✅ kept |
| WebFetch registry 節點頁驗證 | NOT FOUND（該站 client-side 渲染，初始 HTML 看不到）→ 改打 `api.comfy.org` JSON API 才確認 | 🟡 驗證改走 API |

## Key Decisions
- **publish 走 GitHub Action、非本機 `comfy node publish`**：key 存一次為 repo secret、之後 push 自動重發；免裝 comfy-cli。
- **registry `name` = `comfyui-realproductscene`（全小寫、對應 repo 名）**：immutable 識別碼，會進 registry 網址，故一次定對；使用者未否決。
- **PublisherId = `yorimi`**：使用者自建，永久不可改。
- **版本起 `1.0.0`**：V1+Phase1–7 全完成發佈，1.0.0 合理起點。
- **驗證改用 `api.comfy.org` JSON API**：registry 網頁前端渲染、WebFetch 抓不到，API 最準。
- **安全**：API key / token 一律使用者自己在 Terminal 輸入（`gh secret set` 的 `Paste your secret:`、PAT、OAuth），我不代碰——延續上一份 handoff 的偏好。

## User Feedback / Preferences
- **非技術操作需一步步帶 + 截圖溝通**：開瀏覽器輸網址、找按鈕都需具體指引；卡關時使用者以截圖回報最有效。
- **брew 安裝踩雷點**：把「Press RETURN to continue」誤解成要打字打 "return" → 下次帶人裝 brew 要明講「按鍵盤實體 Return 鍵、不要打字母」。
- **偶發手滑貼無關路徑**（如 `/Users/yoriwork/Desktop/.tmp.driveupload/...`、email）→ 不去執行、拉回主線即可（本份與上一份都出現過）。
- 沿用「收斂點主動提醒 handoff、點頭才跑」節奏；本份即使用者點頭後觸發。
- 使用者要求「做新 handoff 時把上一份未進 git 的 handoff 檔一起收進版控」。

## Git State
- Branch: `main`
- Uncommitted: 1 untracked — 本次新 handoff `…Phase4發佈｜B3registry上架｜#1｜2026-07-22_13-07.md`（將與上一份未 commit 的 `…Phase4發佈公開repo｜#1…` 一起收進版控）
- Last commits:
  - `44817de` docs: mark B3 (Comfy Registry publish) done — node live on registry
  - `9422747` B3: add Comfy Registry metadata + auto-publish workflow
  - `3373257` docs: mark Phase 4 published (ComfyUI-RealProductScene), note B3 registry pending
  - `cf83a13` Publish prep: rename to ComfyUI-RealProductScene, LICENSE holder → zeczec
  - `d4501f2` Phase 7: GPT-scene swap backend — align + light-wrap real product (live-verified)

## Where We're Going (Next Steps)
1. **使用者目視驗收**：開 <https://registry.comfy.org/nodes/comfyui-realproductscene> 看節點頁正常、publisher 是 `yorimi`；（選）在 ComfyUI Manager 搜 `RealProductScene` 確認可裝。
2. **repo/registry 品相（選做）**：GitHub Description/Topics、README 塞成品示意圖；registry `Icon`（現空，加一張 ≤800×400 PNG/SVG 到 `[tool.comfy] Icon` 更好看）。
3. **技術殘留軌（選做，沿 Phase 6/7）**：swap 細長 silhouette（帶/細跟）除抹+inpaint 兜底；manual 後端完全離線（合成搬 PIL、脫離 ComfyUI server）；背景光自動偵測。
4. **改版流程備忘**：任何節點更新→改 code→bump `pyproject.toml` version→push main→Action 自動重發 registry。
5. 使用者可能再丟新產品/場景壓測 swap 後端。

## Quick Start for Next Session
「接續 ai-product-scene-generator（GitHub repo 名 **ComfyUI-RealProductScene**、本地資料夾仍叫 ai-product-scene-generator）：V2 roadmap **全數里程碑完成並 live 驗證**——V1 + Phase 1–7 + Phase 4 發佈（GitHub repo 公開 + **ComfyUI Registry 上架**）。節點 live：<https://registry.comfy.org/nodes/comfyui-realproductscene>（`NodeStatusActive`、publisher `yorimi`、v1.0.0）。repo `main` HEAD 乾淨。發佈工具鏈已就位：Homebrew（`/opt/homebrew`）+ `gh` 2.96.0（認證 `yorimi-tamai`）+ repo secret `REGISTRY_ACCESS_TOKEN` + GitHub Action `publish_action.yml`（bump `pyproject.toml` version→push→自動重發 registry）。**剩下全是選做**：repo/registry 品相（Description/Topics/README 圖/registry Icon）、技術殘留軌（swap 細長物除抹+inpaint、manual 全離線、背景光自動偵測）。開發紀律照 PLAN.md。」
