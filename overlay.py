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

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DEMO = os.path.dirname(os.path.abspath(__file__))
AV = f"{DEMO}/_av.mp4"
FINAL = f"{DEMO}/rsync-demo-final.mp4"
PDIR = f"{DEMO}/_panels"
FF = "/opt/homebrew/bin/ffmpeg"

CW, H, TERM_W = 1920, 1080, 1200
PANEL_W = CW - TERM_W                 # 720
MONO = "/System/Library/Fonts/Menlo.ttc"
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
BG = (24, 24, 37)
TEXT = (205, 214, 244)
HL = (49, 50, 68)
ROLE = {"ord": (166, 227, 161), "star": (250, 179, 135), "path": (203, 166, 247)}
PAD = 42
CMD_Y = 172
CMD_SIZE = 27
LINE_H = 54           # roomy: tall padded token boxes still clear the next line
ROW_H = 128
TOK_PADX = 7          # token highlight box padding (more breathing room)
TOK_PADT = 9
TOK_PADB = 14
PANEL_LEAD = -0.08    # banner switches just AFTER the detected clear so it lands
                      # in the NEXT segment — each scene's freeze-hold then holds
                      # its own (matching) panel frame, not the next scene's
INTRO = 0.6           # dissolve-in: hold pure bg this long, then fade
FADE = 0.7            # fade-in duration
HOLD = 1.0            # freeze-hold at the end of each scene before transition
XF = 0.5              # crossfade duration between scenes
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


def panel_img(p, k, next_key=None):
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
        nt = next_key
        while d.textlength(nt + "…", font=nf_t) > INNER and len(nt) > 4:
            nt = nt[:-1]
        if nt != next_key:
            nt += "…"
        d.text((PAD, yb + 54), nt, font=nf_t, fill=muted)
    if p is not None:
        klines = wrap_words(p["key"], cjk_b, INNER - 44)
        bot = 48 + len(klines) * 38 + 14
        d.rectangle([PAD, 40, PANEL_W - PAD, bot], fill=HL)   # square, no radius
        d.line([(PAD, 40), (PAD, bot)], fill=ROLE["star"], width=5)
        for li, ln in enumerate(klines):
            d.text((PAD + 22, 56 + li * 38), ln, font=cjk_b, fill=TEXT)
    if p is None or not p.get("cmd"):
        return img
    cmd = p["cmd"]
    lines = wrap_cmd(cmd)
    toks = p["tokens"][:k]
    # highlight revealed tokens (line-aware). Extend the box to the next
    # whitespace so it wraps the WHOLE argument (e.g. --exclude='*.log'),
    # never cutting in the middle of a token.
    for t in toks:
        ext_ce = t["ce"]
        while ext_ce < len(cmd) and cmd[ext_ce] != " ":
            ext_ce += 1
        li, col = char_xy(lines, t["cs"])
        _, col2 = char_xy(lines, ext_ce - 1)
        y = CMD_Y + li * LINE_H
        d.rounded_rectangle([PAD + col*CHAR_W - TOK_PADX, y - TOK_PADT,
                             PAD + (col2 + 1)*CHAR_W + TOK_PADX,
                             y + CMD_SIZE + TOK_PADB],
                            radius=6, fill=HL, outline=ROLE[t["role"]], width=2)
    for li, (start, txt) in enumerate(lines):
        d.text((PAD, CMD_Y + li * LINE_H), txt, font=CMD_F, fill=TEXT)
    # annotation rows below the (possibly 2-line) command
    row_y0 = CMD_Y + len(lines) * LINE_H + 40
    for i, t in enumerate(toks):
        col = ROLE[t["role"]]
        ry = row_y0 + i * ROW_H
        d.rounded_rectangle([PAD, ry, PAD + 5, ry + 76], radius=2, fill=col)
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


def detect_clears(video):
    """Find the real frame-times where the terminal clears (content -> empty).
    These are deterministic visual anchors: the panel banner is pinned to them
    so left and right switch on the SAME frame (no predicted-clock residual)."""
    sw, sh, fps = 200, 180, 12.5
    raw = subprocess.run([FF, "-i", video, "-vf",
                          f"scale={sw}:{sh},format=gray,fps={fps}",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (sw * sh)
    f = np.frombuffer(raw, np.uint8)[:n*sw*sh].reshape(n, sh, sw)
    content = (f > 90).sum(axis=(1, 2)).astype(float)
    base, hi = np.percentile(content, 5), np.percentile(content, 70)
    thr = base + 0.30 * (hi - base)
    empty = content < thr
    return [i / fps for i in range(1, n) if empty[i] and not empty[i-1]]


def _dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout)


def transitions(core, bounds):
    """Split `core` at scene boundaries, freeze-hold each scene's end by HOLD,
    then crossfade (XF) into the next. Returns (out, scene_starts) where
    scene_starts[i] is scene i's content start in the new timeline."""
    n = len(bounds) - 1
    pad = HOLD + XF
    segpaths, durs = [], []
    for i in range(n):
        seg = f"{DEMO}/_seg{i}.mp4"
        cmd = [FF, "-y", "-ss", f"{bounds[i]:.3f}", "-to", f"{bounds[i+1]:.3f}",
               "-i", core]
        if i < n - 1:                                  # freeze + silence at end
            cmd += ["-vf", f"tpad=stop_duration={pad}:stop_mode=clone",
                    "-af", f"apad=pad_dur={pad}"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", seg]
        subprocess.run(cmd, check=True, capture_output=True)
        segpaths.append(seg); durs.append(_dur(seg))
    cmd = [FF, "-y"]
    for p in segpaths:
        cmd += ["-i", p]
    vf, af, pv, pa, cum = [], [], "[0:v]", "[0:a]", durs[0]
    for k in range(1, n):
        vo, ao = f"[v{k}]", f"[a{k}]"
        vf.append(f"{pv}[{k}:v]xfade=transition=fade:duration={XF}:"
                  f"offset={cum - XF:.3f}{vo}")
        af.append(f"{pa}[{k}:a]acrossfade=d={XF}{ao}")
        pv, pa, cum = vo, ao, cum + durs[k] - XF
    out = f"{DEMO}/_trans.mp4"
    subprocess.run(cmd + ["-filter_complex", ";".join(vf + af),
                          "-map", pv, "-map", pa, "-c:v", "libx264",
                          "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac",
                          "-b:a", "160k", out], check=True, capture_output=True)
    S = [0.0]
    for i in range(1, n):
        S.append(S[-1] + durs[i-1] - XF)
    return out, S


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


def _save(img, path):
    img.save(path); return path


def main():
    os.makedirs(PDIR, exist_ok=True)
    tl = json.load(open(f"{DEMO}/timeline.json", encoding="utf-8"))
    total = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", AV], capture_output=True, text=True).stdout)
    scale = total / tl["predicted_total"]
    print(f"total={total:.1f}s scale={scale:.3f}, CPL={CPL}")

    # panel reveal times come straight from the (TS-calibrated) timeline, so
    # they track the real video per-token; JCUT pulls each token reveal a hair
    # early so it never feels like it lags the typing.
    panels = tl["panels"]
    # Anchor each scene's panel to the REAL detected terminal clear, so the
    # banner switches on the exact frame the terminal clears. Within a scene,
    # token reveals keep their predicted offset (scaled) from the scene start.
    clears = detect_clears(f"{DEMO}/rsync-demo.mp4")
    synced = len(clears) == len(panels) - 1
    if synced:
        anchors = [panels[0]["banner"] * scale] + clears
        print(f"clear-sync: detected {len(clears)} clears, anchored to terminal")
    else:
        anchors = [p["banner"] * scale for p in panels]
        print(f"clear-sync: detected {len(clears)} != {len(panels)-1}, fallback")

    def st(pi, sec):
        return max(0.0, anchors[pi] + (sec - panels[pi]["banner"]) * scale
                   - PANEL_LEAD)

    blank = _save(panel_img(None, 0), f"{PDIR}/blank.png")
    states = [(0.0, blank)]
    for pi, p in enumerate(panels):
        nk = panels[pi + 1]["key"] if pi + 1 < len(panels) else None
        states.append((st(pi, p["banner"]), _save(panel_img(p, 0, nk),
                                                   f"{PDIR}/p{pi}_b.png")))
        if p["hero"]:
            states.append((st(pi, p["cmd_start"]),
                           _save(panel_img(p, 0, nk), f"{PDIR}/p{pi}_c.png")))
            for ki, t in enumerate(p["tokens"], start=1):
                states.append((st(pi, t["reveal"]),
                               _save(panel_img(p, ki, nk), f"{PDIR}/p{pi}_{ki}.png")))
    states.sort(key=lambda s: s[0])
    segs = [(png, (states[i+1][0] if i+1 < len(states) else total) - t0)
            for i, (t0, png) in enumerate(states)]
    segs = [(p, d) for p, d in segs if d > 0.001]
    concat_video(segs, f"{DEMO}/_panel.mp4")

    # pass 1 — pad terminal to 1920 + overlay the panel (still core timeline)
    core = f"{DEMO}/_core.mp4"
    subprocess.run([FF, "-y", "-i", AV, "-i", f"{DEMO}/_panel.mp4",
                    "-filter_complex",
                    f"[0:v]pad={CW}:{H}:0:0:color=0x181825[bg];"
                    f"[bg][1:v]overlay={TERM_W}:0[v]",
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "copy", core],
                   check=True, capture_output=True)

    # pass 2 — per-scene 1s freeze-hold + crossfade between scenes (needs the
    # detected clear boundaries; skip if detection didn't line up).
    if synced:
        bounds = [0.0] + clears + [_dur(core)]
        src, S = transitions(core, bounds)
        print(f"transitions: {len(bounds)-1} scenes, {HOLD}s hold + {XF}s xfade")
    else:
        bounds, S, src = None, None, core

    # pass 3 — dissolve-in intro from pure bg + matching audio offset
    d_ms = int(INTRO * 1000)
    subprocess.run([FF, "-y", "-i", src, "-filter_complex",
                    f"[0:v]tpad=start_duration={INTRO}:start_mode=add:"
                    f"color=0x181825,fade=t=in:st={INTRO}:d={FADE}:"
                    f"color=0x181825[v];[0:a]adelay={d_ms}|{d_ms}[a]",
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac",
                    "-b:a", "160k", FINAL],
                   check=True, capture_output=True)

    # sidecar subtitles (NOT burned in), remapped through the new timeline
    dst = f"{DEMO}/rsync-demo-final.srt"
    if synced:
        remap_srt(f"{DEMO}/subs.srt", dst, bounds, S, INTRO)
    else:
        shift_srt(f"{DEMO}/subs.srt", dst, INTRO)
    print(f"wrote {FINAL} (+ sidecar, intro offset {INTRO}s)")


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
