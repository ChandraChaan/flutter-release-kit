#!/usr/bin/env python3
"""Flutter Release Kit - changelog generator.
Author: Chandra ObulaReddy <https://github.com/ChandraChaan>

Usage: changelog.py [--since REF] [--store] [--max N]
  default range : last tag..HEAD (whole history when no tag exists)
  --since REF   : explicit start ref (tag, commit, branch)
  --store       : plain "What's new" text for store release notes (<= 500 chars)
  --max N       : cap on bullets per section (default 30)
"""
import argparse
import datetime as _dt
import re
import subprocess
import sys


def git(*args):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def pubspec_version():
    try:
        with open("pubspec.yaml", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("version:"):
                    return line.split(":", 1)[1].strip().strip("'\"").split("+")[0]
    except OSError:
        pass
    return None


SECTIONS = [
    ("feat", "Added"),
    ("fix", "Fixed"),
    ("perf", "Performance"),
    ("refactor", "Changed"),
    ("other", "Changed"),
    ("docs", "Docs"),
    ("chore", "Internal"),
]
CHORE_TYPES = {"chore", "build", "ci", "test", "style"}
PREFIX_RE = re.compile(r"^([a-z]+)(\([^)]*\))?!?:\s*(.*)$")
RELEASE_RE = re.compile(r"^(chore(\([^)]*\))?:\s*(release|bump|version)|merge )", re.I)


def classify(subject):
    m = PREFIX_RE.match(subject)
    if not m:
        return "other", subject
    kind, _, rest = m.groups()
    if kind in CHORE_TYPES:
        kind = "chore"
    elif kind not in {"feat", "fix", "perf", "refactor", "docs"}:
        kind = "other"
    return kind, rest


def capitalize(text):
    return text[:1].upper() + text[1:] if text else text


def lower_first(text):
    return text[:1].lower() + text[1:] if text else text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=None)
    ap.add_argument("--store", action="store_true")
    ap.add_argument("--max", type=int, default=30)
    args = ap.parse_args()

    if git("rev-parse", "--is-inside-work-tree") is None:
        sys.exit("error: not a git repository")

    since = args.since or git("describe", "--tags", "--abbrev=0") or ""
    rev_range = f"{since}..HEAD" if since else "HEAD"
    log = git("log", "--no-merges", "--pretty=format:%s|%h", rev_range)
    if not log:
        print(f"No commits in range {rev_range}.")
        return

    groups = {key: [] for key, _ in SECTIONS}
    for line in log.splitlines():
        subject, _, short_hash = line.rpartition("|")
        if RELEASE_RE.match(subject):
            continue
        kind, rest = classify(subject)
        groups[kind].append((capitalize(rest), short_hash))

    if args.store:
        out = ""
        plan = [("feat", ""), ("fix", "Fixed: "), ("perf", "Faster: ")]
        for kind, prefix in plan:
            for text, _ in groups[kind]:
                bullet = "• " + (prefix + lower_first(text) if prefix else text) + "\n"
                if len(out) + len(bullet) > 500:
                    break
                out += bullet
        if not out:
            out = "• Bug fixes and performance improvements\n"
        sys.stdout.write(out)
        return

    version = pubspec_version() or "Unreleased"
    print(f"## [{version}] - {_dt.date.today().isoformat()}\n")
    if since:
        print(f"_Changes since {since}_\n")
    emitted = set()
    for kind, title in SECTIONS:
        items = groups[kind]
        if kind == "refactor":
            items = groups["refactor"] + groups["other"]
        elif kind == "other":
            continue
        if not items or title in emitted:
            continue
        emitted.add(title)
        print(f"### {title}")
        for text, short_hash in items[: args.max]:
            print(f"- {text} ({short_hash})")
        if len(items) > args.max:
            print(f"- ...and {len(items) - args.max} more")
        print()


if __name__ == "__main__":
    main()
