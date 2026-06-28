# Interactive AskUserQuestion in recordings — render + answer, VHS-visual Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development) to implement this plan task-by-task.

**Goal:** Make a recorded `claude` session that calls the **AskUserQuestion** tool answerable automatically — either INVISIBLY (deny + auto-answer, recording never hangs) or, for teaching, VISIBLY (the interactive selector renders on screen and a driver navigates to an option and presses Enter) — while keeping the exact current VHS visual. Build it step by step from a simple fixed-keystroke path up to a robust, adaptive background monitor that handles unknown questions.

**Architecture:** A PreToolUse hook on AskUserQuestion has two MODES (env `VHS_QUESTION_MODE`): `auto` (deny with the chosen answer in the reason — recording proceeds invisibly, never hangs; already shipped as `autoanswer_questions.py`) and `render` (ALLOW the selector to render, and write the question + options + chosen target to a signal file `pending_q.json`). In `render` mode two drivers pick the option ON SCREEN, both preserving VHS rendering:
- **VHS-scripted** (simple, known questions): the VHS tape `Wait+Screen`s for the selector footer, then sends `Down × (N-1)` + `Enter`. Pure VHS — exact visual.
- **tmux bg-monitor** (robust, unknown questions): `claude` runs inside a status-less tmux that VHS is *attached to and renders*; a background monitor reads `pending_q.json`, computes the keystrokes for the actual options, and `tmux send-keys` the selection. VHS still renders every frame (the question appears, the highlight moves, Enter fires).

The v6 pipeline gains a "question beat" so `author.py`/`panel.py` narrate the Q&A ("claude 需要澄清 → 我們選 Bash → 繼續").

**Tech Stack:** Python 3 (repo `.venv`), tmux, VHS, edge-tts, ffmpeg, Pillow. Tests: pytest. Validated spike findings live in this plan (the AskUserQuestion UI structure + `Down`/`Enter` navigation are confirmed working).

---

## Spike findings (confirmed — design against these)

The AskUserQuestion selector renders (Claude Code v2.1.195) as:
```
 ☐ <header>
<question text>
❯ 1. <option-1 label>
     <option-1 description>
  2. <option-2 label>
     <option-2 description>
  ...
  N+1. Type something.            <- auto-appended escape-hatch rows
  N+2. Chat about this
Enter to select · ↑/↓ to navigate · Esc to cancel
```
- **Highlight** starts on option **1**; the highlighted row is prefixed `❯ `, others `  `.
- **`Down`** moves the highlight; **`Enter`** selects and claude proceeds. To reach the model's option index `i` (1-based), send `Down × (i-1)` then `Enter`.
- **Detect "a question is showing"**: match the footer `↑/↓ to navigate` (stable, unique to a live selector). **Do NOT** match option words (they also appear in the echoed prompt → false positives before render).
- **Post-selection confirm**: the transcript/screen shows `User answered Claude's questions` then `→ <chosen label>`.
- The selector needs a moment to paint after the prompt (claude "thinks" first) — POLL for the footer before sending keys; never blind-sleep.
- Two synthetic rows (`Type something.` / `Chat about this`) are always appended after the model's options.

---

## Conventions

- Work dir: `engine/experimental/session-recorder/live/`. Tests in `live/tests/`. Run with `cd /Users/htlin/vhs-demo && .venv/bin/python -m pytest engine/experimental/session-recorder/live/tests/ -v`.
- Absolute paths in code. Commit after each task with the message in its final step + the two trailers (Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com> / Claude-Session: https://claude.ai/code/session_01GNWqH3arEQMozWxuL8YxXP).
- The existing `autoanswer_questions.py` (the `auto`/deny path) and its 6 tests already exist and pass — extend, don't break.

---

## Phase A — hook modes + signal file (the shared foundation)

### Task A1: `VHS_QUESTION_MODE` + `pending_q.json` in the hook

**Files:**
- Modify: `engine/experimental/session-recorder/live/autoanswer_questions.py`
- Test: `engine/experimental/session-recorder/live/tests/test_autoanswer.py` (extend)

**Step 1: Write failing tests**
```python
def test_render_mode_allows_and_signals(tmp_path, monkeypatch):
    monkeypatch.setenv("VHS_QUESTION_MODE", "render")
    monkeypatch.setenv("VHS_SIGNAL_DIR", str(tmp_path))
    out = aq.handle({"tool_input": Q["questions"] and {"questions": Q["questions"]}}, {})
    # render mode does NOT deny — it allows (so the selector shows)
    assert out is None or out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
    sig = tmp_path / "pending_q.json"
    assert sig.exists()
    rec = json.loads(sig.read_text())
    assert rec["target_index"] == 0                  # first option by default (1-based: option 1)
    assert rec["options"] == ["Python (hello.py)", "Bash (hello.sh)"]

def test_auto_mode_still_denies():
    out = aq.handle({"tool_input": {"questions": Q["questions"]}}, {})  # default mode
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
```

**Step 2: Implement** — refactor a pure `handle(data, answers, mode, signal_dir)` that:
- `mode == "auto"` (default): return the deny payload (current behaviour).
- `mode == "render"`: compute `target_index` (0-based into the MODEL's options) from the same override logic, write `{"questions":[...], "options":[...], "target_index": i, "target_label": ...}` to `<signal_dir>/pending_q.json`, and return an ALLOW (output `{"hookSpecificOutput": {"hookEventName":"PreToolUse","permissionDecision":"allow"}}` or empty → claude renders the selector). `mode` from `$VHS_QUESTION_MODE`, signal_dir from `$VHS_SIGNAL_DIR` (default the cwd/demo).
- Keep `choose_answers`/`_pick`/`deny_payload` intact; add `target_index_for(question, answers)` (pure) reused by both.

**Step 3: Run tests + commit** `feat(live): hook render-mode + pending_q.json signal for on-screen answering`.

---

## Phase B — VHS-scripted on-screen answering (simple path, exact visual)

### Task B1: keystroke planner (pure)

**Files:** Create `engine/experimental/session-recorder/live/qnav.py`; Test `tests/test_qnav.py`.

**Step 1: Failing test**
```python
import qnav
def test_keys_to_reach_option():
    assert qnav.keys_to_select(target_index=0, highlight=0) == ["Enter"]
    assert qnav.keys_to_select(target_index=1, highlight=0) == ["Down", "Enter"]
    assert qnav.keys_to_select(target_index=2, highlight=0) == ["Down", "Down", "Enter"]
def test_keys_handle_existing_highlight():
    assert qnav.keys_to_select(target_index=0, highlight=2) == ["Up", "Up", "Enter"]
```

**Step 2: Implement** `keys_to_select(target_index, highlight=0)` → `Down`/`Up` × delta + `Enter`. Pure.

**Step 3: Also add `FOOTER_RE = r"↑/↓ to navigate"` and `ANSWERED_RE = r"User answered Claude" + "'" + "s questions"` constants here (single source of truth for the patterns). Test they compile.**

**Step 4: Commit** `feat(live): qnav — selector keystroke planner + detection patterns`.

### Task B2: question beats in `gen_capture_tape.py`

**Files:** Modify `gen_capture_tape.py`; Test `tests/test_capture_tape.py` (extend).

A turn in `script.json` may declare an expected question:
```jsonc
{"prompt": "...", "intro": "...", "think": "...", "outro": "...",
 "question": {"answer_index": 1, "footer": "↑/↓ to navigate"}}
```

**Step 1: Failing test** — when a turn has `question`, the emitted tape, after the prompt's `Enter`, contains a `Wait+Screen@<turn_to>s /↑\/↓ to navigate/` then the `Down`×answer_index + `Enter` lines (from qnav) BEFORE the `VHS_TURN_DONE` wait:
```python
def test_question_turn_waits_and_selects(tmp_path):
    spec = {"launch": {...minimal...}, "turns": [{"prompt": "pick one", "question": {"answer_index": 1}}]}
    tape, plan = g.render(spec, demo=str(tmp_path), width=1200, height=1080, font_size=26, word_delay=220)
    assert "↑/↓ to navigate" in tape
    assert tape.index("Wait+Screen") < tape.index("Down") < tape.index("VHS_TURN_DONE_1")
    assert plan["turns"][0]["question"]["answer_index"] == 1
```

**Step 2: Implement** — in `render`, when a turn carries `question`, after `Enter` emit: a `Wait+Screen@{turn_to}s /↑\/↓ to navigate/` (selector appeared), a `Sleep` (let the viewer read the question), `Down`×answer_index, a `Sleep`, `Enter`, then the existing `Wait+Screen /VHS_TURN_DONE_i/`. Record the question in `capture.json`. Default `VHS_QUESTION_MODE=render` is set via the sandbox (Task B3) so the selector actually shows.

**Step 3: Commit** `feat(live): gen_capture_tape — question beats (wait for selector, navigate, select)`.

### Task B3: sandbox wires render-mode for question demos

**Files:** Modify `claude_sandbox.sh` (and/or `gen_capture_tape.py` tape `Env`).

The tape must run claude with `VHS_QUESTION_MODE=render` when the script has any question turn, so the hook allows the selector to render (instead of auto-denying). Emit `Env VHS_QUESTION_MODE "render"` + `Env VHS_SIGNAL_DIR "<demo>"` in the tape when any turn has `question`; otherwise leave the default `auto` (recordings stay hang-proof). Add a `render`-mode value test for the tape. **Commit** `feat(live): tape sets render-mode when a script declares question turns`.

### Task B4: end-to-end SIMPLE demo (real recording)

**Files:** Create `script.question.json` (a 1-2 turn script whose first turn elicits a known AskUserQuestion, `answer_index` set).

Run `run_v6.sh` on it. Acceptance:
- the recording COMPLETES (no hang),
- the filmstrip shows: claude renders the selector → the highlight moves to the chosen option → Enter → claude proceeds with that answer,
- `lint.py` passes.
Iterate prompt wording until claude reliably asks (use an explicit "use the AskUserQuestion tool to ask me whether …"). **Commit** the script + a short README note. This is the first robust milestone: a teaching demo where the question is visibly asked and answered, in the exact VHS visual.

---

## Phase C — narrate the Q&A (pipeline integration)

### Task C1: author + panel understand question beats

**Files:** Modify `author.py`, `panel.py`; Tests extend.

- `author.py`: a question turn's `think` narration rides the selector+selection window (the gap between submit and done now includes the question). The intro still leads typing; outro over the result. No new beat kind needed — the question is part of the turn's hard segment (the selector renders, gets answered, claude continues — all inside [submit, done]). Add a test that a question turn still satisfies the serialization invariant.
- `panel.py`: when a turn has a question, the panel shows a "詢問 / Question" row (the header + chosen answer) before the tool rows — sourced from `capture.json`'s question + `pending_q.json`'s chosen label. Pure `keyframe_times` test for the question row.

**Commit** `feat(live): narrate + panel the AskUserQuestion turn`.

### Task C2: full NARRATED simple demo

Re-author `script.question.json` with intro/think/outro that explain the Q&A ("這裡 claude 需要我們選語言 → 我們挑 Bash → 它接著寫 hello.sh"). Produce `session_panel.mp4`. Acceptance: lint PASS; the panel shows the Question row + answer; eyeball confirms voice ≈ the on-screen ask+select. **Commit** the narrated script.

---

## Phase D — robust adaptive bg-monitor (unknown questions, VHS-visual)

This generalizes B/C to questions we do NOT know ahead of time, while keeping VHS rendering. `claude` runs inside a status-less tmux; VHS is the attached client (renders every frame); a background monitor injects the adaptive selection via `tmux send-keys`, cued by the hook's `pending_q.json`.

### Task D1: selector parser (pure, tested against the spike capture)

**Files:** Create `qparse.py`; Test `tests/test_qparse.py` using the REAL captured screen text from the spike (embed it as a fixture).

**Step 1: Failing test** — `qparse.parse_selector(screen_text)` returns `{"showing": True, "header": "Language", "question": "...", "options": ["Python (hello.py)", "Bash (hello.sh)"], "highlight": 0}` from the captured UI; returns `{"showing": False}` for a non-question screen. It must EXCLUDE the synthetic `Type something.` / `Chat about this` rows from `options`.

**Step 2: Implement** — detect via `FOOTER_RE`; parse numbered `N.` rows with `❯`/`  ` prefix for highlight; stop options at the synthetic rows. Pure.

**Step 3: Commit** `feat(live): qparse — parse the AskUserQuestion selector from captured pane text`.

### Task D2: the bg-monitor (tmux read + inject)

**Files:** Create `qmonitor.py`; Test `tests/test_qmonitor.py` (pure decision core).

**Step 1: Failing test** — pure `decide_keystrokes(pending, parsed)`:
```python
def test_monitor_picks_target_from_signal_and_parse():
    pending = {"target_index": 1, "options": ["Python (hello.py)", "Bash (hello.sh)"]}
    parsed = {"showing": True, "options": ["Python (hello.py)", "Bash (hello.sh)"], "highlight": 0}
    assert qmonitor.decide_keystrokes(pending, parsed) == ["Down", "Enter"]
def test_monitor_reconciles_target_by_label_if_order_differs():
    pending = {"target_index": 1, "target_label": "Bash (hello.sh)", "options": ["Python (hello.py)", "Bash (hello.sh)"]}
    parsed = {"showing": True, "options": ["Bash (hello.sh)", "Python (hello.py)"], "highlight": 0}  # order flipped on screen
    assert qmonitor.decide_keystrokes(pending, parsed) == ["Enter"]  # target label is at on-screen index 0
```
(The monitor RECONCILES the target by LABEL against the actually-rendered order — robustness the static VHS path can't give.)

**Step 2: Implement** — `decide_keystrokes` (pure): find the target label's index in the PARSED on-screen options (fallback to `target_index`), then `qnav.keys_to_select(on_screen_index, parsed["highlight"])`. Plus the I/O `run(session, signal_dir, poll=0.2)` loop: poll `pending_q.json`; when present, poll `tmux capture-pane` until `parse_selector(...).showing`, decide, `tmux send-keys` each key (with small gaps), wait for the `ANSWERED_RE` confirmation, delete `pending_q.json`, continue. Guard with a max-wait so it never spins forever.

**Step 3: Commit** `feat(live): qmonitor — adaptive on-screen answering via tmux send-keys`.

### Task D3: VHS-renders-tmux capture path

**Files:** Create `gen_capture_tape.py` `--tmux` option (or a sibling `gen_tmux_tape.py`) + `run_v6_tmux.sh`.

The tape, in tmux mode, launches `tmux new-session -A -s vhsdemo 'claude <flags>'` (status off via a seeded `~/.tmux.conf` or `tmux set -g status off`), types the prompts into the attached client, and `Wait+Screen`s for the sentinel. The driver `run_v6_tmux.sh`: start the bg `qmonitor.py run vhsdemo <demo>` in the background BEFORE `vhs`, then run vhs (which renders the attached tmux), then stop the monitor. Verify statically (`bash -n`, shellcheck) — the real recording is Task D4.

**Commit** `feat(live): tmux capture path — VHS renders an attached tmux the monitor drives`.

### Task D4: end-to-end ROBUST demo (real recording, unknown question)

Use a prompt whose exact options we do NOT hardcode (e.g. "ask me a multiple-choice question about how to structure the file, then proceed"). Run `run_v6_tmux.sh`. Acceptance:
- recording completes; the selector renders; the monitor picks the target (by label) and selects it ON SCREEN; claude proceeds; lint PASS.
- Confirm via filmstrip the VISUAL is identical to the VHS path (Catppuccin terminal, panel) — the tmux is invisible (status off).
**Commit** the robust scenario script + README.

---

## Phase E — comprehensive hardening

### Task E1: multi-question + multiSelect
AskUserQuestion can carry several questions and `multiSelect`. Extend `qparse`/`qnav`/`qmonitor`: iterate questions (Tab/Enter between them — VERIFY the multi-question nav in a spike first), and for `multiSelect` toggle with `Space` before `Enter`. Tests for the keystroke sequences. **Commit**.

### Task E2: timeouts, fallbacks, and the safety net
- If the monitor can't parse/the selector never appears within `MAX_WAIT`, fall back to `Esc` or the first option, and `log()` it (never hang the recording).
- If `VHS_QUESTION_MODE` is unset, the `auto` deny path remains the default (hang-proof) — document that `render` is opt-in per demo.
- Tests for the fallback decision. **Commit**.

### Task E3: lint + ledger awareness
`lint.py`: a question turn must show the question was answered (the ledger/capture records `answer_label`); add a relation check. `author` records the chosen answer into the ledger meta for the panel. Test. **Commit**.

### Task E4: docs
Update `live/README.md`: the two modes (`auto` invisible vs `render` visible), the two render drivers (VHS-scripted vs tmux bg-monitor), the `script.json` `question` schema, `$VHS_QUESTION_MODE`/`$VHS_ANSWERS`/`$VHS_SIGNAL_DIR`, and when to use which. Add the spike's UI reference. **Commit** `docs(live): interactive AskUserQuestion handling`.

### Task E5: stress validation
Run all three demos (auto-invisible, simple-visible, robust-adaptive) end-to-end; confirm lint PASS, no hang, VHS visual intact, claude launched once each. Deliver the three `session_panel.mp4`. **Commit** a validation note.

---

## Done criteria
- A recorded claude session that calls AskUserQuestion never hangs (auto mode) AND can be answered visibly on screen (render mode), in the unchanged VHS visual.
- The bg-monitor adaptively answers UNKNOWN questions by reconciling the target against the rendered options.
- `pytest engine/experimental/session-recorder/live/tests/` green; lint passes on all three scenarios; three delivered videos.
