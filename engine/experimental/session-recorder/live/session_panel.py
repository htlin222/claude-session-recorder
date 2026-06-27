#!/usr/bin/env python3
"""session_panel.py — Roadmap #3 "session mode": composite the filmed claude
session (left, 1200px) with an explainshell-style panel (right, 720px).

The panel shows what the subtitles don't (the three-layer rule: voice = why,
subtitles = synced text, panel = structure):
  * LAUNCH phase  -> the `claude <flags>` command dissected, each flag revealed
                     as it is typed (appear-on-type), with a hand-written note.
  * each TURN     -> the actions claude took, from the hook timeline (Write /
                     Edit / Bash …), each row appearing at the moment it happened,
                     then the Stop conclusion.

Timing comes from session_sync.json (launch beat reveals, per-turn typing/submit/
stop in video time) + the hook timeline. A tool event's video time is
`submit_i + (event_wall - UserPromptSubmit_i_wall)` (after Enter, wall == video).

Prereq: run session_overlay.py first (writes session_sync.json + session.mp4 with
the narration track; we reuse its audio). Render the terminal at 1200x1080
(`gen_session_tape.py --width 1200 --height 1080`). Needs Pillow + ffmpeg.

Out: <demo>/session_panel.mp4  (1920x1080, terminal + panel + narration).
"""
import argparse
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

FF = "/opt/homebrew/bin/ffmpeg"
CW, H, TERM_W = 1920, 1080, 1200
PANEL_W = CW - TERM_W                       # 720
MONO = "/System/Library/Fonts/Menlo.ttc"
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
BG = (24, 24, 37)
TEXT = (205, 214, 244)
MUTED = (127, 132, 156)
HL = (49, 50, 68)
ROLE = {"ord": (166, 227, 161), "star": (250, 179, 135), "path": (203, 166, 247),
        "blue": (137, 180, 250), "yellow": (249, 226, 175)}
PAD = 42


def F(path, sz):
    return ImageFont.truetype(path, sz)


def _new():
    img = Image.new("RGB", (PANEL_W, H), BG)
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (0, H)], fill=ROLE["path"], width=3)     # left divider
    return img, d


def _title(d, text, sub=None):
    d.text((PAD, 44), text, font=F(CJK, 30), fill=TEXT)
    d.line([(PAD, 92), (PANEL_W - PAD, 92)], fill=(52, 54, 66), width=2)
    if sub:
        d.text((PAD, 100), sub, font=F(CJK, 20), fill=MUTED)


def launch_panel(command, flags, revealed):
    """`claude <flags>` with the first `revealed` flags shown + annotated."""
    img, d = _new()
    _title(d, "啟動 Claude Code", "claude 指令與旗標")
    # echoed command, colouring the revealed flag args
    y = 150
    d.text((PAD, y), "$ claude", font=F(MONO, 24), fill=TEXT)
    x = PAD + d.textlength("$ claude ", font=F(MONO, 24))
    colours = [ROLE["ord"], ROLE["star"], ROLE["blue"], ROLE["yellow"]]
    for i, f in enumerate(flags[:revealed]):
        col = colours[i % len(colours)]
        seg = f["arg"]
        if x + d.textlength(seg + " ", font=F(MONO, 22)) > PANEL_W - PAD:
            y += 36; x = PAD + 24
        d.text((x, y + 2), seg, font=F(MONO, 22), fill=col)
        d.line([(x, y + 32), (x + d.textlength(seg, font=F(MONO, 22)), y + 32)],
               fill=col, width=3)                            # short stub
        x += d.textlength(seg + "  ", font=F(MONO, 22))
    # annotations, one row per revealed flag (colour-matched left bar + label)
    ay = y + 84
    for i, f in enumerate(flags[:revealed]):
        col = colours[i % len(colours)]
        d.rectangle([PAD, ay, PANEL_W - PAD, ay + 78], fill=HL)
        d.line([(PAD, ay), (PAD, ay + 78)], fill=col, width=5)
        d.text((PAD + 20, ay + 10), f["arg"], font=F(MONO, 20), fill=col)
        note = f.get("note") or f.get("say", "")
        for li, ln in enumerate(_wrap(d, note, F(CJK, 20), PANEL_W - 2 * PAD - 40)[:2]):
            d.text((PAD + 20, ay + 40 + li * 26), ln, font=F(CJK, 20), fill=TEXT)
        ay += 98
    return img


TOOL = {"Write": ("✎", "建立檔案"), "Edit": ("✎", "修改檔案"), "Read": ("▢", "讀取"),
        "Bash": ("⚙", "執行指令"), "Grep": ("⌕", "搜尋"), "Glob": ("⌕", "找檔案"),
        "Task": ("⌗", "子代理"), "TodoWrite": ("☑", "更新待辦")}


def turn_panel(num, total, prompt, events, revealed, conclusion=None):
    """A turn's action list: rows appear as claude performs each tool call."""
    img, d = _new()
    short = prompt if len(prompt) < 26 else prompt[:25] + "…"
    _title(d, f"第 {num} / {total} 輪", short)        # title y44, divider y92, sub y100
    d.text((PAD, 148), "Claude 的動作", font=F(CJK, 21), fill=MUTED)
    y = 188
    if not events:                       # a pure-text turn (no tool calls)
        d.text((PAD, y), "·", font=F(MONO, 24), fill=MUTED)
        d.text((PAD + 40, y + 2), "Claude 直接以文字回覆", font=F(CJK, 20), fill=MUTED)
    for ev in events[:revealed]:
        icon, verb = TOOL.get(ev["tool"], ("•", ev["tool"]))
        col = ROLE["star"] if ev["tool"] in ("Bash",) else ROLE["ord"]
        d.text((PAD, y), icon, font=F(CJK, 24), fill=col)
        d.text((PAD + 40, y), ev["tool"], font=F(MONO, 21), fill=col)
        d.text((PAD + 40, y + 30), verb, font=F(CJK, 17), fill=MUTED)
        tgt = ev.get("target", "")
        for li, ln in enumerate(_wrap(d, tgt, F(MONO, 18), PANEL_W - 2 * PAD - 60)[:1]):
            d.text((PAD + 200, y + 4), ln, font=F(MONO, 18), fill=TEXT)
        y += 76
    if conclusion:
        cy = H - 240
        d.line([(PAD, cy), (PANEL_W - PAD, cy)], fill=(52, 54, 66), width=2)
        d.text((PAD, cy + 16), "✓ 完成", font=F(CJK, 22), fill=ROLE["ord"])
        for li, ln in enumerate(_wrap(d, conclusion, F(CJK, 20), PANEL_W - 2 * PAD)[:5]):
            d.text((PAD, cy + 52 + li * 30), ln, font=F(CJK, 20), fill=TEXT)
    return img


def _wrap(d, text, font, maxw):
    out, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=font) > maxw and cur:
            out.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def last_session(timeline):
    rows = [json.loads(l) for l in open(timeline, encoding="utf-8") if l.strip()]
    starts = [i for i, r in enumerate(rows) if r["event"] == "SessionStart"]
    return rows[starts[-1]:] if starts else rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", required=True)
    ap.add_argument("--timeline", default=None)
    args = ap.parse_args()
    demo = os.path.abspath(args.demo)
    here = os.path.dirname(os.path.abspath(__file__))
    timeline = args.timeline or os.path.join(os.path.dirname(here), "session-timeline.jsonl")
    plan = json.load(open(os.path.join(demo, "plan.json"), encoding="utf-8"))
    sync = json.load(open(os.path.join(demo, "session_sync.json"), encoding="utf-8"))
    rows = last_session(timeline)
    ups = [r for r in rows if r["event"] == "UserPromptSubmit"]
    stop = [r for r in rows if r["event"] == "Stop"]
    flags = plan["open"]["flags"] if "flags" in plan.get("open", {}) else \
        [{"arg": b["token"], "say": b["text"]} for b in plan["open"]["beats"][1:]]
    cmd = plan["open"].get("command", "")
    turns = plan["turns"]
    nfb = len(plan["open"]["beats"])              # beats incl base

    # ---- panel keyframes: (video_time, PIL image) ----
    keys = []
    pdir = os.path.join(demo, "_panels")
    os.makedirs(pdir, exist_ok=True)
    # launch: reveal a flag each time its token appears (beat onset + dur)
    beats = sync["open_beats"]
    for k in range(1, len(plan["open"]["beats"])):          # skip base (k=0)
        b = plan["open"]["beats"][k]
        onset = next((s["onset"] for s in beats if s["text"] == b["text"]), None)
        if onset is None:
            continue
        keys.append((round(onset + b["dur"], 3), ("launch", k)))   # flag appears
    # turns: header when the prompt is submitted; each tool event mapped into the
    # DETECTED [submit, done] window by its wall-clock FRACTION of the turn (the
    # window is from the video; the timeline only orders/labels the events, since
    # wall-clock can't be mapped to video time directly — it drifts). Conclusion
    # at the detected `done`.
    for ti, (t, u, s) in enumerate(zip(turns, ups, stop)):
        st = sync["turns"][ti]
        sub_v, done_v = st["submit"], st["done"]
        keys.append((round(sub_v, 3), ("turn", ti, 0, False)))     # header, no events
        evs = [r for r in rows if r["event"] == "PreToolUse"
               and u["t"] < r["t"] <= s["t"]]
        span_w = max(0.1, s["t"] - u["t"])                         # turn span (wall)
        seen = 0
        for ev in evs:
            seen += 1
            frac = min(1.0, max(0.0, (ev["t"] - u["t"]) / span_w))
            ev_v = sub_v + frac * (done_v - sub_v)                 # -> video time
            evd = ev.get("detail", "")
            tool = evd.split(" ", 1)[0]
            target = (evd.split(" ", 1)[1] if " " in evd else "")
            target = os.path.basename(target) if "/" in target else target[:36]
            keys.append((round(ev_v, 3), ("turn", ti, seen, False, (tool, target))))
        keys.append((round(done_v, 3), ("turn", ti, seen, True)))  # conclusion
    keys.sort(key=lambda x: x[0])

    # render each keyframe cumulatively
    def conclusion_text(ti):
        m = stop[ti].get("message", "") if ti < len(stop) else ""
        return (m.split("\n")[0] if m else turns[ti]["outro"]["text"])[:80]

    turn_events = {ti: [] for ti in range(len(turns))}
    segs = []
    for idx, (t, spec) in enumerate(keys):
        if spec[0] == "launch":
            img = launch_panel(cmd, flags, spec[1])
        else:
            _, ti, nrev, concl = spec[:4]
            if len(spec) == 5:                     # an event row to add
                tool, target = spec[4]
                turn_events[ti].append({"tool": tool, "target": target})
            img = turn_panel(ti + 1, len(turns), turns[ti]["prompt"],
                             turn_events[ti], nrev,
                             conclusion_text(ti) if concl else None)
        p = os.path.join(pdir, f"p{idx:03d}.png")
        img.save(p)
        segs.append((p, t))

    # build the panel video (each png held until the next keyframe)
    vtot = sync["video_total"]
    lst = os.path.join(pdir, "panels.txt")
    with open(lst, "w") as f:
        # blank panel before the first keyframe
        blank = os.path.join(pdir, "blank.png"); _new()[0].save(blank)
        f.write(f"file '{blank}'\nduration {segs[0][1]:.3f}\n")
        for i, (p, t) in enumerate(segs):
            end = segs[i + 1][1] if i + 1 < len(segs) else vtot
            f.write(f"file '{p}'\nduration {max(0.05, end - t):.3f}\n")
        f.write(f"file '{segs[-1][0]}'\n")
    panel_mp4 = os.path.join(pdir, "panel.mp4")
    subprocess.run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-r", "25",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-vsync", "cfr", panel_mp4], check=True, capture_output=True)

    # composite: terminal (1200) left + panel (720) right; audio from session.mp4
    term = os.path.join(demo, "terminal.mp4")
    audio_src = os.path.join(demo, "session.mp4")
    out = os.path.join(demo, "session_panel.mp4")
    subprocess.run(
        [FF, "-y", "-i", term, "-i", panel_mp4, "-i", audio_src,
         "-filter_complex",
         f"[0:v]scale={TERM_W}:-1,pad={TERM_W}:{H}:0:(oh-ih)/2:color=0x181825[L];"
         f"[1:v]scale={PANEL_W}:{H}[R];[L][R]hstack=inputs=2[v]",
         "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-crf", "20", "-c:a", "aac", "-b:a", "192k", out],
        check=True, capture_output=True)
    print(f"wrote {out}  ({len(segs)} panel keyframes)")


if __name__ == "__main__":
    main()
