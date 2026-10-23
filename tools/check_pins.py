#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check that every pinned GitHub project's commit is on its upstream branch.

  tools/check_pins.py [--android 4.4|6.0]

For each project of the track's top manifest (default.xml or android-6.0.xml), asks GitHub's
compare API whether `revision` is the head of `upstream` or an ancestor of it. For an AOSP
project (remote aosp), `upstream` is a tag and `revision` must be the commit it names
(`git ls-remote` on android.googlesource.com). A pin that is
only on a pull request branch, or on no branch, fails: merge the pull request first and pin its
merge commit. Needs network access; set GITHUB_TOKEN (or GH_TOKEN) for GitHub's higher rate
limit. Prints one line per project and exits 1 if any pin is off its branch.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_manifest import TRACKS  # noqa: E402

API = "https://api.github.com"
AOSP = "https://android.googlesource.com/"


def github_compare(repo, base, head):
    """Status of head against base: identical, behind (head is an ancestor), ahead, diverged."""
    url = (f"{API}/repos/{repo}/compare/{urllib.parse.quote(base, safe='')}..."
           f"{urllib.parse.quote(head, safe='')}?per_page=1")
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "openmyglass-check-pins"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["status"]
    except urllib.error.HTTPError as e:
        return f"error {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return f"error {getattr(e, 'reason', e)}"


def aosp_tag_commit(name, tag):
    """The commit an AOSP tag names (peeled), or None."""
    try:
        out = subprocess.run(["git", "ls-remote", AOSP + name, tag, tag + "^{}"],
                             capture_output=True, text=True, timeout=120, check=True).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    refs = dict(line.split("\t")[::-1] for line in out.splitlines() if "\t" in line)
    return refs.get(tag + "^{}") or refs.get(tag)


def check(root=ROOT, android="4.4", compare=github_compare, tag_commit=aosp_tag_commit):
    top = ET.parse(root / TRACKS[android]["top"]).getroot()
    lines, problems = [], []
    for p in top.iter("project"):
        name, path = p.get("name"), p.get("path") or p.get("name")
        rev, branch = p.get("revision") or "", p.get("upstream") or ""
        if p.get("remote") == "aosp":
            commit = tag_commit(name, branch)
            status = "identical" if commit == rev else f"tag names {commit}"
        elif p.get("remote") == "github":
            status = compare(name, branch, rev)
        else:
            continue
        line = f"{path}: {rev[:12]} on {name} {branch}: {status}"
        if status in ("identical", "behind"):
            lines.append("ok   " + line)
        else:
            lines.append("FAIL " + line)
            problems.append(line)
    return lines, problems


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--android", choices=sorted(TRACKS), default="4.4")
    args = ap.parse_args(argv)
    lines, problems = check(android=args.android)
    print("\n".join(lines))
    if problems:
        print(f"{len(problems)} pin(s) not on their upstream branch (ahead or diverged: on a "
              "pull request branch or no branch; or the commit or branch not found)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
