#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check a manifest: AOSP base unchanged, removals real, every outside project pinned.

  tools/check_manifest.py [--android 4.4|6.0] [--upstream FILE]

--android picks the manifest: 4.4 (Track A, default.xml over aosp.xml, the default) or 6.0
(Track B, android-6.0.xml over aosp-6.0.xml). --upstream is AOSP's default.xml at that track's
tag (platform/manifest); with it, the AOSP file must equal it except for the remote's fetch URL.
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AOSP_FETCH = "https://android.googlesource.com/"
SHA = re.compile(r"[0-9a-f]{40}")
# GitHub organisations a project may come from, and why (docs/kitkat-base.md,
# docs/marshmallow-base.md).
ORGS = {
    "OpenMyGlass": "our repositories, forks and mirrors",
    "omap4-aosp": "OMAP4 hardware (later Unlegacy-Android)",
}
DEVICE = ("device/glass/glass-1", "OpenMyGlass/android_device_glass_glass-1")
# Groups that the documented repo init leaves out.
EXCLUDED_GROUPS = {"device", "darwin", "mips", "x86", "notdefault"}
# Per track: the AOSP file and tag, the top file, our patched forks (path -> repository), and
# the branch of the unmodified android-security mirrors (every other OpenMyGlass project).
TRACKS = {
    "4.4": {
        "aosp": "aosp.xml",
        "top": "default.xml",
        "tag": "refs/tags/android-4.4.4_r2.0.1",
        "forks": {
            "art": "OpenMyGlass/android_art",
            "build": "OpenMyGlass/android_build",
            "frameworks/native": "OpenMyGlass/android_frameworks_native",
            "libnativehelper": "OpenMyGlass/android_libnativehelper",
        },
        "mirror_branch": "aosp-4.4",
        "device_branch": "android-4.4.4",
    },
    "6.0": {
        "aosp": "aosp-6.0.xml",
        "top": "android-6.0.xml",
        "tag": "refs/tags/android-6.0.1_r81",
        "forks": {
            "build": "OpenMyGlass/android_build",
            "frameworks/av": "OpenMyGlass/android_frameworks_av",
            "frameworks/native": "OpenMyGlass/android_frameworks_native",
        },
        "fork_branch": "glass-6.0",
        "mirror_branch": "aosp-6.0",
        "device_branch": "android-6.0.1_r31",
    },
}
# Track A names, kept for callers.
AOSP_TAG = TRACKS["4.4"]["tag"]
FORKS = TRACKS["4.4"]["forks"]
MIRROR_BRANCH = TRACKS["4.4"]["mirror_branch"]


def mirror_name(path):
    return "OpenMyGlass/android_" + (path or "").replace("/", "_")


def expected_aosp(upstream_text):
    return upstream_text.replace('fetch=".."', f'fetch="{AOSP_FETCH}"', 1)


def check(root=ROOT, upstream_text=None, android="4.4"):
    t = TRACKS[android]
    af, tf, tag, forks = t["aosp"], t["top"], t["tag"], t["forks"]
    problems = []
    aosp_text = (root / af).read_text()
    aosp = ET.fromstring(aosp_text)
    top = ET.parse(root / tf).getroot()

    if upstream_text is not None and aosp_text != expected_aosp(upstream_text):
        problems.append(f"{af} differs from AOSP's default.xml beyond the fetch URL")
    remotes = {r.get("name"): r.get("fetch") for r in aosp.iter("remote")}
    if remotes != {"aosp": AOSP_FETCH}:
        problems.append(f"{af} remotes {remotes}, want aosp={AOSP_FETCH}")
    default = aosp.find("default")
    if default is None or default.get("revision") != tag:
        problems.append(f"{af} default revision is not {tag}")

    if [i.get("name") for i in top.iter("include")] != [af]:
        problems.append(f"{tf} must include {af} and nothing else")
    top_remotes = {r.get("name"): r.get("fetch") for r in top.iter("remote")}
    if top_remotes != {"github": "https://github.com/"}:
        problems.append(f"{tf} remotes {top_remotes}, want github=https://github.com/")

    projects = {p.get("name"): p for p in aosp.iter("project")}
    paths = {p.get("path") or p.get("name"): p.get("name") for p in aosp.iter("project")}
    removed = []
    for rp in top.iter("remove-project"):
        name = rp.get("name")
        if name not in projects:
            problems.append(f"remove-project {name}: not in {af}")
        elif name in removed:
            problems.append(f"remove-project {name}: twice")
        else:
            removed.append(name)
            del paths[projects[name].get("path") or name]

    for p in top.iter("project"):
        name, path, rev = p.get("name"), p.get("path"), p.get("revision") or ""
        where = f"project {path}"
        if p.get("remote") != "github":
            problems.append(f"{where}: remote must be github")
        org = name.split("/", 1)[0]
        if org not in ORGS:
            problems.append(f"{where}: organisation {org} is not one of {sorted(ORGS)}")
        if not SHA.fullmatch(rev):
            problems.append(f"{where}: revision {rev!r} is not a 40-hex commit")
        if not p.get("upstream"):
            problems.append(f"{where}: no upstream branch")
        if path in paths:
            problems.append(f"{where}: path already used by {paths[path]} (remove it first)")
        paths[path] = name
        groups = set((p.get("groups") or "").split(",")) - {""}
        if groups & EXCLUDED_GROUPS:
            problems.append(f"{where}: in excluded groups {sorted(groups & EXCLUDED_GROUPS)}")
        if path in forks and "fork_branch" in t and p.get("upstream") != t["fork_branch"]:
            problems.append(f"{where}: fork must have upstream {t['fork_branch']}")
        if (path, name) == DEVICE and p.get("upstream") != t["device_branch"]:
            problems.append(f"{where}: device tree must have upstream {t['device_branch']}")
        if org == "OpenMyGlass" and path not in forks and (path, name) != DEVICE:
            if name != mirror_name(path):
                problems.append(f"{where}: OpenMyGlass mirror must be {mirror_name(path)}")
            if p.get("upstream") != t["mirror_branch"]:
                problems.append(f"{where}: OpenMyGlass mirror must have upstream {t['mirror_branch']}")
    for path, name in list(forks.items()) + [DEVICE]:
        if paths.get(path) != name:
            problems.append(f"{path}: must be {name}, is {paths.get(path)}")
    return problems


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--android", choices=sorted(TRACKS), default="4.4")
    ap.add_argument("--upstream", type=Path)
    args = ap.parse_args(argv)
    upstream = args.upstream.read_text() if args.upstream else None
    problems = check(upstream_text=upstream, android=args.android)
    for p in problems:
        print(p)
    if not problems:
        t = TRACKS[args.android]
        print(f"{t['top']} ok" + (f" ({t['aosp']} matches upstream)" if upstream else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
