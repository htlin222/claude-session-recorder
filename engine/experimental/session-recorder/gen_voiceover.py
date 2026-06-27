#!/usr/bin/env python3
"""Post-hoc: turn a recorded session timeline into a TIMECODE-MATCHED voiceover.

Reads session-timeline.jsonl (written by timelog.py while a Claude Code session
ran), computes each event's time RELATIVE to the first event, writes a narration
line per event placed at that timecode. So when you replay the session, the voice
explains exactly what's happening as it happens.

Outputs:
  session-voiceover.srt   always — timecode -> zh-TW line (the script / subtitles)
  session-voiceover.mp3    with --audio — each line synthesized (edge-tts) and
                           placed at its timecode on one silent track (ffmpeg)

Usage:  python3 gen_voiceover.py [--audio] [--all]
  --all  narrate every logged event (default: a curated, less chatty subset)
"""
import argparse
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "session-timeline.jsonl")
FF = "/opt/homebrew/bin/ffmpeg"
VOICE = "zh-TW-HsiaoChenNeural"

# events spoken by default (others are timing-only unless --all)
SPOKEN = {"SessionStart", "UserPromptSubmit", "PreToolUse", "SubagentStart",
          "Stop", "SessionEnd"}
TOOL_VERB = {"Bash": "執行終端指令", "Read": "讀取檔案", "Edit": "編輯檔案",
             "Write": "寫入檔案", "Grep": "搜尋程式碼內容", "Glob": "尋找檔案",
             "Task": "派出子代理", "WebFetch": "抓取網頁", "WebSearch": "上網搜尋",
             "TodoWrite": "更新待辦清單"}


def phrase(row):
    ev = row["event"]
    detail = row.get("detail", "")
    if ev in ("Stop", "SubagentStop"):
        # ★ the turn's final message — the most important line to narrate
        msg = (row.get("message") or "").strip()
        if msg:
            first = re.split(r"[。！？\n]", msg)[0].strip()[:70]
            who = "子代理" if ev == "SubagentStop" else "Claude"
            return f"{who} 的結論：{first}。"
        return "Claude 完成這一輪回應。"
    if ev == "SessionStart":
        return "工作階段開始。"
    if ev == "UserPromptSubmit":
        return "你送出了一個請求。"
    if ev == "PreToolUse":
        tool, _, rest = detail.partition(" ")
        verb = TOOL_VERB.get(tool, f"使用 {tool}")
        rest = rest.strip()
        return f"{verb}：{rest[:32]}" if rest else f"{verb}。"
    if ev == "PostToolUse":
        return "工具執行完成。"
    if ev == "SubagentStart":
        return f"開始一個子代理{('：' + detail) if detail else ''}。"
    if ev == "Notification":
        return f"通知：{detail}" if detail else "出現一則通知。"
    if ev == "SessionEnd":
        return "工作階段結束。"
    return detail or ev


def srt_ts(s):
    h = int(s // 3600); s -= h * 3600
    m = int(s // 60); s -= m * 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
    if not rows:
        raise SystemExit(f"empty timeline: {LOG}")
    t0 = rows[0]["t"]
    cues = []
    for i, r in enumerate(rows):
        if not a.all and r["event"] not in SPOKEN:
            continue
        rel = r["t"] - t0
        end = (rows[i + 1]["t"] - t0) if i + 1 < len(rows) else rel + 3.0
        # the Stop conclusion is important — give it a longer dwell
        cap = 9.0 if r["event"] in ("Stop", "SubagentStop") else 6.0
        end = max(rel + 1.4, min(end, rel + cap))
        cues.append((rel, end, phrase(r)))

    srt = os.path.join(HERE, "session-voiceover.srt")
    with open(srt, "w", encoding="utf-8") as f:
        for n, (a0, b0, txt) in enumerate(cues, 1):
            f.write(f"{n}\n{srt_ts(a0)} --> {srt_ts(b0)}\n{txt}\n\n")
    print(f"wrote {srt}  ({len(cues)} cues, span {cues[-1][1]:.1f}s)")

    if not a.audio:
        print("(add --audio to synthesize the timed narration track)")
        return
    # synthesize each line, place it at its timecode on one silent track
    seg = os.path.join(HERE, "_seg")
    os.makedirs(seg, exist_ok=True)
    inputs, filt, mix = [], [], []
    for i, (rel, _b, txt) in enumerate(cues):
        mp3 = f"{seg}/{i}.mp3"
        subprocess.run(["edge-tts", "--voice", VOICE, "--text", txt,
                        "--write-media", mp3], check=True)
        inputs += ["-i", mp3]
        filt.append(f"[{i}:a]adelay={int(rel*1000)}|{int(rel*1000)}[a{i}]")
        mix.append(f"[a{i}]")
    total = cues[-1][1] + 1.0
    out = os.path.join(HERE, "session-voiceover.mp3")
    fc = ";".join(filt) + ";" + "".join(mix) + \
        f"amix=inputs={len(cues)}:normalize=0:dropout_transition=0,apad=whole_dur={total:.2f},atrim=end={total:.2f}[a]"
    subprocess.run([FF, "-y", *inputs, "-filter_complex", fc, "-map", "[a]",
                    "-c:a", "libmp3lame", "-q:a", "4", out], check=True,
                   capture_output=True)
    print(f"wrote {out}  ({total:.1f}s, narration placed at each event's timecode)")


if __name__ == "__main__":
    main()
