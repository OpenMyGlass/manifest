#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check the manifest: AOSP base unchanged, removals real, every outside project pinned.

  tools/check_manifest.py [--upstream FILE]

--upstream is AOSP's default.xml at android-4.4.4_r2.0.1 (platform/manifest); with it, aosp.xml
must equal it except for the remote's fetch URL.
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AOSP_TAG = "refs/tags/android-4.4.4_r2.0.1"
AOSP_FETCH = "https://android.googlesource.com/"
SHA = re.compile(r"[0-9a-f]{40}")
# GitHub organisations a project may come from, and why (docs/kitkat-base.md).
ORGS = {
    "OpenMyGlass": "our repositories, forks and mirrors",
    "omap4-aosp": "OMAP4 hardware (later Unlegacy-Android)",
}
# Our patched forks: path -> repository.
FORKS = {
    "build": "OpenMyGlass/android_build",
    "frameworks/native": "OpenMyGlass/android_frameworks_native",
    "libnativehelper": "OpenMyGlass/android_libnativehelper",
}
DEVICE = ("device/glass/glass-1", "OpenMyGlass/android_device_glass_glass-1")
# Every other OpenMyGlass project is an unmodified mirror of android-security's aosp-4.4.
MIRROR_BRANCH = "aosp-4.4"
# Groups that the documented repo init leaves out.
EXCLUDED_GROUPS = {"device", "darwin", "mips", "x86", "notdefault"}


def mirror_name(path):
    return "OpenMyGlass/android_" + (path or "").replace("/", "_")


def expected_aosp(upstream_text):
    return upstream_text.replace('fetch=".."', f'fetch="{AOSP_FETCH}"', 1)


def check(root=ROOT, upstream_text=None):
    problems = []
    aosp_text = (root / "aosp.xml").read_text()
    aosp = ET.fromstring(aosp_text)
    top = ET.parse(root / "default.xml").getroot()

    if upstream_text is not None and aosp_text != expected_aosp(upstream_text):
        problems.append("aosp.xml differs from AOSP's default.xml beyond the fetch URL")
    remotes = {r.get("name"): r.get("fetch") for r in aosp.iter("remote")}
    if remotes != {"aosp": AOSP_FETCH}:
        problems.append(f"aosp.xml remotes {remotes}, want aosp={AOSP_FETCH}")
    default = aosp.find("default")
    if default is None or default.get("revision") != AOSP_TAG:
        problems.append(f"aosp.xml default revision is not {AOSP_TAG}")

    if [i.get("name") for i in top.iter("include")] != ["aosp.xml"]:
        problems.append("default.xml must include aosp.xml and nothing else")
    top_remotes = {r.get("name"): r.get("fetch") for r in top.iter("remote")}
    if top_remotes != {"github": "https://github.com/"}:
        problems.append(f"default.xml remotes {top_remotes}, want github=https://github.com/")

    projects = {p.get("name"): p for p in aosp.iter("project")}
    paths = {p.get("path") or p.get("name"): p.get("name") for p in aosp.iter("project")}
    removed = []
    for rp in top.iter("remove-project"):
        name = rp.get("name")
        if name not in projects:
            problems.append(f"remove-project {name}: not in aosp.xml")
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
        if org == "OpenMyGlass" and path not in FORKS and (path, name) != DEVICE:
            if name != mirror_name(path):
                problems.append(f"{where}: OpenMyGlass mirror must be {mirror_name(path)}")
            if p.get("upstream") != MIRROR_BRANCH:
                problems.append(f"{where}: OpenMyGlass mirror must have upstream {MIRROR_BRANCH}")
    for path, name in list(FORKS.items()) + [DEVICE]:
        if paths.get(path) != name:
            problems.append(f"{path}: must be {name}, is {paths.get(path)}")
    return problems


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", type=Path)
    args = ap.parse_args(argv)
    upstream = args.upstream.read_text() if args.upstream else None
    problems = check(upstream_text=upstream)
    for p in problems:
        print(p)
    if not problems:
        print("manifest ok" + (" (aosp.xml matches upstream)" if upstream else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
