#!/usr/bin/env python3
"""strategies.py — one SegmentStrategy per segment KIND (the controllability axis).

The capture's timeline is partitioned by detect_anchors.raw_segments into segments
of three kinds; each kind is re-timed differently by splice. `boot` and `hard` are
VERBATIM (copied frame-for-frame — their length is fixed by what was recorded);
`soft` is FREEZE-STRETCHABLE (a static idle region held to whatever the authored
voice needs). Encapsulating each kind's behavior here means adding a new region
type (a future long-running external command, streaming output, …) is one new
strategy + registry entry, not edits scattered across `if kind == …` sites."""


class SegmentStrategy:
    kind = None
    verbatim = None      # True: copied frame-for-frame; False: freeze-stretchable

    def splice_ops(self, seg):
        """Return the ordered ffmpeg op dicts that realize `seg` in the spliced
        video. Each op is {"op": "copy"|"freeze", "raw": [a,b], ...}."""
        raise NotImplementedError


class HardStrategy(SegmentStrategy):
    """typing -> submit -> done. Claude drives the length (the nondeterministic
    think/work gap); copy it verbatim."""
    kind = "hard"
    verbatim = True

    def splice_ops(self, seg):
        return [{"op": "copy", "raw": list(seg["raw"])}]


class BootStrategy(SegmentStrategy):
    """The launch/boot animation. Copy verbatim; if the authored out_dur exceeds
    the captured length (the launch outro rides a touch past boot), hold the last
    static frame for the remainder — never freeze the animation itself."""
    kind = "boot"
    verbatim = True

    def splice_ops(self, seg):
        raw_len = seg["raw"][1] - seg["raw"][0]
        ops = [{"op": "copy", "raw": list(seg["raw"])}]
        extra = round(seg.get("out_dur", raw_len) - raw_len, 3)
        if extra > 0.01:
            ops.append({"op": "freeze", "raw": list(seg["raw"]),
                        "at": "end", "out_dur": extra})
        return ops


class SoftStrategy(SegmentStrategy):
    """A static idle region (post-boot, between turns, tail). Replace with a
    single-frame freeze held for the authored out_dur (stretch OR trim).

    The TAIL is special: its raw range runs from the last turn's `done` THROUGH
    the Ctrl+C teardown into the post-exit blank shell. The globally-calmest frame
    there is the blank shell (more static than the result), so a naive freeze ends
    the video on a blank screen while the outro/close narrate. Mark the tail to
    freeze from the START (the settled RESULT, before teardown) instead."""
    kind = "soft"
    verbatim = False

    def splice_ops(self, seg):
        raw_len = seg["raw"][1] - seg["raw"][0]
        op = {"op": "freeze", "raw": list(seg["raw"]),
              "out_dur": round(seg.get("out_dur", raw_len), 3)}
        if seg.get("role") == "tail":
            op["freeze_from"] = "start"      # hold the result, not the teardown
        return [op]


_STRATEGIES = [HardStrategy(), BootStrategy(), SoftStrategy()]
REGISTRY = {s.kind: s for s in _STRATEGIES}


def strategy_for_kind(kind):
    try:
        return REGISTRY[kind]
    except KeyError:
        raise KeyError(f"no SegmentStrategy for segment kind {kind!r} "
                       f"(known: {sorted(REGISTRY)})")


def strategy_for(seg):
    return strategy_for_kind(seg["kind"])
