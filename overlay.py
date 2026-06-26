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
# distinct colour per token (by position) so no two tokens share a colour
PALETTE = [(166, 227, 161), (137, 180, 250), (250, 179, 135),
           (203, 166, 247), (148, 226, 213), (249, 226, 175)]
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
FADEOUT = 0.9         # fade the last clip out at the end
HOLD = 1.0            # freeze-hold at the end of each scene before transition
XF = 0.5              # crossfade duration between scenes
SAFETY = 0.25         # end each scene's video this much BEFORE the clear, so the
                      # freeze-hold grabs the last output frame, not the blank
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


def transitions_av(vid, voice, vb, ab, delays):
    """Assemble per-scene clips, freeze-hold + crossfade between them.

    Video is split at the visual clears (vb); audio is split at the *sentence*
    boundaries (ab) — so the narration is NEVER cut mid-sentence. Each scene's
    narration is re-anchored to that scene's start (delays[i]), so video, audio
    and panel all line up at every scene boundary. Returns (out, scene_starts)."""
    n = len(vb) - 1
    pad = HOLD + XF
    segpaths, durs = [], []
    for i in range(n):
        # end the video a hair BEFORE the clear (Hide makes content->blank an
        # instant jump cut; without this margin the freeze grabs the blank frame)
        vend = vb[i+1] - (SAFETY if i < n - 1 else 0.0)
        L = vend - vb[i]
        A = ab[i+1] - ab[i]                            # narration length
        # last scene: hold long enough for the narration to FINISH, then leave a
        # HOLD+FADEOUT silent tail so the closing fade never cuts the voice.
        end_pad = pad if i < n - 1 else max(0.0, A - L) + HOLD + FADEOUT
        target = L + end_pad
        dms = int(delays[i] * 1000)
        seg = f"{DEMO}/_seg{i}.mp4"
        fc = [f"[1:a]adelay={dms}|{dms},apad=whole_dur={target:.3f},"
              f"atrim=end={target:.3f}[a]",
              f"[0:v]tpad=stop_duration={end_pad:.3f}:stop_mode=clone[v]"]
        vmap = "[v]"
        subprocess.run(
            [FF, "-y", "-ss", f"{vb[i]:.3f}", "-to", f"{vend:.3f}", "-i", vid,
             "-ss", f"{ab[i]:.3f}", "-to", f"{ab[i+1]:.3f}", "-i", voice,
             "-filter_complex", ";".join(fc), "-map", vmap, "-map", "[a]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
             "-c:a", "aac", "-b:a", "160k", seg],
            check=True, capture_output=True)
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


def build_subs(cues, ab, S, delays, initial, intro, dst):
    """Place each cue (voice-timeline) on the transitioned timeline: scene i's
    narration starts at S[i] + delays[i], so a cue at voice-time vt lands there
    + (vt - ab[i]). Subtitles thus follow the re-anchored per-scene audio."""
    def fmt(s):
        h = int(s//3600); s -= h*3600; m = int(s//60); s -= m*60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}"

    def tt(vt):
        i = max(j for j in range(len(ab)-1) if ab[j] <= vt)
        i = min(i, len(S)-1)
        return S[i] + delays[i] + (vt - ab[i]) + intro
    out = []
    for n, (a, b, txt) in enumerate(cues, start=1):
        out.append(f"{n}\n{fmt(tt(a))} --> {fmt(tt(b))}\n{txt}")
    open(dst, "w", encoding="utf-8").write("\n\n".join(out) + "\n")


def _save(img, path):
    img.save(path); return path


def main():
    os.makedirs(PDIR, exist_ok=True)
    tl = json.load(open(f"{DEMO}/timeline.json", encoding="utf-8"))
    total = _dur(f"{DEMO}/rsync-demo.mp4")
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
    subprocess.run([FF, "-y", "-i", f"{DEMO}/rsync-demo.mp4",
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
        src, S = transitions_av(vid, f"{DEMO}/audio/voice.mp3", vb, ab, delays)
        print(f"transitions: {len(panels)} scenes, {HOLD}s hold + {XF}s xfade")
    else:                                                # fallback: no transitions
        d_ms = int(INTRO * 1000)
        subprocess.run([FF, "-y", "-i", vid, "-i", f"{DEMO}/audio/voice.mp3",
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
                    "-b:a", "160k", FINAL], check=True, capture_output=True)

    # sidecar subtitles (NOT burned in), built on the new per-scene timeline
    dst = f"{DEMO}/rsync-demo-final.srt"
    if synced:
        build_subs(tl["cues"], ab, S, delays, INITIAL, INTRO, dst)
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
