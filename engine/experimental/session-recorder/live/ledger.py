#!/usr/bin/env python3
"""ledger.py — the v6 single source of truth.

A ledger is {"beats": [...], "meta": {...}}. Every downstream stage (splice,
overlay, panel, lint) reads it; nobody re-derives a time it already holds. See
docs/plans/2026-06-28-event-ledger-deterministic-pipeline-design.md.
"""
import hashlib
import json

BREATH = 0.5     # min silence between consecutive beats (== v5 MIN_GAP)


def beat_id(kind, turn_idx, payload):
    """sha1(kind|turn_idx|payload)[:6] — stable across re-authoring so a beat's
    identity survives editing its sibling beats."""
    h = hashlib.sha1(f"{kind}|{turn_idx}|{payload}".encode("utf-8"))
    return h.hexdigest()[:6]


def beat_end(beat):
    """The moment every channel of this beat has quiesced (design's
    `beat.end = max(voice.end, visual.end, panel activity end)`). A channel that
    is None/absent contributes nothing."""
    ends = []
    v = beat.get("voice")
    if v:
        ends.append(v["end"])
    vis = beat.get("visual")
    if vis:
        ends.append(vis["end"])
    p = beat.get("panel")
    if p and "switch_at" in p:
        ends.append(p["switch_at"])
    return max(ends) if ends else 0.0


def beat_start(beat):
    """The earliest active moment of a beat — min over present channel starts."""
    starts = []
    v = beat.get("voice")
    if v:
        starts.append(v["start"])
    vis = beat.get("visual")
    if vis:
        starts.append(vis["start"])
    p = beat.get("panel")
    if p and "switch_at" in p:
        starts.append(p["switch_at"])
    return min(starts) if starts else 0.0


def serialization_violations(beats, breath=BREATH):
    """Return one record per adjacent pair that breaks
    `beat[i].end + breath <= beat[i+1].start`. Dropped beats are excluded.
    Active beats are ordered by their start time before checking."""
    active = sorted((b for b in beats if not b.get("drop")), key=beat_start)
    out = []
    for i in range(1, len(active)):
        gap = round(beat_start(active[i]) - beat_end(active[i - 1]), 3)
        if gap < breath - 0.05:
            out.append({"prev": active[i - 1].get("id"),
                        "next": active[i].get("id"), "gap": gap})
    return out


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, led):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=2)
