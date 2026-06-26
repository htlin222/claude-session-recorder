#!/usr/bin/env python3
"""Deterministic environment probe for a lesson's CLI tools.

The /clip workflow runs this between Design and Author so tool selection is
FACT-driven, not guessed from the model's platform memory: for each command it
reports whether it exists and whether it's the GNU build or a divergent variant
(macOS BSD, busybox), and points at a GNU alternative (gsed/gawk/gdate...) when
the default differs from Linux. Same machine -> same output (deterministic).

Usage:  python3 src/envcheck.py <cmd> [cmd ...]      # first cmd = PRIMARY
Output: aligned human lines + one machine line  `ENV_JSON [ {...}, ... ]`.
Exit 2 if the PRIMARY tool is missing (so the workflow fails fast, before render).
"""
import json
import shutil
import subprocess
import sys


def _first_line(cmd_argv):
    try:
        out = subprocess.run(cmd_argv, capture_output=True, text=True, timeout=5).stdout
        lines = out.splitlines()
        return lines[0] if lines else ""
    except Exception:                                   # noqa: BLE001
        return ""


def probe(cmd):
    if not shutil.which(cmd):
        return dict(cmd=cmd, present=False, flavor="missing", version="",
                    gnu_alt=None, recommend=f"'{cmd}' is NOT installed")
    ver = _first_line([cmd, "--version"])
    if "gnu" in ver.lower():
        return dict(cmd=cmd, present=True, flavor="gnu", version=ver,
                    gnu_alt=None, recommend=f"use `{cmd}` as-is (GNU = matches Linux)")
    # not GNU — is a GNU alternative `g<cmd>` installed?
    galt = f"g{cmd}"
    if shutil.which(galt) and "gnu" in _first_line([galt, "--version"]).lower():
        return dict(cmd=cmd, present=True, flavor="bsd", version=ver or "(BSD/variant)",
                    gnu_alt=galt,
                    recommend=(f"use `{galt}` (GNU); the default `{cmd}` here is "
                               f"BSD/variant and DIFFERS from Linux — note the split in the intro"))
    flv = "busybox" if "busybox" in ver.lower() else "other"
    return dict(cmd=cmd, present=True, flavor=flv, version=ver or "(no --version)",
                gnu_alt=None,
                recommend=(f"`{cmd}`: no GNU/BSD split detected; likely uniform across "
                           f"platforms, but verify any doubtful command both ways"))


def main():
    tools = sys.argv[1:]
    if not tools:
        print("usage: envcheck.py <cmd> [cmd ...]", file=sys.stderr)
        sys.exit(1)
    res = [probe(t) for t in tools]
    for r in res:
        print(f"  {r['cmd']:9} {r['flavor']:8} {r['version'][:46]:46}  -> {r['recommend']}")
    print("ENV_JSON " + json.dumps(res, ensure_ascii=False))
    if res and not res[0]["present"]:
        print(f"[envcheck] PRIMARY tool '{res[0]['cmd']}' missing — cannot render", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
