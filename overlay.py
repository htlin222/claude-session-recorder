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
CMD_Y = 168
CMD_SIZE = 27
LINE_H = 40
ROW_H = 128
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


def panel_img(p, k):
    cjk_b = ImageFont.truetype(CJK, 29)
    cjk = ImageFont.truetype(CJK, 26)
    lblf = ImageFont.truetype(MONO, 27)
    img = Image.new("RGB", (PANEL_W, H), BG)
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (0, H)], fill=ROLE["path"], width=3)
    if p is not None:
        klines = wrap_words(p["key"], cjk_b, INNER - 44)
        d.rounded_rectangle([PAD, 40, PANEL_W - PAD, 48 + len(klines)*38 + 14],
                            radius=14, fill=HL)
        d.line([(PAD, 40), (PAD, 48 + len(klines)*38 + 14)], fill=ROLE["star"],
               width=5)
        for li, ln in enumerate(klines):
            d.text((PAD + 22, 56 + li * 38), ln, font=cjk_b, fill=TEXT)
    if p is None or not p.get("cmd"):
        return img
    cmd = p["cmd"]
    lines = wrap_cmd(cmd)
    toks = p["tokens"][:k]
    # highlight revealed tokens (line-aware)
    for t in toks:
        li, col = char_xy(lines, t["cs"])
        _, col2 = char_xy(lines, t["ce"] - 1)
        y = CMD_Y + li * LINE_H
        d.rounded_rectangle([PAD + col*CHAR_W - 3, y - 4,
                             PAD + (col2 + 1)*CHAR_W + 2, y + CMD_SIZE + 8],
                            radius=6, fill=HL)
    for li, (start, txt) in enumerate(lines):
        d.text((PAD, CMD_Y + li * LINE_H), txt, font=CMD_F, fill=TEXT)
    # short stubs under revealed tokens (line-aware)
    for t in toks:
        li, col = char_xy(lines, t["cs"])
        _, col2 = char_xy(lines, t["ce"] - 1)
        tcx = PAD + (col + col2 + 1) / 2 * CHAR_W
        ytop = CMD_Y + li * LINE_H + CMD_SIZE + 8
        d.line([(tcx, ytop), (tcx, ytop + 14)], fill=ROLE[t["role"]], width=3)
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

    blank = _save(panel_img(None, 0), f"{PDIR}/blank.png")
    states = [(0.0, blank)]
    for pi, p in enumerate(tl["panels"]):
        states.append((p["banner"] * scale, _save(panel_img(p, 0),
                                                   f"{PDIR}/p{pi}_b.png")))
        if p["hero"]:
            states.append((p["cmd_start"] * scale,
                           _save(panel_img(p, 0), f"{PDIR}/p{pi}_c.png")))
            for ki, t in enumerate(p["tokens"], start=1):
                states.append((t["reveal"] * scale,
                               _save(panel_img(p, ki), f"{PDIR}/p{pi}_{ki}.png")))
    states.sort(key=lambda s: s[0])
    segs = [(png, (states[i+1][0] if i+1 < len(states) else total) - t0)
            for i, (t0, png) in enumerate(states)]
    segs = [(p, d) for p, d in segs if d > 0.001]
    concat_video(segs, f"{DEMO}/_panel.mp4")

    subprocess.run([FF, "-y", "-i", AV, "-i", f"{DEMO}/_panel.mp4",
                    "-filter_complex",
                    f"[0:v]pad={CW}:{H}:0:0:color=0x181825[bg];"
                    f"[bg][1:v]overlay={TERM_W}:0[v]",
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "copy", FINAL],
                   check=True, capture_output=True)
    # subtitles as a sidecar (NOT burned in)
    import shutil
    shutil.copy(f"{DEMO}/subs.srt", f"{DEMO}/rsync-demo-final.srt")
    print(f"wrote {FINAL} (+ sidecar rsync-demo-final.srt)")


if __name__ == "__main__":
    main()
