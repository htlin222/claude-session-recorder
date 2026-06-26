#!/usr/bin/env python3
"""STANDALONE PROTOTYPE — a different clip type: a terminal slideshow.

Left pane: `mdp` runs a Markdown deck as a fullscreen terminal presentation,
advanced slide-by-slide by timed Space keypresses. Right pane: the *detail* —
a per-slide panel that elaborates what the slide summarizes. One continuous
zh-TW narration ties them together.

Why this is its own pipeline (not a clip/ lesson): the main engine anchors the
panel to detected screen CLEARS, but mdp slide transitions are redraws, not
clears. Here WE drive the slides (Space at known times), so the panel switches on
those same predicted times — deterministic, and with no typing during the show
there is no per-char drift to calibrate. Proof-of-concept; integrate into /clip
later if it earns its keep.

Run:  python3 slideshow.py        # needs: mdp, vhs, ffmpeg, edge-tts, Pillow, numpy
Out:  ../../../mdp-demo/mdp-demo.mp4 (+ .srt)
"""
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "mdp-demo"))
FF = "/opt/homebrew/bin/ffmpeg"
VOICE = "zh-TW-HsiaoChenNeural"

# canvas: terminal 1200 (left) + detail panel 720 (right)
CW, H, TERM_W = 1920, 1080, 1200
PANEL_W = CW - TERM_W
MONO = "/System/Library/Fonts/Menlo.ttc"
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
BG = (24, 24, 37)
TEXT = (205, 214, 244)
HL = (49, 50, 68)
ACCENT = (137, 180, 250)     # blue
STAR = (250, 179, 135)       # peach
MUTED = (112, 116, 128)
PALETTE = [(166, 227, 161), (137, 180, 250), (250, 179, 135),
           (203, 166, 247), (148, 226, 213), (249, 226, 175)]

# timing (seconds)
INITIAL = 0.4          # idle before typing the launch command
MDP_BOOT = 1.1         # let mdp draw slide 0 before narration starts
TS = 0.024             # modelled per-char typing (only the launch command types)
END_HOLD = 1.6         # SAFE BUFFER: hold the last slide this long AFTER the voice
                       #   finishes, before the fade — so the voice is never clipped
INTRO, FADE_IN, FADE_OUT = 0.6, 0.7, 0.9

# ── the deck: each slide = markdown (left), detail (right panel), narration ──
DECK = [
    dict(md="# 這支 clip 引擎\n\n## 把終端變成教學影片\n\n左邊跑畫面，右邊補細節",
         title="clip 引擎", role=0,
         detail=["一個把 CLI / 終端操作", "變成 1920×1080 教學影片的小工廠",
                 "左：終端實錄　右：explainshell 風格側欄"],
         say=["這支工具，把終端操作變成一支教學影片。",
              "左邊是終端實錄，右邊即時補上細節。"]),
    dict(md="## 三層架構\n\n- **lesson** — 內容\n- **engine** — 產線\n- **workflow** — 編排",
         title="三層分離", role=1,
         detail=["lesson：要教什麼（旁白＋命令）", "engine：怎麼渲染（build / overlay）",
                 "workflow：怎麼自動產出（/clip）"],
         say=["它分成三層：內容、產線、編排。",
              "換個工具，只要改內容，產線完全不用動。"]),
    dict(md="## lesson = 內容\n\n```\nS(\"旁白\")\nR(\"命令\")\nCLR(場景, 面板)\n```",
         title="lesson 怎麼寫", role=2,
         detail=["S()：一句連續旁白", "R()：螢幕上實際跑的命令",
                 "CLR()：開一個場景＋右側面板資料"],
         say=["一支 lesson，就是旁白、命令、跟面板註解。",
              "命令逐 token 打字，註解就隨著打字浮現。"]),
    dict(md="## 渲染管線\n\nbuild → setup → **vhs** → overlay",
         title="四步產線", role=3,
         detail=["build：合成旁白＋產生 tape", "setup：建好命令要用的環境",
                 "vhs：把終端錄成影片", "overlay：合成側欄、轉場、字幕"],
         say=["渲染分四步：合成旁白、佈置環境、錄終端、再合成側欄。"]),
    dict(md="## 同步模型\n\n> 一條連續旁白\n> 動作釘在句界",
         title="畫音怎麼鎖", role=4,
         detail=["整支只有一段連續語音", "命令、清屏都釘在語音的句子邊界",
                 "從錄影偵測真實清屏幀，左右同一幀切換"],
         say=["最難的，是讓聲音跟畫面對上。",
              "整支用一段連續旁白，動作釘在句子邊界。",
              "再從錄影偵測真實的清屏，左右同一幀切換。"]),
    dict(md="## 轉場：J-cut\n\n- 下一段聲音 **提前** 進場\n- 每段定格撐到旁白講完",
         title="J-cut 轉場", role=5,
         detail=["下一幕的引入句提前約 0.35 秒進來", "每幕定格撐到自己旁白講完才轉場",
                 "所以聲音不會溢出、也不會被切掉"],
         say=["場景之間用 J-cut：下一段聲音稍微提前進來。",
              "每一幕都等自己講完才轉場，聲音不會被切。"]),
    dict(md="## loop engineering\n\nverify → 不過關就修 → 再 verify",
         title="可驗的同步", role=0,
         detail=["五道 gate：結構同步、旁白沒切、", "時長、J-cut、旁白沒溢出",
                 "沒過就自動修（guided clears）再驗一次"],
         say=["同步不是憑感覺，是可以量測的。",
              "五道關卡沒過，就自動修、再驗，過了才出片。"]),
    dict(md="## /clip workflow\n\ndesign → envcheck → author → render → verify → deliver",
         title="一句話出片", role=1,
         detail=["丟一個主題或素材給 /clip", "它設計、查環境、寫 lesson、渲染、驗證",
                 "成品落在 ./<slug>/，附完整 provenance"],
         say=["最後，整個流程自動化成一個 workflow。",
              "給它一個主題，它就交出一支驗證過的影片。"]),
    dict(md="# 謝謝\n\n## 一切都可重現",
         title="可重現", role=2,
         detail=["每支成品都附 provenance：", "timeline、verify 判決、設定快照、原始碼",
                 "換機器、改一句，都能重出一模一樣的片"],
         say=["而且一切都可重現。", "謝謝觀看。"]),
]


def parse_srt(path):
    def t2s(t):
        h, m, r = t.split(":"); s, ms = r.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    cues, block = [], []
    for line in open(path, encoding="utf-8").read().splitlines() + [""]:
        if line.strip() == "":
            if len(block) >= 3:
                a, b = block[1].split(" --> ")
                cues.append([t2s(a), t2s(b), " ".join(block[2:]).strip()])
            block = []
        else:
            block.append(line)
    return cues


def _dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "csv=p=0", p],
                capture_output=True, text=True).stdout)


def wrap(text, font, maxw, draw):
    cur, out = "", []
    for ch in text:
        if draw.textlength(cur + ch, font=font) > maxw and cur:
            out.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def panel_img(i):
    s = DECK[i]
    img = Image.new("RGB", (PANEL_W, H), BG)
    d = ImageDraw.Draw(img)
    pad, inner = 42, PANEL_W - 84
    col = PALETTE[s["role"] % len(PALETTE)]
    d.line([(0, 0), (0, H)], fill=col, width=3)
    cjk_b = ImageFont.truetype(CJK, 34)
    cjk = ImageFont.truetype(CJK, 27)
    lbl = ImageFont.truetype(CJK, 22)        # CJK font: "詳解" label needs it
    # number + title banner
    ns = f"{i + 1} / {len(DECK)}"
    nw = d.textlength(ns + "  ", font=cjk_b)
    klines = wrap(s["title"], cjk_b, inner - 44 - nw, d)
    bot = 48 + len(klines) * 46 + 14
    d.rectangle([pad, 40, PANEL_W - pad, bot], fill=HL)
    d.line([(pad, 40), (pad, bot)], fill=STAR, width=5)
    d.text((pad + 22, 56), ns, font=cjk_b, fill=STAR)
    for li, ln in enumerate(klines):
        d.text((pad + 22 + nw, 56 + li * 46), ln, font=cjk_b, fill=TEXT)
    d.text((pad + 2, bot + 22), "詳解", font=lbl, fill=MUTED)
    # detail bullets
    y = bot + 64
    for line in s["detail"]:
        d.rectangle([pad, y + 6, pad + 5, y + 30], fill=col)
        for j, ln in enumerate(wrap(line, cjk, inner - 26, d)):
            d.text((pad + 22, y + j * 36), ln, font=cjk, fill=TEXT)
        y += 36 * max(1, len(wrap(line, cjk, inner - 26, d))) + 16
    # next-up preview
    if i + 1 < len(DECK):
        yb = H - 120
        nf_l = ImageFont.truetype(CJK, 21)
        nf_t = ImageFont.truetype(CJK, 27)
        d.line([(pad, yb), (PANEL_W - pad, yb)], fill=(52, 54, 66), width=1)
        d.text((pad, yb + 18), "下一張", font=nf_l, fill=MUTED)
        d.text((pad, yb + 52), f"{i + 2}  {DECK[i + 1]['title']}", font=nf_t, fill=MUTED)
    return img


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    deck_md = os.path.join(WORK, "deck.md")
    open(deck_md, "w", encoding="utf-8").write("\n\n---\n\n".join(s["md"] for s in DECK))

    # 1) one continuous narration
    says = [snt for s in DECK for snt in s["say"]]
    mp3, srt = os.path.join(WORK, "voice.mp3"), os.path.join(WORK, "voice.srt")
    if not (os.path.exists(mp3) and os.path.exists(srt)):
        subprocess.run(["edge-tts", "--voice", VOICE, "--text", "".join(says),
                        "--write-media", mp3, "--write-subtitles", srt], check=True)
    cues = parse_srt(srt)
    assert len(cues) == len(says), f"cue/sentence mismatch {len(cues)}/{len(says)}"

    # slide i starts when its first narration sentence starts. advance[i] = that
    # time (relative to narration start); advance[0] = 0.
    counts = [len(s["say"]) for s in DECK]
    advance, idx = [0.0], 0
    for c in counts[:-1]:
        idx += c
        advance.append(cues[idx - 1][1])           # end of prev slide's last cue
    narr = _dur(mp3)

    # 2) tape: launch mdp, then Space at each advance time, then quit
    launch = "mdp deck.md"
    t0 = INITIAL + len(launch) * TS + MDP_BOOT      # when slide 0 is up
    bounds = advance + [narr]                       # slide i shown for bounds diff
    slide_dur = [bounds[i + 1] - bounds[i] for i in range(len(DECK))]
    tape = ["Output terminal.mp4", "Set Shell zsh", "Set FontSize 28",
            f"Set Width {TERM_W}", f"Set Height {H}", 'Set Theme "Catppuccin Mocha"',
            "Set Padding 40", "Hide", 'Type "clear"', "Enter", "Show",
            f"Sleep {INITIAL}s", f'Type "{launch}"', "Enter", f"Sleep {MDP_BOOT}s"]
    for i in range(len(DECK)):
        hold = slide_dur[i] + (END_HOLD if i == len(DECK) - 1 else 0.0)
        tape.append(f"Sleep {round(hold, 2)}s")
        if i < len(DECK) - 1:
            tape.append("Space")                    # advance to the next slide
    # NB: no `q` — end ON the last slide, so the final frame is the slide (not the
    # shell prompt). The composite then anchors the fade to the voice, not here.
    open(os.path.join(WORK, "demo.tape"), "w").write("\n".join(tape))

    print(f"slides={len(DECK)} sentences={len(says)} narration={narr:.1f}s t0={t0:.2f}s")
    subprocess.run(["vhs", "demo.tape"], cwd=WORK, check=True)
    term = os.path.join(WORK, "terminal.mp4")
    total = _dur(term)

    # 3) panel video — one PNG per slide, switched at t0+advance[i]
    pdir = os.path.join(WORK, "_panels")
    os.makedirs(pdir, exist_ok=True)
    segs = []
    for i in range(len(DECK)):
        png = os.path.join(pdir, f"p{i}.png")
        panel_img(i).save(png)
        start = t0 + advance[i]
        stop = t0 + advance[i + 1] if i + 1 < len(DECK) else total
        segs.append((png, max(0.1, stop - start)))
    # a blank lead so the panel doesn't show before mdp is up
    blank = os.path.join(pdir, "blank.png")
    Image.new("RGB", (PANEL_W, H), BG).save(blank)
    segs = [(blank, t0)] + segs
    lst = os.path.join(WORK, "_panel.txt")
    with open(lst, "w") as f:
        for png, dur in segs:
            f.write(f"file '{png}'\nduration {dur:.3f}\n")
        f.write(f"file '{segs[-1][0]}'\n")
    panel = os.path.join(WORK, "_panel.mp4")
    subprocess.run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-r", "25",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-vsync", "cfr", panel], check=True, capture_output=True)

    # 4) composite: pad terminal to 1920 + overlay panel; mux narration; fades
    vid = os.path.join(WORK, "_vid.mp4")
    subprocess.run([FF, "-y", "-i", term, "-i", panel, "-filter_complex",
                    f"[0:v]pad={CW}:{H}:0:0:color=0x181825[bg];"
                    f"[bg][1:v]overlay={TERM_W}:0[v]", "-map", "[v]", "-an",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", vid],
                   check=True, capture_output=True)
    final = os.path.join(OUT, "mdp-demo.mp4")
    d_ms = int((t0 + INTRO) * 1000)                 # narration starts when slide 0 is up
    voice_end = t0 + INTRO + narr
    fo = voice_end + END_HOLD                       # fade starts a safe hold AFTER voice
    final_len = fo + FADE_OUT
    # freeze the last slide generously (stop_mode=clone), then -t trims to the
    # voice-anchored length — so the tail is always exactly END_HOLD+FADE_OUT,
    # never a long silent tail nor a clipped last word.
    subprocess.run([FF, "-y", "-i", vid, "-i", mp3, "-filter_complex",
                    f"[0:v]tpad=start_duration={INTRO}:start_mode=add:color=0x181825,"
                    f"tpad=stop_duration={END_HOLD + FADE_OUT + 1.0:.3f}:stop_mode=clone,"
                    f"fade=t=in:st={INTRO}:d={FADE_IN}:color=0x181825,"
                    f"fade=t=out:st={fo:.3f}:d={FADE_OUT}:color=0x181825[v];"
                    f"[1:a]adelay={d_ms}|{d_ms},afade=t=out:st={fo:.3f}:d={FADE_OUT}[a]",
                    "-map", "[v]", "-map", "[a]", "-t", f"{final_len:.3f}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", final],
                   check=True, capture_output=True)

    # 5) sidecar subtitles on the final timeline
    def fmt(s):
        h = int(s // 3600); s -= h * 3600; m = int(s // 60); s -= m * 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"
    out_srt, off = os.path.join(OUT, "mdp-demo.srt"), t0 + INTRO
    with open(out_srt, "w", encoding="utf-8") as f:
        for n, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{n}\n{fmt(a + off)} --> {fmt(b + off)}\n{txt}\n\n")
    print(f"wrote {final}  ({_dur(final):.1f}s, {len(DECK)} slides)")


if __name__ == "__main__":
    main()
