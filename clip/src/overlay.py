#!/usr/bin/env python3
"""Composite the explainshell panel (right) onto the terminal video.

Canvas 1920x1080: terminal 1200 (left) + panel 720 (right). The panel is
flattened to its own video via the concat demuxer (one image per time-segment)
then overlaid in a single pass — fast. Subtitles are NOT burned in; subs.srt is
shipped as a sidecar.

Panel = variant A: key-point banner + echoed command (FIXED mono size — long
commands WRAP to a 2nd line, never shrink) + per-token rows that reveal in sync
with the deliberate typing. Colours: ord=green, star=peach, path=mauve."""
import json
import os
import subprocess
import tomllib

import lesson
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # clip/
# per-slug workspace (must match build.py); pass LESSON=<slug> so concurrent
# overlays read their OWN render, not config.toml's single active lesson.
SLUG = lesson.active_slug(ROOT)
DEMO = lesson.workspace(ROOT, SLUG)
DIST = f"{ROOT}/dist"
TERMINAL = f"{DEMO}/terminal.mp4"     # tool-agnostic VHS render (left pane)
PDIR = f"{DEMO}/_panels"
FF = "/opt/homebrew/bin/ffmpeg"
_T = tomllib.load(open(f"{ROOT}/config.toml", "rb"))["timing"]

CW, H, TERM_W = 1920, 1080, 1200
PANEL_W = CW - TERM_W                 # 720
MONO = "/System/Library/Fonts/Menlo.ttc"
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
BG = (24, 24, 37)
TEXT = (205, 214, 244)
HL = (49, 50, 68)
ROLE = {"ord": (166, 227, 161), "star": (250, 179, 135), "path": (203, 166, 247)}
# distinct colour per token (by position) so no two tokens share a colour
PALETTE = [tuple(c) for c in
           tomllib.load(open(f"{ROOT}/config.toml", "rb"))["panel"]["palette"]]
PAD = 42
CMD_Y = 172
CMD_SIZE = 27
LINE_H = 54           # roomy: tall padded token boxes still clear the next line
ROW_H = 128
TOK_PADX = 7          # token highlight box padding (more breathing room)
TOK_PADT = 9
TOK_PADB = 14
PANEL_LEAD = _T["panel_lead"]   # banner lands in its own segment (see config)
INTRO = _T["intro"]
FADE = _T["fade_in"]
FADEOUT = _T["fade_out"]
HOLD = _T["hold"]
XF = _T["xfade"]
SAFETY = _T["safety"]
JCUT = _T.get("jcut_lead", 0.35)     # transition J-cut: incoming voice leads video
GUARD = _T.get("jcut_guard", 0.12)   # silence kept after a scene's last word
INNER = PANEL_W - 2 * PAD
_d = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
CMD_F = ImageFont.truetype(MONO, CMD_SIZE)
CHAR_W = _d.textlength("M", font=CMD_F)
CPL = int(INNER // CHAR_W)            # chars per line


def wrap_words(text, font, maxw):
    cur, out = "", []
    for ch in text:
        if _d.textlength(cur + ch, font=font) > maxw and cur:
            out.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def wrap_cmd(cmd):
    """partition cmd into <=CPL-char lines at spaces; return [(start_idx, text)]."""
    lines, i, n = [], 0, len(cmd)
    while i < n:
        end = min(i + CPL, n)
        if end < n:
            sp = cmd.rfind(" ", i, end + 1)
            if sp > i:
                end = sp + 1
        lines.append((i, cmd[i:end])); i = end
    return lines


def char_xy(lines, k):
    """char index k -> (line_idx, col) using the wrapped command lines."""
    for li, (start, txt) in enumerate(lines):
        if start <= k < start + len(txt):
            return li, k - start
    return len(lines) - 1, len(lines[-1][1])


def panel_img(p, k, next_key=None, num=None, total=None, next_num=None):
    cjk_b = ImageFont.truetype(CJK, 29)
    cjk = ImageFont.truetype(CJK, 26)
    lblf = ImageFont.truetype(MONO, 27)
    img = Image.new("RGB", (PANEL_W, H), BG)
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (0, H)], fill=ROLE["path"], width=3)
    # subtle "next up" preview at the bottom (65% opacity, low saturation)
    if next_key:
        muted = (112, 116, 128)
        nf_l = ImageFont.truetype(CJK, 21)
        nf_t = ImageFont.truetype(CJK, 27)
        yb = H - 124
        d.line([(PAD, yb), (PANEL_W - PAD, yb)], fill=(52, 54, 66), width=1)
        d.text((PAD, yb + 18), "下一個任務", font=nf_l, fill=muted)
        label = f"{next_num}  {next_key}" if next_num else next_key
        nt = label
        while d.textlength(nt + "…", font=nf_t) > INNER and len(nt) > 4:
            nt = nt[:-1]
        if nt != label:
            nt += "…"
        d.text((PAD, yb + 54), nt, font=nf_t, fill=muted)
    if p is not None:
        nw = 0
        if num:
            ns = f"{num} / {total}"
            nw = d.textlength(ns + "  ", font=cjk_b)
        klines = wrap_words(p["key"], cjk_b, INNER - 44 - nw)
        bot = 48 + len(klines) * 38 + 14
        d.rectangle([PAD, 40, PANEL_W - PAD, bot], fill=HL)   # square, no radius
        d.line([(PAD, 40), (PAD, bot)], fill=ROLE["star"], width=5)
        if num:
            d.text((PAD + 22, 56), ns, font=cjk_b, fill=ROLE["star"])
        for li, ln in enumerate(klines):
            d.text((PAD + 22 + nw, 56 + li * 38), ln, font=cjk_b, fill=TEXT)
    if p is None or not p.get("cmd"):
        return img
    cmd = p["cmd"]
    lines = wrap_cmd(cmd)
    toks = p["tokens"][:k]
    # highlight revealed tokens (line-aware). Extend the box to the next
    # whitespace so it wraps the WHOLE argument (e.g. --exclude='*.log'),
    # never cutting in the middle of a token.
    for i, t in enumerate(toks):
        ext_ce = t["ce"]
        while ext_ce < len(cmd) and cmd[ext_ce] != " ":
            ext_ce += 1
        li, col = char_xy(lines, t["cs"])
        _, col2 = char_xy(lines, ext_ce - 1)
        y = CMD_Y + li * LINE_H
        d.rectangle([PAD + col*CHAR_W - TOK_PADX, y - TOK_PADT,
                     PAD + (col2 + 1)*CHAR_W + TOK_PADX, y + CMD_SIZE + TOK_PADB],
                    fill=HL, outline=PALETTE[i % len(PALETTE)], width=2)
    for li, (start, txt) in enumerate(lines):
        d.text((PAD, CMD_Y + li * LINE_H), txt, font=CMD_F, fill=TEXT)
    # annotation rows below the (possibly 2-line) command
    row_y0 = CMD_Y + len(lines) * LINE_H + 40
    for i, t in enumerate(toks):
        col = PALETTE[i % len(PALETTE)]
        ry = row_y0 + i * ROW_H
        d.rectangle([PAD, ry, PAD + 5, ry + 76], fill=col)
        d.text((PAD + 22, ry), t["label"], font=lblf, fill=col)
        for j, ln in enumerate(wrap_words(t["ann"], cjk, INNER - 26)):
            d.text((PAD + 22, ry + 42 + j * 34), ln, font=cjk, fill=TEXT)
    return img


def concat_video(segs, out):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for png, dur in segs:
            f.write(f"file '{png}'\nduration {dur:.3f}\n")
        f.write(f"file '{segs[-1][0]}'\n")
    subprocess.run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-r", "25", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "20", "-vsync", "cfr", out],
                   check=True, capture_output=True)


FPS = 12.5


def _clear_signal(video):
    """Per-frame bright-pixel count of the terminal (high=full screen, low=empty)."""
    sw, sh = 200, 180
    raw = subprocess.run([FF, "-i", video, "-vf",
                          f"scale={sw}:{sh},format=gray,fps={FPS}",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (sw * sh)
    f = np.frombuffer(raw, np.uint8)[:n*sw*sh].reshape(n, sh, sw)
    return (f > 90).sum(axis=(1, 2)).astype(float)


def detect_clears(video, predicted=None, expected=None):
    """Find the real frame-times where the terminal clears (content -> empty).
    These are deterministic visual anchors: the panel banner is pinned to them
    so left and right switch on the SAME frame (no predicted-clock residual).

    Blind brightness-threshold detection works when each scene fills the screen.
    Sparse-output lessons (e.g. `fzf -f` prints 1-3 lines) dip near-empty
    mid-scene, so the blind pass over-counts. When the count is wrong AND we know
    how many scenes to expect (+ their predicted clear times), fall back to
    GUIDED selection: keep the `expected` content-drops nearest the predicted
    per-scene clears, which ignores spurious mid-scene dips. Returns (clears,
    method) where method is "detect" or "guided"."""
    content = _clear_signal(video)
    n = len(content)
    base, hi = np.percentile(content, 5), np.percentile(content, 70)
    thr = base + 0.30 * (hi - base)
    empty = content < thr
    cands = [i / FPS for i in range(1, n) if empty[i] and not empty[i-1]]
    if expected is None or len(cands) == expected:
        return cands, "detect"
    # guided: one clear per predicted scene-start — nearest candidate, monotonic.
    # The real clear (full->empty) is always a candidate and sits at the scene
    # start; spurious mid-scene dips are seconds away, so "nearest" picks reals.
    sel, last = [], -1.0
    for t in predicted:
        avail = [c for c in cands if c > last + 0.05]
        if not avail:
            break
        c = min(avail, key=lambda x: abs(x - t))
        if abs(c - t) > 4.0:               # no real clear near this scene start
            break
        sel.append(c); last = c
    if len(sel) == expected:
        return sel, "guided"
    return cands, "detect"                 # guided failed -> wrong count -> fallback


def _dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout)


def transitions_av(vid, voice, vb, ab, delays):
    """Freeze-held, crossfaded VIDEO segments + one globally-placed narration
    track with an adaptive J-cut at each transition.

    Video is split at the visual clears (vb) and xfaded — unchanged, so every
    scene stays locked to its real terminal clear. The narration (split at
    sentence boundaries ab, never mid-sentence) is then placed on a single track:
    scene i's voice starts at S[i] - lead[i], i.e. its intro sentence leads its
    own video into the SILENT HOLD that follows scene i-1's last word. lead[i] is
    capped at JCUT and shrunk to whatever silent gap is actually available, so a
    J-cut never talks over the previous scene. Returns (out, scene_starts, leads)."""
    n = len(vb) - 1
    segpaths, durs, Alen = [], [], []
    for i in range(n):
        # end the video a hair BEFORE the clear (Hide makes content->blank an
        # instant jump cut; without this margin the freeze grabs the blank frame)
        vend = vb[i+1] - (SAFETY if i < n - 1 else 0.0)
        L = vend - vb[i]
        A = ab[i+1] - ab[i]                            # narration length
        Alen.append(A)
        # CRITICAL: hold the still frame until THIS scene's narration has fully
        # finished, THEN HOLD more, before the transition — so a scene's voice
        # never bleeds into the next clip. `overrun` is how much the narration
        # outlasts the on-screen action (delays[i] covers the intro idle); every
        # scene thus leaves >= HOLD of silence before the next, which the J-cut
        # leads into. The last scene also reserves FADEOUT for the closing fade.
        overrun = max(0.0, delays[i] + A - L)
        end_pad = overrun + HOLD + (FADEOUT if i == n - 1 else XF)
        seg = f"{DEMO}/_seg{i}.mp4"
        subprocess.run(
            [FF, "-y", "-ss", f"{vb[i]:.3f}", "-to", f"{vend:.3f}", "-i", vid,
             "-filter_complex",
             f"[0:v]tpad=stop_duration={end_pad:.3f}:stop_mode=clone[v]",
             "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-crf", "20", "-an", seg], check=True, capture_output=True)
        segpaths.append(seg); durs.append(_dur(seg))
    # scene starts on the xfade-overlapped timeline
    S = [0.0]
    for i in range(1, n):
        S.append(S[-1] + durs[i-1] - XF)
    # adaptive J-cut lead: pull scene i's intro voice into the silent gap left
    # after scene i-1 stops talking; never into scene i-1's narration.
    leads = [0.0]
    for i in range(1, n):
        prev_end = S[i-1] + delays[i-1] + Alen[i-1]    # scene i-1 stops talking
        gap = (S[i] + delays[i]) - prev_end            # silent hold before scene i
        leads.append(round(min(JCUT, max(0.0, gap - GUARD)), 3))
    total = S[-1] + durs[-1]
    # video: xfade-chain the (audio-less) segments
    cmd = [FF, "-y"]
    for p in segpaths:
        cmd += ["-i", p]
    vf, pv, cum = [], "[0:v]", durs[0]
    for k in range(1, n):
        vo = f"[v{k}]"
        vf.append(f"{pv}[{k}:v]xfade=transition=fade:duration={XF}:"
                  f"offset={cum - XF:.3f}{vo}")
        pv, cum = vo, cum + durs[k] - XF
    # audio: place each scene's narration slice at S[i]+delays[i]-lead[i] and sum
    # (slices never overlap each other, so a straight non-normalised mix is clean)
    cmd += ["-i", voice]
    vix = n                                            # voice is input n
    af, labs = [], []
    for i in range(n):
        onset = max(0.0, S[i] + delays[i] - leads[i])
        dms = int(round(onset * 1000))
        af.append(f"[{vix}:a]atrim={ab[i]:.3f}:{ab[i+1]:.3f},asetpts=PTS-STARTPTS,"
                  f"adelay={dms}|{dms}[s{i}]")
        labs.append(f"[s{i}]")
    af.append("".join(labs) + f"amix=inputs={n}:normalize=0:dropout_transition=0,"
              f"apad=whole_dur={total:.3f},atrim=end={total:.3f}[a]")
    out = f"{DEMO}/_trans.mp4"
    subprocess.run(cmd + ["-filter_complex", ";".join(vf + af),
                          "-map", pv, "-map", "[a]", "-c:v", "libx264",
                          "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac",
                          "-b:a", "160k", out], check=True, capture_output=True)
    # J-cut report for verify_sync: per-transition lead + the gap it had to work
    # with, so the loop can confirm no narration was talked over.
    trans = [dict(scene=i, lead=leads[i],
                  gap=round((S[i] + delays[i]) - (S[i-1] + delays[i-1] + Alen[i-1]), 3))
             for i in range(1, n)]
    json.dump(dict(target=JCUT, guard=GUARD, transitions=trans),
              open(f"{DEMO}/jcut_report.json", "w"))
    return out, S, leads


def remap_srt(src, dst, bounds, S, off):
    """remap cue times from core timeline through the transition timeline."""
    def fmt(s):
        h = int(s//3600); s -= h*3600; m = int(s//60); s -= m*60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}"

    def mp(t):
        i = max(j for j in range(len(bounds)-1) if bounds[j] <= t) \
            if t >= bounds[0] else 0
        i = min(i, len(S) - 1)
        return S[i] + (t - bounds[i]) + off
    out = []
    for blk in open(src, encoding="utf-8").read().split("\n\n"):
        ls = blk.splitlines()
        if len(ls) >= 2 and "-->" in ls[1]:
            a, b = ls[1].split(" --> ")
            def p(t):
                h, m, r = t.split(":"); s, ms = r.split(",")
                return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
            ls[1] = f"{fmt(mp(p(a)))} --> {fmt(mp(p(b)))}"
            out.append("\n".join(ls))
    open(dst, "w", encoding="utf-8").write("\n\n".join(out) + "\n")


def build_subs(cues, ab, S, delays, leads, initial, intro, dst):
    """Place each cue (voice-timeline) on the transitioned timeline: scene i's
    narration starts at S[i] + delays[i] - leads[i] (the J-cut shift), so a cue at
    voice-time vt lands there + (vt - ab[i]). Subtitles follow the J-cut voice."""
    def fmt(s):
        h = int(s//3600); s -= h*3600; m = int(s//60); s -= m*60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}"

    def tt(vt):
        i = max(j for j in range(len(ab)-1) if ab[j] <= vt)
        i = min(i, len(S)-1)
        return S[i] + delays[i] - leads[i] + (vt - ab[i]) + intro
    out = []
    for n, (a, b, txt) in enumerate(cues, start=1):
        out.append(f"{n}\n{fmt(tt(a))} --> {fmt(tt(b))}\n{txt}")
    open(dst, "w", encoding="utf-8").write("\n\n".join(out) + "\n")


def _save(img, path):
    img.save(path); return path


def main():
    os.makedirs(PDIR, exist_ok=True)
    tl = json.load(open(f"{DEMO}/timeline.json", encoding="utf-8"))
    slug = tl.get("slug", "demo")          # name outputs after the lesson
    voice = tl["mp3"]
    final = f"{DIST}/{slug}.mp4"
    total = _dur(TERMINAL)
    scale = total / tl["predicted_total"]
    print(f"[{slug}] total={total:.1f}s scale={scale:.3f}, CPL={CPL}")

    # panel reveal times come straight from the (TS-calibrated) timeline, so
    # they track the real video per-token; JCUT pulls each token reveal a hair
    # early so it never feels like it lags the typing.
    panels = tl["panels"]
    # Anchor each scene's panel to the REAL detected terminal clear, so the
    # banner switches on the exact frame the terminal clears. Within a scene,
    # token reveals keep their predicted offset (scaled) from the scene start.
    expected = len(panels) - 1
    # verify_sync.py may drop a clears_override.json (guided, count-correct clears)
    # to heal a structural desync without re-running vhs. Absent in normal runs.
    ovr = f"{DEMO}/clears_override.json"
    if os.path.exists(ovr):
        clears, method = json.load(open(ovr))["clears"], "override"
        print(f"clear-sync: using {len(clears)} override clears")
    else:
        # predicted per-scene clear times (real terminal clock) guide recovery
        # when blind detection miscounts on sparse-output lessons
        predicted = [panels[i]["banner"] * scale for i in range(1, len(panels))]
        clears, method = detect_clears(TERMINAL, predicted, expected)
    synced = len(clears) == expected
    if synced:
        anchors = [panels[0]["banner"] * scale] + clears
        print(f"clear-sync: {method} {len(clears)} clears, anchored to terminal")
    else:
        anchors = [p["banner"] * scale for p in panels]
        print(f"clear-sync: {method} {len(clears)} != {expected}, fallback")
    # the machine-readable sync signal verify_sync.py / the /clip loop read
    json.dump({"slug": slug, "synced": synced, "detected": len(clears),
               "expected": expected, "method": method},
              open(f"{DEMO}/sync_report.json", "w"))
    # default jcut_report so a fallback (no-transition) render never leaves a STALE
    # report from a previous lesson; transitions_av overwrites it when synced.
    json.dump({"target": JCUT, "guard": GUARD, "transitions": []},
              open(f"{DEMO}/jcut_report.json", "w"))

    def st(pi, sec):
        return max(0.0, anchors[pi] + (sec - panels[pi]["banner"]) * scale
                   - PANEL_LEAD)

    ntasks = len(panels) - 1                 # command scenes are numbered 1..N
    blank = _save(panel_img(None, 0), f"{PDIR}/blank.png")
    states = [(0.0, blank)]
    for pi, p in enumerate(panels):
        nk = panels[pi + 1]["key"] if pi + 1 < len(panels) else None
        num = pi if pi >= 1 else None         # intro (pi=0) unnumbered
        nnum = pi + 1 if nk else None

        def pim(kk):
            return panel_img(p, kk, nk, num, ntasks, nnum)
        states.append((st(pi, p["banner"]),
                       _save(pim(0), f"{PDIR}/p{pi}_b.png")))
        if p["hero"]:
            states.append((st(pi, p["cmd_start"]),
                           _save(pim(0), f"{PDIR}/p{pi}_c.png")))
            for ki, t in enumerate(p["tokens"], start=1):
                states.append((st(pi, t["reveal"]),
                               _save(pim(ki), f"{PDIR}/p{pi}_{ki}.png")))
    states.sort(key=lambda s: s[0])
    segs = [(png, (states[i+1][0] if i+1 < len(states) else total) - t0)
            for i, (t0, png) in enumerate(states)]
    segs = [(p, d) for p, d in segs if d > 0.001]
    concat_video(segs, f"{DEMO}/_panel.mp4")

    # pass 1 — pad terminal to 1920 + overlay the panel (VIDEO only; audio is
    # re-attached per scene in transitions_av so it never gets cut mid-sentence)
    vid = f"{DEMO}/_vid.mp4"
    subprocess.run([FF, "-y", "-i", TERMINAL,
                    "-i", f"{DEMO}/_panel.mp4", "-filter_complex",
                    f"[0:v]pad={CW}:{H}:0:0:color=0x181825[bg];"
                    f"[bg][1:v]overlay={TERM_W}:0[v]", "-map", "[v]",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-an", vid], check=True, capture_output=True)

    INITIAL = tl["anchor"]
    if synced:
        # video splits at the visual clears; audio splits at sentence ends
        vb = [0.0] + clears + [total]
        ab = [0.0] + [panels[i]["banner"] - INITIAL for i in range(1, len(panels))] \
            + [tl["narration_dur"]]
        delays = [INITIAL] + [0.0] * (len(panels) - 1)   # scene1 has lead idle
        src, S, leads = transitions_av(vid, voice, vb, ab, delays)
        jc = [l for l in leads if l > 0.02]
        print(f"transitions: {len(panels)} scenes, {HOLD}s hold + {XF}s xfade, "
              f"J-cut on {len(jc)}/{len(leads)-1} (mean {sum(jc)/len(jc):.2f}s)"
              if jc else f"transitions: {len(panels)} scenes, no J-cut room")
    else:                                                # fallback: no transitions
        d_ms = int(INTRO * 1000)
        subprocess.run([FF, "-y", "-i", vid, "-i", voice,
                        "-filter_complex", f"[1:a]adelay={int(INITIAL*1000)}|"
                        f"{int(INITIAL*1000)}[a]", "-map", "0:v", "-map", "[a]",
                        "-c:v", "copy", "-c:a", "aac", f"{DEMO}/_core.mp4"],
                       check=True, capture_output=True)
        src, S, ab, delays = f"{DEMO}/_core.mp4", None, None, None

    # pass 2 — dissolve-in intro from pure bg + matching audio offset, and
    # fade the last clip out at the very end
    d_ms = int(INTRO * 1000)
    fo = _dur(src) + INTRO - FADEOUT                  # fade-out start
    subprocess.run([FF, "-y", "-i", src, "-filter_complex",
                    f"[0:v]tpad=start_duration={INTRO}:start_mode=add:"
                    f"color=0x181825,fade=t=in:st={INTRO}:d={FADE}:"
                    f"color=0x181825,fade=t=out:st={fo:.3f}:d={FADEOUT}:"
                    f"color=0x181825[v];"
                    f"[0:a]adelay={d_ms}|{d_ms},afade=t=out:st={fo:.3f}:"
                    f"d={FADEOUT}[a]",
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac",
                    "-b:a", "160k", final], check=True, capture_output=True)

    # sidecar subtitles (NOT burned in), built on the new per-scene timeline
    dst = f"{DIST}/{slug}.srt"
    if synced:
        build_subs(tl["cues"], ab, S, delays, leads, INITIAL, INTRO, dst)
    else:
        shift_srt(f"{DEMO}/subs.srt", dst, INTRO)
    print(f"wrote {final} (+ sidecar, intro offset {INTRO}s)")


def shift_srt(src, dst, off):
    def fmt(s):
        h = int(s // 3600); s -= h*3600; m = int(s // 60); s -= m*60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}"
    out = []
    for blk in open(src, encoding="utf-8").read().split("\n\n"):
        ls = blk.splitlines()
        if len(ls) >= 2 and "-->" in ls[1]:
            a, b = ls[1].split(" --> ")
            def p(t):
                h, m, r = t.split(":"); s, ms = r.split(",")
                return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
            ls[1] = f"{fmt(p(a)+off)} --> {fmt(p(b)+off)}"
            out.append("\n".join(ls))
    open(dst, "w", encoding="utf-8").write("\n\n".join(out) + "\n")


if __name__ == "__main__":
    main()
