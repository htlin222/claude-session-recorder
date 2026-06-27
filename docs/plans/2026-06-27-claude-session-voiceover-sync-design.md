# Claude session 影片的旁白同步設計（voice-leads-typing）

**日期**：2026-06-27
**範圍**：`engine/experimental/session-recorder/live/`（Roadmap 路徑 #4）+ overlay「session mode」（Roadmap #3）
**前置**：先讀 `engine/context/sync-model.md`（CLI-lesson 的 v1→v6 演化）。本設計把那套
loop-engineering 套到「拍 claude 自己」這條非決定性路徑上。

## 問題

現行 `live/` 路徑借用 `session-recorder` 的 **post-hoc** 旁白模型：先錄真實事件，再依
`session-timeline.jsonl` 的事件時間擺旁白。結果 `UserPromptSubmit` 永遠在「打完字之後」
才觸發，旁白只能尾隨動作 —— 正是 sync-model.md 記錄的 **v1 失敗（命令先跑、旁白後到）**。
觀看體驗差。

## 核心洞見：硬軸 vs 軟槽

一支 session 影片的時間軸分兩種區段：

```
  ┌─ 軟（tape 控制，可決定性加長）─┐  ┌─ 硬 ─┐  ┌─ 軟 ──┐
  │  ① prompt 前停頓   ② 打字節奏 │  │ ③思考 │  │ ④輸出後停頓 │
  └───────────────────────────┘  └──────┘  └──────────┘
        intro 語音住這              think      outro 語音住這
        （一定塞得下）             語音住這     （一定塞得下）
                                 ↑ claude 主導、可長可短、不可控
```

- **硬軸 = ③思考 gap**（Enter → Stop sentinel）：claude 主導、每次不同、唯一不可控。
- **軟槽 = ①prompt 前 / ②打字中 / ④輸出後**：由 tape 的 `Sleep`／打字延遲控制，要多長給多長。

**設計支點**：
- intro 語音住①，把停頓設 `>=` intro 語音長 → **語音必先行、決定性**。
- outro 語音住④，把 hold 設 `>=` outro 語音長 → **決定性塞得下**。
- think 語音住③硬軸 → **唯一需要「loop until align」真正出力**的地方。

→ 「先講解、動作釘句界」（v2/v4）的精神保留；差別是這裡**畫面不動、語音去 fit 真實
時間軸**，而非 CLI-lesson 的「語音釘畫面」（那邊輸出決定性，可反過來）。

### 核心原則：聲音先行，瞬間輸出「唸完才出現」

凡是**瞬間出現**的畫面內容（指令、flag、任何一次打完的 token —— 不限 claude），
一律 **先唸旁白、唸完該段才讓它出現**，不可邊打邊講或先打後講。理由：打字是瞬間的，
若先出現就等於「還沒解釋觀眾已看到」，旁白變成事後補充。

決定性作法（launch flag 即用此）：tape 每個 beat 排成
`Sleep(旁白時長) → Type(token) → Sleep(breath)`；overlay 把該段旁白 onset 放在槽起點，
token 落在 `onset + 旁白時長`（唸完的瞬間）。實證：唸「claude」時畫面是空 prompt，唸完
才出現 `claude`；唸「--model opus」時只見 `claude`，唸完才出現該 flag。

**與逐字打字的 prompt 區分**：prompt 是 demo 內容、逐字慢打可見，沿用「intro 先行 →
再打字」即可（intro 是解釋、prompt 本身是被示範的動作）。本原則只管**瞬間 token**。
未來若要逐 flag 高亮 prompt 內的 token，沿用同一 `Sleep(say) → Type(token)` 機制。

## 流程（使用者定義）：設計操作 → 實際執行 → 配旁白 → loop until align

```
①設計操作  作者寫 prompts + 每turn{intro,think,outro} 旁白 + tape 預埋 intro 停頓槽
②實際執行  vhs 錄 terminal.mp4  ‖  hooks 記 session-timeline.jsonl（真實時間軸）
③配旁白    依真實時間軸把每段語音 fit 進真實槽位（edge-tts 合成、量長、adelay+amix）
④loop until align  verify_sync（session 模式）gate → 不齊就自動調整 → 重驗，收斂
```

### loop 是雙層

- **內層（調內容，不重錄，便宜）**：think 語音塞不進真實 gap → **先改旁白內容**（把 think
  裁到能塞進 gap 的最長句界前綴、用自然語速重新合成）→ 重驗。**不要用 `atempo` 壓縮音檔** —
  那會讓 think 突然變快、跟正常語速的 intro/outro 一聽就突兀。
- **外層（調 tape，重錄）**：硬軸結構性太短（claude 秒回、think 槽 1s 但旁白要 6s）→
  加大 tape 的 intro `Sleep`／改寫短 think 句／改 prompt → 重錄 → 回 ③。

因為①②④是軟槽，內層幾乎總能解 intro/outro；外層只在硬軸出問題時才動。

## 元件與資料流

1. **旁白稿格式**（新）`script.json`：
   ```json
   { "turns": [ { "prompt": "...", "intro": "先請 Claude 寫…",
                  "think": "這裡會用 % 15 先判…", "outro": "測試通過，完成" } ] }
   ```
2. **`gen_session_tape.py`（改）**：讀 `script.json`；先用 edge-tts 量出每句 intro/outro 語音
   長度，把①停頓 `Sleep = intro_dur + lead`、④hold `Sleep = outro_dur + hold` 寫進 tape；
   仍逐字打字、`Wait+Screen /VHS_TURN_DONE_N/`。另輸出 **`plan.json`**：每 turn 的軟槽結構
   （intro_slot 起點/長、打字起點、Enter 時刻、hold 長）—— 這是 overlay 對齊的藍圖。
3. **錄製**：`vhs session.tape` → `terminal.mp4`；hooks → `session-timeline.jsonl`
   （真實秒數：每個 `UserPromptSubmit`、`PreToolUse`、`Stop`）。`Stop` 的時間即 sentinel 時刻。
4. **`session_overlay.py`（新）**：核心對齊器。輸入 `terminal.mp4 + plan.json +
   session-timeline.jsonl + 語音片段`。對每 turn：
   - intro 語音擺在 `plan.intro_slot.start`（決定性，必早於打字）。
   - think 語音擺在真實 `Enter→Stop` 區間起點；若語音比硬軸 gap 長 → 內層**裁短內容**
     （句界前綴）重新合成成自然語速，塞進 `gap - safety`；連第一句都塞不下才標記需重錄。
   - outro 語音擺在真實 `Stop` 之後（住軟槽④，必塞得下）。
   - 用 `adelay+amix`（沿用 build/overlay 慣例）組全域音軌；輸出 `.srt`、`timeline.json`。
   - **畫面不 freeze/trim**（與舊設計差異）—— 真實錄影原樣保留。
5. **`verify_sync.py`（擴）session 模式**：新 gate（見下）。

## verify gate（session 模式）

延伸現有 5 gate，新增/改寫：
1. **語音先行（新，核心）** — 每 turn `intro.onset < typing.onset`。違反 = FAIL。這條
   結構性保證「命令先跑」再也不會發生。
2. **think 落在硬軸內** — `Enter <= think.onset` 且 `think.onset + think.dur <= Stop + tol`。
   超出（裁到第一句後仍超 → claude 秒回）→ FAIL_FIXABLE（外層：改短 think 句或加大 prompt 重錄）。
3. **旁白沒溢出** — 沿用 v6 `min_gap`（每段語音在自己槽內講完）。
4. **成品長度 >= 旁白總長**（沿用）。
5. **最小間隔** — 任兩段相鄰旁白 clip 間隔 >= MIN_GAP（~0.5s）。只擋硬重疊不夠：
   0.4s 的間隔聽起來仍像「前句沒講完後句就上來」。開場改逐 flag 獨立 clip（非一段
   連讀）；放不下的收尾語（open outro）採 fit-or-drop：先裁短，窗口太小就略過，
   絕不壓到下一句。THINK_GUARD >= MIN_GAP 確保 think 與 outro 間也留得下一口氣。

## YAGNI（明確不做）

- 不做畫面 freeze/trim 對齊（改用真實時間軸 + loop）。
- 不做課程串接/montage（Roadmap 後話）。
- 不做思考 gap 的「智慧內容生成」—— think 句是預寫的，loop 只調**長度/語速**不調內容。

## 驗收

以 fizzbuzz 兩 turn demo 跑完整 pipeline：verify_sync session 模式 PASS，
人工觀看確認每個 prompt 都是「先聽到 intro、才看到打字」，think 旁白蓋在 spinner 上、
outro 蓋在結果上，全程無「命令先跑」。
