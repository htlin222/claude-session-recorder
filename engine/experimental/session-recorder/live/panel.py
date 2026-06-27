#!/usr/bin/env python3
"""panel.py — v6 right-side explainshell panel, TIMED FROM THE LEDGER.

v5's session_panel.py re-derived per-turn windows from the video + a separate
session_sync.json, which could disagree with the terminal stage by a frame (the
"畫音亂套" desync bug class). v6 fixes this structurally: EVERY keyframe time the
panel uses comes from the SAME `ledger.json` that splice reconciled and overlay
muxed against. So left-terminal == right-panel == narration by construction.

The timeline JSONL (the hook log) is read ONLY to LABEL tool events — never for
timing. A tool event's wall-clock can't be mapped to video time directly (it
drifts), so each PreToolUse is placed into its turn's HARD output window by its
wall-clock fraction of the turn (the window itself comes from the ledger).

What the panel shows (same as v5):
  * LAUNCH phase -> the `claude <flags>` command dissected, each flag revealed
                    when its launch_flag beat's panel.switch_at fires.
  * each TURN    -> a header (at the turn's intro beat panel.switch_at), the
                    turn's tool actions (Write / Edit / Bash …) each appearing at
                    the moment it happened (mapped into the hard window), then the
                    conclusion at the turn's hard out-end (= done in output time).

Out: <demo>/session_panel.mp4  (1920x1080, terminal + panel + narration).
"""

import argparse
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

FF = "/opt/homebrew/bin/ffmpeg"
CW, H, TERM_W = 1920, 1080, 1200
PANEL_W = CW - TERM_W  # 720
# one font for the whole panel (Hiragino renders both Latin and CJK) — keeps the
# panel visually unified; the real terminal on the left stays monospaced.
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
MONO = CJK
BG = (24, 24, 37)
TEXT = (205, 214, 244)
MUTED = (127, 132, 156)
HL = (49, 50, 68)
ROLE = {
    "ord": (166, 227, 161),
    "star": (250, 179, 135),
    "path": (203, 166, 247),
    "blue": (137, 180, 250),
    "yellow": (249, 226, 175),
}
PAD = 42


def F(path, sz):
    return ImageFont.truetype(path, sz)


def _new():
    img = Image.new("RGB", (PANEL_W, H), BG)
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (0, H)], fill=ROLE["path"], width=3)  # left divider
    return img, d


def _title(d, text, sub=None):
    d.text((PAD, 44), text, font=F(CJK, 30), fill=TEXT)
    d.line([(PAD, 92), (PANEL_W - PAD, 92)], fill=(52, 54, 66), width=2)
    if sub:
        d.text((PAD, 100), sub, font=F(CJK, 20), fill=MUTED)


def launch_panel(command, flags, revealed):
    """`claude <flags>` with the first `revealed` flags shown + annotated. The
    command echo wraps within the panel and the annotation boxes auto-size to
    their note text, so nothing overflows."""
    img, d = _new()
    _title(d, "啟動 Claude Code", "claude 指令與旗標")
    fc, fa = F(MONO, 23), F(MONO, 21)
    colours = [ROLE["ord"], ROLE["star"], ROLE["blue"], ROLE["yellow"]]
    rmax = PANEL_W - PAD
    # echoed command, colouring the revealed flag args; wrap when it would overflow
    y = 152
    d.text((PAD, y), "$ claude", font=fc, fill=TEXT)
    x = PAD + d.textlength("$ claude ", font=fc)
    for i, f in enumerate(flags[:revealed]):
        col, seg = colours[i % len(colours)], f["arg"]
        if x + d.textlength(seg, font=fa) > rmax:
            y += 38
            x = PAD + 24
        d.text((x, y + 1), seg, font=fa, fill=col)
        w = d.textlength(seg, font=fa)
        d.line([(x, y + 30), (x + w, y + 30)], fill=col, width=3)  # short stub
        x += w + d.textlength("  ", font=fa)
    # annotations: a colour-barred box per revealed flag, height fits the note
    ay = y + 76
    for i, f in enumerate(flags[:revealed]):
        col = colours[i % len(colours)]
        note = f.get("note") or f.get("say", "")
        lines = _wrap(d, note, F(CJK, 20), rmax - PAD - 24)[:3]
        bh = 44 + len(lines) * 28
        d.rectangle([PAD, ay, rmax, ay + bh], fill=HL)
        d.line([(PAD, ay), (PAD, ay + bh)], fill=col, width=5)
        d.text((PAD + 20, ay + 10), f["arg"], font=F(MONO, 19), fill=col)
        for li, ln in enumerate(lines):
            d.text((PAD + 20, ay + 42 + li * 28), ln, font=F(CJK, 20), fill=TEXT)
        ay += bh + 18
    return img


# shape per tool (drawn with PIL — unicode glyphs render as tofu in these fonts)
TOOL = {
    "Write": ("sq", "建立檔案"),
    "Edit": ("sq", "修改檔案"),
    "Read": ("ring", "讀取"),
    "Bash": ("dot", "執行指令"),
    "Grep": ("ring", "搜尋"),
    "Glob": ("ring", "找檔案"),
    "Task": ("dia", "子代理"),
    "TodoWrite": ("sq", "更新待辦"),
}


def draw_icon(d, x, y, shape, col, sz=20):
    if shape == "sq":
        d.rectangle([x, y, x + sz, y + sz], fill=col)
    elif shape == "ring":
        d.ellipse([x, y, x + sz, y + sz], outline=col, width=3)
    elif shape == "dia":
        h = sz / 2
        d.polygon([(x + h, y), (x + sz, y + h), (x + h, y + sz), (x, y + h)], fill=col)
    elif shape == "check":  # a tick: two strokes
        d.line([(x + 2, y + sz * 0.55), (x + sz * 0.4, y + sz - 2)], fill=col, width=4)
        d.line([(x + sz * 0.4, y + sz - 2), (x + sz, y + 1)], fill=col, width=4)
    else:  # dot
        d.ellipse([x, y, x + sz, y + sz], fill=col)


def turn_panel(num, total, prompt, events, revealed, conclusion=None):
    """A turn's action list: rows appear as claude performs each tool call."""
    img, d = _new()
    short = prompt if len(prompt) < 26 else prompt[:25] + "…"
    _title(d, f"第 {num} / {total} 輪", short)  # title y44, divider y92, sub y100
    d.text((PAD, 148), "Claude 的動作", font=F(CJK, 21), fill=MUTED)
    y = 188
    if not events:  # a pure-text turn (no tool calls)
        d.text((PAD, y), "·", font=F(MONO, 24), fill=MUTED)
        d.text((PAD + 40, y + 2), "Claude 直接以文字回覆", font=F(CJK, 20), fill=MUTED)
    for ev in events[:revealed]:
        shape, verb = TOOL.get(ev["tool"], ("dot", ev["tool"]))
        col = ROLE["star"] if ev["tool"] in ("Bash",) else ROLE["ord"]
        draw_icon(d, PAD, y + 4, shape, col)
        d.text((PAD + 40, y), ev["tool"], font=F(MONO, 21), fill=col)
        d.text((PAD + 40, y + 30), verb, font=F(CJK, 17), fill=MUTED)
        tgt = ev.get("target", "")
        for li, ln in enumerate(_wrap(d, tgt, F(MONO, 18), PANEL_W - 2 * PAD - 60)[:1]):
            d.text((PAD + 200, y + 4), ln, font=F(MONO, 18), fill=TEXT)
        y += 76
    if conclusion:
        cy = H - 240
        d.line([(PAD, cy), (PANEL_W - PAD, cy)], fill=(52, 54, 66), width=2)
        d.text((PAD, cy + 16), "完成", font=F(CJK, 22), fill=ROLE["ord"])
        for li, ln in enumerate(
            _wrap(d, conclusion, F(CJK, 20), PANEL_W - 2 * PAD)[:5]
        ):
            d.text((PAD, cy + 52 + li * 30), ln, font=F(CJK, 20), fill=TEXT)
    return img


def _wrap(d, text, font, maxw):
    out, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=font) > maxw and cur:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def last_session(timeline):
    rows = [json.loads(l) for l in open(timeline, encoding="utf-8") if l.strip()]
    starts = [i for i, r in enumerate(rows) if r["event"] == "SessionStart"]
    return rows[starts[-1] :] if starts else rows


# ---------------------------------------------------------------------------
# timing — derived PURELY from the ledger
# ---------------------------------------------------------------------------
def _is_flag_beat(b):
    """A launch_flag beat that actually reveals a flag (vs the launch intro/outro
    narration, which authors as the same kind). Use the synthesized clip name:
    flags are `open_flag*`, the framing beats are `open_intro`/`open_outro`. With
    no voice info (e.g. a bare unit fixture), treat it as a flag reveal."""
    v = b.get("voice")
    if not v or not v.get("clip"):
        return True
    return "flag" in os.path.basename(v["clip"])


def keyframe_times(led):
    """PURE: walk the ledger's beats + meta.segments and emit an ordered list of
    keyframe dicts derivable WITHOUT the timeline:

      {"t": <output sec>, "type": "launch",      "reveal": <cumulative flags>}
      {"t": <output sec>, "type": "turn_header", "turn": <idx>}
      {"t": <output sec>, "type": "conclusion",  "turn": <idx>}

    Tool events need the timeline to label them and the hard-window mapping to
    place them, so they are merged in `main()`, not here.
    """
    beats = led["beats"]
    segs = led["meta"]["segments"]
    keys = []

    # launch: each launch_flag beat's panel.switch_at reveals one more flag.
    launch_beats = sorted(
        (b for b in beats if b["kind"] == "launch_flag" and not b.get("drop")),
        key=lambda b: b["panel"]["switch_at"],
    )
    revealed = 0
    for b in launch_beats:
        if _is_flag_beat(b):
            revealed += 1
        keys.append({"t": b["panel"]["switch_at"], "type": "launch", "reveal": revealed})

    # per-turn header: the turn's intro beat panel.switch_at.
    for b in beats:
        if b["kind"] == "intro" and not b.get("drop"):
            keys.append({"t": b["panel"]["switch_at"], "type": "turn_header",
                         "turn": b["turn_idx"]})

    # conclusion: each turn's hard segment out-end (= done in output time).
    for s in segs:
        if s.get("kind") == "hard":
            keys.append({"t": s["out"][1], "type": "conclusion", "turn": s["turn_idx"]})

    keys.sort(key=lambda k: k["t"])
    return keys


def _tool_events(led, rows, turn_idx, ups_wall, stop_wall):
    """Label + place the PreToolUse events of one turn. Labels come from the
    timeline; the OUTPUT time of each event is its wall-clock FRACTION of the turn
    mapped into the turn's HARD output window — both window edges from the ledger.
    """
    hard = next(s for s in led["meta"]["segments"]
                if s.get("kind") == "hard" and s["turn_idx"] == turn_idx)
    submit_out = hard["out"][0] + (hard.get("submit", hard["raw"][0]) - hard["raw"][0])
    done_out = hard["out"][1]
    span_w = max(0.1, stop_wall - ups_wall)
    out = []
    for r in rows:
        if r["event"] != "PreToolUse" or not (ups_wall < r["t"] <= stop_wall):
            continue
        frac = min(1.0, max(0.0, (r["t"] - ups_wall) / span_w))
        ev_out = submit_out + frac * (done_out - submit_out)
        detail = r.get("detail", "")
        tool = detail.split(" ", 1)[0]
        target = detail.split(" ", 1)[1] if " " in detail else ""
        target = os.path.basename(target) if "/" in target else target[:36]
        out.append({"t": round(ev_out, 3), "type": "tool", "turn": turn_idx,
                    "tool": tool, "target": target})
    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--demo", required=True)
    ap.add_argument("--timeline", default=None)
    args = ap.parse_args()
    demo = os.path.abspath(args.demo)
    timeline = args.timeline or os.path.join(demo, "session-timeline.jsonl")

    led = json.load(open(os.path.join(demo, "ledger.json"), encoding="utf-8"))
    cap = json.load(open(os.path.join(demo, "capture.json"), encoding="utf-8"))
    lc = cap.get("launch", {})
    cmd = lc.get("base", "claude")
    flags = lc.get("flags", [])
    turns = cap["turns"]

    rows = last_session(timeline)
    ups = [r for r in rows if r["event"] == "UserPromptSubmit"]
    stop = [r for r in rows if r["event"] == "Stop"]

    # ledger-derived keyframes (launch reveals, turn headers, conclusions) …
    keys = keyframe_times(led)
    # … plus the timeline tool events mapped into each turn's hard output window.
    for ti in range(len(turns)):
        if ti >= len(ups) or ti >= len(stop):
            break
        keys.extend(_tool_events(led, rows, ti, ups[ti]["t"], stop[ti]["t"]))
    keys.sort(key=lambda k: k["t"])

    # conclusion text: the turn's Stop message (first line), else the ledger outro.
    outro_txt = {b["turn_idx"]: b.get("text", "")
                 for b in led["beats"] if b["kind"] == "outro"}

    def conclusion_text(ti):
        m = stop[ti].get("message", "") if ti < len(stop) else ""
        return (m.split("\n")[0] if m else outro_txt.get(ti, ""))[:80]

    # render each keyframe cumulatively to a PNG (as v5 does)
    pdir = os.path.join(demo, "_panels")
    os.makedirs(pdir, exist_ok=True)
    turn_events = {ti: [] for ti in range(len(turns))}
    segs = []
    for idx, k in enumerate(keys):
        if k["type"] == "launch":
            img = launch_panel(cmd, flags, min(k["reveal"], len(flags)))
        else:
            ti = k["turn"]
            if k["type"] == "tool":
                turn_events[ti].append({"tool": k["tool"], "target": k["target"]})
            concl = conclusion_text(ti) if k["type"] == "conclusion" else None
            img = turn_panel(ti + 1, len(turns), turns[ti]["prompt"],
                             turn_events[ti], len(turn_events[ti]), concl)
        p = os.path.join(pdir, f"p{idx:03d}.png")
        img.save(p)
        segs.append((p, k["t"]))

    # build the panel video (each png held until the next keyframe)
    vtot = led["meta"]["vtot_out"]
    lst = os.path.join(pdir, "panels.txt")
    with open(lst, "w") as f:
        blank = os.path.join(pdir, "blank.png")
        _new()[0].save(blank)
        f.write(f"file '{blank}'\nduration {segs[0][1]:.3f}\n")
        for i, (p, t) in enumerate(segs):
            end = segs[i + 1][1] if i + 1 < len(segs) else vtot
            f.write(f"file '{p}'\nduration {max(0.05, end - t):.3f}\n")
        f.write(f"file '{segs[-1][0]}'\n")
    panel_mp4 = os.path.join(pdir, "panel.mp4")
    subprocess.run(
        [
            FF,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            lst,
            "-r",
            "25",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "20",
            "-vsync",
            "cfr",
            "-t",
            f"{vtot:.3f}",          # the concat's trailing-repeat frame overshoots
            panel_mp4,              # under CFR; cap the panel at the ledger total
        ],
        check=True,
        capture_output=True,
    )

    # composite: terminal (1200) left + panel (720) right; audio from session.mp4
    term = os.path.join(demo, "terminal.mp4")
    audio_src = os.path.join(demo, "session.mp4")
    out = os.path.join(demo, "session_panel.mp4")
    subprocess.run(
        [
            FF,
            "-y",
            "-i",
            term,
            "-i",
            panel_mp4,
            "-i",
            audio_src,
            "-filter_complex",
            f"[0:v]scale={TERM_W}:-1,pad={TERM_W}:{H}:0:(oh-ih)/2:color=0x181825[L];"
            f"[1:v]scale={PANEL_W}:{H}[R];[L][R]hstack=inputs=2[v]",
            "-map",
            "[v]",
            "-map",
            "2:a",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{vtot:.3f}",          # end exactly with the terminal+audio (no dead tail)
            out,
        ],
        check=True,
        capture_output=True,
    )
    print(f"wrote {out}  ({len(segs)} panel keyframes)")


if __name__ == "__main__":
    main()
