#!/usr/bin/env python3
"""Build the rsync demo: ONE continuous narration + an explainshell side panel.

The voice never stops — it flows sentence to sentence. On-screen actions are
pinned to sentence timestamps inside that single audio (edge-tts gives a real
time for every sentence end). The HERO command of each scene is typed token by
token at a deliberate pace, and each token's panel annotation reveals the moment
that token finishes typing — so the explanatory sentence walks the flags in the
same order they appear. compose.py atempo-nudges the audio to the real render
length to stay locked; overlay.py paints the panel. Subtitles ship as a sidecar
.srt (not burned in)."""
import json
import os
import subprocess

DEMO = os.path.dirname(os.path.abspath(__file__))
AUDIO = f"{DEMO}/audio"
VOICE = "zh-TW-HsiaoChenNeural"
RATE = "+0%"

TS = 0.024          # calibrated to VHS's ACTUAL per-char typing (measured:
                    # 252 chars took ~6.1s -> 24.4ms/char, even though Set is
                    # 45ms). Matching it makes the predicted clock track the
                    # real video at every point, so panel reveals are accurate
                    # straight from timeline.json — no linear-scale fudge.
TOKEN_STEP = 0.6    # deliberate pause before each hero token (smoke-test feel)
ENTER = 0.0
INITIAL = 1.0
OUTPUT_MIN = 0.45
TAIL = 1.4

S = lambda t: ("say", t)
R = lambda c: ("run", c)
# CLR opens a scene and carries its right-panel data: one-line key point, the
# hero command to dissect, and annotated tokens (substr, note, role).
# role -> colour: ord=green, star=peach (scenario's key flag), path=mauve.
def CLR(key=None, hero=None, toks=None):
    return ("clear", key, hero, toks or [])

SCRIPT = [
    CLR(key="rsync · 把 A 同步到 B"),
    S("先來認識這兩個資料夾，A 是來源，B 是目標。"),
    S("我們先看看來源 A 裡面有什麼。"),
    R("tree -a A"),
    S("有原始碼、文件，還有一個比較大的檔案。"),
    S("再看看目標 B。"),
    R("tree B"),
    S("它只有一份舊的 README，和一個多餘的 obsolete 檔案。"),

    CLR(key="先預覽：-n 只看不動手", hero="rsync -a -v -n A/ B/", toks=[
        ("-a", "封存模式，保留權限與目錄結構", "ord"),
        ("-v", "顯示傳輸細節", "ord"),
        ("-n", "dry-run：只列出計畫，不動檔案", "star"),
        ("A/ B/", "複製 A 的內容到 B", "path")]),
    S("同步之前，先養成預覽的好習慣。"),
    S("先用 -a 封存、加上 -v 顯示細節，再放上關鍵的 -n，把來源 A 同步到 B。"),
    R("rsync -a -v -n A/ B/"),
    S("你看，它只列出了計畫，並用 DRY RUN 標示，完全不會動到檔案。"),

    CLR(key="-a -v 標準同步", hero="rsync -a -v A/ B/", toks=[
        ("-a", "封存模式：保留權限、時間、目錄結構", "star"),
        ("-v", "顯示傳輸細節", "ord"),
        ("A/ B/", "結尾斜線＝複製內容，非資料夾", "path")]),
    S("確認沒問題，我們就正式同步。"),
    S("這次用 -a 封存模式、搭配 -v 顯示細節，把 A 的內容複製到 B。"),
    R("rsync -a -v A/ B/"),
    S("所有檔案，都成功複製過去了。"),
    R("tree B"),
    S("現在 B 的內容，跟來源 A 一模一樣。"),

    CLR(key="鏡像同步：--delete 讓 B 跟 A 一致",
        hero="rsync -a -v --delete A/ B/", toks=[
        ("-a", "封存模式，保留權限/時間", "ord"),
        ("-v", "顯示傳輸細節", "ord"),
        ("--delete", "鏡像：刪除 B 裡 A 沒有的檔案", "star"),
        ("A/ B/", "複製 A 的內容到 B", "path")]),
    S("那如果想讓 B 變成 A 的完整鏡像呢？"),
    S("一樣用 -a 封存、-v 顯示細節，再加上 --delete，讓 B 完全對齊 A。"),
    R("rsync -a -v --delete A/ B/"),
    S("注意這一行，多餘的 obsolete 檔案被刪掉了，這個選項要小心使用。"),

    CLR(key="用 --exclude 跳過不要的檔",
        hero="rsync -a -v --exclude='*.log' --exclude='.cache/' A/ C/", toks=[
        ("-a", "封存模式，保留結構", "ord"),
        ("-v", "顯示細節", "ord"),
        ("--exclude", "排除符合樣式的檔案，可重複（*.log、.cache/）", "star"),
        ("A/ C/", "這次目標是新資料夾 C", "path")]),
    S("有些檔案我們並不想同步，例如快取和日誌。"),
    S("用 -a 封存、-v 顯示細節，再用 --exclude 排除掉 log 跟 cache，同步到新的 C。"),
    R("rsync -a -v --exclude='*.log' --exclude='.cache/' A/ C/"),
    S("可以看到，cache 目錄和所有的 log 檔，都被跳過了。"),
    R("tree -a C"),
    S("C 裡面乾乾淨淨，只留下我們真正想要的檔案。"),

    CLR(key="-z 壓縮 + 進度顯示", hero="rsync -a -z --info=progress2 A/ C/",
        toks=[
        ("-a", "封存模式", "ord"),
        ("-z", "壓縮資料，節省傳輸頻寬", "star"),
        ("--info=progress2", "顯示整體傳輸進度", "ord"),
        ("A/ C/", "同步到資料夾 C", "path")]),
    S("傳輸大檔，或透過網路同步時，速度就很重要。"),
    S("我先把這個大檔，改得更大一些。"),
    R("head -c 12000000 /dev/urandom > A/data/archive.bin"),
    S("這次用 -a 封存、加上 -z 壓縮，再用 info=progress2 顯示進度，同步到 C。"),
    R("rsync -a -z --info=progress2 A/ C/"),
    S("進度條一路跑到百分之百，大檔也同步完成了。"),

    CLR(key="-i 看懂每行變更", hero="rsync -a -v -i A/ B/", toks=[
        ("-a", "封存模式", "ord"),
        ("-v", "顯示細節", "ord"),
        ("-i", "itemize：每行符號標示變更類型", "star"),
        ("A/ B/", "複製 A 的內容到 B", "path")]),
    S("最後一個技巧，學會看懂 rsync 的輸出。"),
    S("用 -a 封存、-v 顯示細節，最後加上 -i，把每一筆變更都標示出來。"),
    R("rsync -a -v -i A/ B/"),
    S("開頭的符號，會告訴你檔案是新增、更新，還是只有屬性改變。"),
    S("掌握這幾招，你就能應付大多數的 rsync 情境了。"),
]


def parse_srt(path):
    def t2s(t):
        h, m, r = t.split(":")
        s, ms = r.split(",")
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


def main():
    says = [i[1] for i in SCRIPT if i[0] == "say"]
    text = "".join(says)
    os.makedirs(AUDIO, exist_ok=True)
    mp3, srt = f"{AUDIO}/voice.mp3", f"{AUDIO}/voice.srt"
    if not (os.path.exists(mp3) and os.path.exists(srt)):
        subprocess.run(["edge-tts", "--voice", VOICE, "--rate", RATE,
                        "--text", text, "--write-media", mp3,
                        "--write-subtitles", srt], check=True)
    D = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", mp3], capture_output=True, text=True).stdout)
    cues = parse_srt(srt)
    if len(cues) != len(says):
        print(f"WARNING cue/sentence mismatch: {len(cues)} vs {len(says)}")
        for i, c in enumerate(cues):
            print(f"  cue{i}: {c[2]}")
        return

    tape = [
        "# Auto-generated by build.py — one continuous narration + panel data.",
        "Output rsync-demo.mp4",
        "Set Shell zsh",
        "Set FontSize 26", "Set Width 1200", "Set Height 1080",
        'Set Theme "Catppuccin Mocha"',
        # keep Set at 45ms (the config measured to yield ~24ms/char real); TS
        # models that real rate, so don't derive this from TS.
        "Set TypingSpeed 45ms", "Set Padding 28", "",
        # enable `#` comments AND clear, all hidden, so t=0 opens on a clean
        # prompt (no leftover `setopt ...` line visible at the start).
        "Hide", 'Type "setopt interactive_comments"', "Enter",
        'Type "clear"', "Enter", "Sleep 200ms", "Show", "",
    ]
    vt = 0.0

    def sleep_to(target):
        nonlocal vt
        dt = target - vt
        if dt > 0.02:
            tape.append(f"Sleep {round(dt, 2)}s")
            vt = target

    sleep_to(INITIAL)
    si = -1
    panels, cur, cur_toks = [], None, []

    def finalize(end):
        if cur:
            cur["show_to"] = round(end, 3)
            panels.append(cur)

    for item in SCRIPT:
        kind = item[0]
        if kind == "say":
            si += 1
        elif kind == "clear":
            b = cues[si][1] if si >= 0 else 0.0
            sleep_to(INITIAL + b)
            tape += ["Hide", 'Type "clear"', "Enter", "Sleep 120ms", "Show"]
            finalize(INITIAL + b)
            _, key, hero, toks = item
            cur = (dict(banner=round(INITIAL + b, 3), key=key, hero=hero,
                        cmd=None, cmd_start=None, tokens=[]) if key else None)
            cur_toks = toks
        elif kind == "run":
            cmd = item[1]
            cs, ce = cues[si][0], cues[si][1]
            sleep_to(INITIAL + cs)
            is_hero = cur is not None and cur["hero"] == cmd and cur_toks
            if is_hero:
                pos, spec = 0, []
                for sub, ann, role in cur_toks:
                    idx = cmd.find(sub, pos); end = idx + len(sub); pos = end
                    spec.append((idx, end, sub, ann, role))
                # Type each token so it lands *when the voice names that flag* —
                # spread across the explain sentence, not clustered at the start.
                # Find where the flag is spoken (its char position in the
                # sentence) and map that to a time inside the cue.
                text = cues[si][2]; L = max(1, len(text)); dur = ce - cs
                n = len(spec)

                def vfrac(sub, role, i):
                    for key in (sub, sub.lstrip("-"), sub.split("=")[0].lstrip("-")):
                        if key and key in text:
                            return text.index(key) / L
                    if role == "path" and "A" in text:
                        return text.index("A") / L
                    return (i + 1) / (n + 1)            # even-spread fallback

                vrel, prevv = [], 0.0
                for i, (idx, end, sub, ann, role) in enumerate(spec):
                    v = max(prevv + 0.4, vfrac(sub, role, i) * dur)
                    v = min(v, dur - 0.2)               # leave a beat before <CR>
                    vrel.append(v); prevv = v
                prefix = cmd[:spec[0][0]]
                tape.append(f'Type "{prefix}"')
                vt += len(prefix) * TS
                prev = spec[0][0]
                cur["cmd"] = cmd
                cur["cmd_start"] = round(INITIAL + cs, 3)
                for (idx, end, sub, ann, role), v in zip(spec, vrel):
                    chunk = cmd[prev:end]
                    sleep_to(INITIAL + cs + v - len(chunk) * TS)  # land at voice
                    tape.append(f'Type "{chunk}"')
                    vt += len(chunk) * TS
                    prev = end
                    cur["tokens"].append(dict(label=sub, ann=ann, role=role,
                                              cs=idx, ce=end, reveal=round(vt, 3)))
                if cmd[prev:]:
                    tape.append(f'Type "{cmd[prev:]}"')
                    vt += len(cmd[prev:]) * TS
            else:
                tape.append(f'Type "{cmd}"')
                vt += len(cmd) * TS
            sleep_to(INITIAL + ce)               # hold until the sentence ends
            tape.append("Enter")
            vt += ENTER
            sleep_to(vt + OUTPUT_MIN)
    sleep_to(INITIAL + D)
    tape += [f"Sleep {TAIL}s", ""]
    total = vt + TAIL
    finalize(total)

    open(f"{DEMO}/demo.tape", "w").write("\n".join(tape))
    json.dump(dict(predicted_total=round(total, 3), anchor=INITIAL, mp3=mp3,
                   narration_dur=round(D, 3),
                   cues=[[round(a, 3), round(b, 3), x] for a, b, x in cues],
                   panels=panels),
              open(f"{DEMO}/timeline.json", "w"), ensure_ascii=False, indent=2)
    print(f"predicted total = {total:.1f}s, narration = {D:.1f}s, "
          f"{len(cues)} sentences, {len(panels)} panels")


if __name__ == "__main__":
    main()
