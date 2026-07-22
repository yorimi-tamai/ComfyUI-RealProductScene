# Handoff — ai-product-scene-generator｜V2通用管線｜Phase4發佈公開repo｜#1 — 2026-07-22 12:07

> 檔案: `ai-product-scene-generator｜V2通用管線｜Phase4發佈公開repo｜#1｜2026-07-22_12-07.md`
> 前一份同單元 handoff: （無、這是「Phase4發佈公開repo」子單元第一份；相關前身見「…V2通用管線｜ComfyUI節點包｜#1…」＝節點包建置，本份是它的對外發佈收尾）

## The Goal
主線 Phase 1–7 已全完成，回頭把當初順延的 **Phase 4 發佈收尾**（roadmap「別條軌 B」）做掉：把 ComfyUI 節點包正式公開到 GitHub，讓其他 ComfyUI 使用者 git-clone 裝來用。

## 本次推進（This Session's Progress）
- **repo 正式公開上線**：<https://github.com/yorimi-tamai/ComfyUI-RealProductScene>（個人帳號 yorimi-tamai、Public）。
- **B1 LICENSE 版權人** → `Copyright (c) 2026 zeczec`（原為 `ai-product-scene-generator contributors`）。
- **B2 專案改名** `ai-product-scene-generator` → `ComfyUI-RealProductScene`（合 ComfyUI registry `ComfyUI-` 慣例、點出「真實產品刷進場景」）；6 處舊名一次改齊：README 標題 / 目錄樹 / clone 指令（連真實網址）、根 `__init__.py`、`comfyui_nodes/__init__.py`、`requirements.txt` 標頭。
- **發佈前體檢通過**：62 tracked 檔、無 secret/金鑰（掃出的兩個 match 只是撞到 PNG 二進位）、`.DS_Store` 未進版控、history 乾淨（size-pack 0）；唯一 binary 是 `tests/fixtures/phase3-surface/` 9 張測試背景圖（AI 生成、無真實產品/使用者資產，公開 OK）。
- **`.gitignore` 加 `outputs/**/*.html`**：擋掉 `outputs/phase{3,5}_validation/report.html`（引用的 PNG 已被 gitignore → 傳上去只會是壞掉的報告）。
- push 成功並確認：遠端 `main` == 本機 HEAD `cf83a13`，tracking `main...origin/main` 已建立。

## Where We Are
- **repo 現況**：`ComfyUI-RealProductScene` 公開、`main` 分支、HEAD `cf83a13`，working tree 乾淨（全 commit）。
- **內容**：CLI（`scripts/generate.py` 三後端 comfyui/manual/swap）+ ComfyUI 節點包（`comfyui_nodes/` 兩顆節點 A/B）+ 範例 workflow + 測試 + plans/ + handoff-archive/ 全在 repo 內。
- **認證**：本機原本無 GitHub 認證（無 SSH key、keychain 無 github.com 憑證），改用使用者自建的 **classic PAT（`repo` scope）** 在自己的 Terminal 手動 push；PAT 已存進 macOS osxkeychain，之後 push 免再輸入。
- **remote**：`origin` = `https://github.com/yorimi-tamai/ComfyUI-RealProductScene.git`（HTTPS）。
- **B3 registry 未做**：ComfyUI Manager registry 上架照 phase4 決策 #1 仍為「後續獨立里程碑」，本輪未啟動。

## What We Tried

| Approach | Result | Status |
|---|---|---|
| `git add -A` 一次暫存 | 誤把 `outputs/*_validation/report.html` 吞進來（gitignore 只擋圖不擋 html） | 🟡 發現問題 |
| 撤下 report.html + `.gitignore` 加 `outputs/**/*.html` | 壞報告不外流、暫存區乾淨剩 6 檔 | ✅ kept |
| `git push` HTTPS（我這端環境跑） | `could not read Username … Device not configured` — 環境無法互動輸入帳密 | ❌ 此環境不可行 |
| 查本機認證：credential.helper / SSH key / ssh -T github | osxkeychain 有設但無 github.com 憑證；無 SSH pub key；`ssh -T git@github.com` → Permission denied (publickey) | ❌ 無現成認證 |
| 改由使用者在自己 Terminal 手動 push + classic PAT | push 成功、遠端 main == cf83a13、tracking 建立 | ✅ kept |

## Key Decisions
- **repo 名 `ComfyUI-RealProductScene`**：選它、拒使用者一度給的 `yoriwork`（像個人 catch-all 倉、不描述用途）；理由：合 registry `ComfyUI-` 慣例、點出「真實產品」核心，且會烙進 clone 網址/registry 故要一次定對。
- **開在個人帳號、非 zeczec org**：使用者選個人帳號。
- **版權人寫 `zeczec`（非個人 handle / 非公司全名）**：使用者選團隊名。
- **建 repo 用網頁、非裝 gh**：使用者選「先在網頁建空 repo 給網址」；建時不勾 README/.gitignore/license（repo 已有、避免衝突）。
- **push 認證用 classic PAT、非裝 gh / 非 SSH**：走路 A（自己 Terminal 手動 push）；我依安全規則不代輸入 token。
- **B3 registry 本輪不做**：沿原 phase4 決策當後續里程碑；且需 gh CLI（未裝）+ 開 PR。

## User Feedback / Preferences
- 安全：token/金鑰類不代輸入 —— 使用者自己在 Terminal 貼 PAT，我只確認 push 結果，不碰 token。
- 對「classic PAT 是什麼」不熟 → 需要一步步教（產 token 流程、`repo` scope、貼進 Terminal 而非貼給 AI）。
- 命名一度想用 `yoriwork`，經提醒後接受更描述性的專案名（願意被拉回方向）。
- 沿用「收斂點主動提醒 handoff、點頭才跑」的節奏。
- 中途出現一次疑似手滑貼上無關路徑（`/Users/yoriwork/Desktop/.tmp.driveupload/...`）→ 未去開它、拉回 push 主線。

## Git State
- Branch: `main`
- Uncommitted: 無（working tree 乾淨；`outputs/phase{3,5}_validation/` 已由 .gitignore 忽略）
- Last commits:
  - `cf83a13` Publish prep: rename to ComfyUI-RealProductScene, LICENSE holder → zeczec
  - `d4501f2` Phase 7: GPT-scene swap backend — align + light-wrap real product (live-verified)
  - `041d85c` Phase 6: bring-your-own-background / multi-backend (live-verified)
  - `c3ef7ae` Phase 5 complete: composite realism polish (live-verified)
  - `0bb97f8` Phase 3 complete: depth-based surface auto-detection + manual override

## Where We're Going (Next Steps)
1. **目視驗收 repo 頁面**（使用者待辦）：GitHub 上 README 是否正常渲染、標題為 `ComfyUI-RealProductScene`、LICENSE 分頁顯示 MIT + zeczec。
2. **B3 — ComfyUI Manager registry 上架**（發佈最後一哩，需外部動作）：需裝 `gh`（目前未裝，可 `brew install gh && gh auth login` 走瀏覽器 OAuth）、依 Comfy registry 規範補 metadata、對 registry 開 PR + 過審核。是獨立里程碑。
3. **repo 品相打磨（選做）**：GitHub repo Description/Topics、加一張成品示意圖到 README、About 區連結。
4. **殘留技術軌（沿 Phase 7/6 遺留）**：swap 細長物除抹+inpaint 兜底；manual 後端完全離線（合成搬 PIL）；背景光自動偵測。
5. 使用者可能再丟新產品/場景壓測 swap。

## Quick Start for Next Session
「接續 ai-product-scene-generator（GitHub 上已改名 **ComfyUI-RealProductScene**）：V2 roadmap V1 + Phase 1–7 全完成 live 驗證，且 Phase 4 節點包已**公開發佈**到 <https://github.com/yorimi-tamai/ComfyUI-RealProductScene>（個人帳號、Public、`main` HEAD `cf83a13`、working tree 乾淨）。本地資料夾仍叫 `ai-product-scene-generator`（只有 repo/pack 名改了）。發佈認證＝使用者自建 classic PAT（`repo` scope）已存 osxkeychain，push 免再輸入；remote origin 為 HTTPS。**發佈剩最後一哩 B3＝ComfyUI Manager registry 上架**（需裝 gh + 開 PR + 過審核，未做）。其他發佈品相（repo Description/Topics/README 示意圖）與技術殘留（swap 細長物除抹+inpaint、manual 全離線、背景光自動偵測）為選做。開發紀律照 PLAN.md。」
