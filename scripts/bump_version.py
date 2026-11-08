#!/usr/bin/env python3
"""Flutter Release Kit - version bumper.
Author: Chandra ObulaReddy (ChandraChaan)

Usage:
  bump_version.py (major|minor|patch|build|exact X.Y.Z[+N]) [--pubspec PATH]
                  [--changelog PATH] [--no-changelog] [--dry-run]

Rules:
  * version is kept in the form X.Y.Z+BUILD
  * the build number ALWAYS increases by one (stores reject a reused build)
  * major/minor/patch reset the lower parts to 0
  * if CHANGELOG.md has an "## [Unreleased]" section it becomes the new version
    section, otherwise a new dated section is inserted at the top
"""
import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r"^(version:\s*)(['\"]?)(\d+)\.(\d+)\.(\d+)(?:\+(\d+))?(['\"]?)(\s*(?:#.*)?)$", re.M)


def bump(old, part):
    major, minor, patch, build = old
    build = (build or 0) + 1
    if part == "major":
        return (major + 1, 0, 0, build)
    if part == "minor":
        return (major, minor + 1, 0, build)
    if part == "patch":
        return (major, minor, patch + 1, build)
    if part == "build":
        return (major, minor, patch, build)
    raise ValueError(part)


def parse_exact(value, old_build):
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\+(\d+))?", value)
    if not m:
        sys.exit(f"error: '{value}' is not X.Y.Z or X.Y.Z+N")
    major, minor, patch, build = m.groups()
    build = int(build) if build else (old_build or 0) + 1
    return (int(major), int(minor), int(patch), build)


def fmt(v):
    return f"{v[0]}.{v[1]}.{v[2]}+{v[3]}"


def update_changelog(path: Path, new_semver: str, dry_run: bool) -> str:
    today = _dt.date.today().isoformat()
    heading = f"## [{new_semver}] - {today}"
    if not path.exists():
        text = (
            "# Changelog\n\nAll notable changes to this project are documented here.\n\n"
            f"{heading}\n\n### Added\n- \n\n### Changed\n- \n\n### Fixed\n- \n"
        )
        action = f"created {path} with section {new_semver}"
    else:
        text = path.read_text(encoding="utf-8")
        if re.search(r"^## \[Unreleased\]", text, re.M):
            text = re.sub(r"^## \[Unreleased\].*$", heading, text, count=1, flags=re.M)
            action = f"renamed [Unreleased] to {new_semver} in {path}"
        elif f"[{new_semver}]" in text:
            return f"{path} already has a {new_semver} section"
        else:
            m = re.search(r"^## ", text, re.M)
            block = f"{heading}\n\n### Added\n- \n\n### Changed\n- \n\n### Fixed\n- \n\n"
            if m:
                text = text[: m.start()] + block + text[m.start():]
            else:
                text = text.rstrip("\n") + "\n\n" + block
            action = f"inserted {new_semver} section into {path}"
    if not dry_run:
        path.write_text(text, encoding="utf-8")
    return action


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("part", help="major | minor | patch | build | exact")
    ap.add_argument("value", nargs="?", help="explicit version when part is 'exact'")
    ap.add_argument("--pubspec", default="pubspec.yaml")
    ap.add_argument("--changelog", default="CHANGELOG.md")
    ap.add_argument("--no-changelog", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pubspec = Path(args.pubspec)
    if not pubspec.exists():
        sys.exit(f"error: {pubspec} not found (run from the Flutter project root)")
    text = pubspec.read_text(encoding="utf-8")
    m = VERSION_RE.search(text)
    if not m:
        sys.exit("error: no 'version: X.Y.Z+N' line found in pubspec.yaml")

    old = (int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)) if m.group(6) else None)
    if args.part == "exact":
        if not args.value:
            sys.exit("error: 'exact' needs a version, e.g. exact 2.1.0+15")
        new = parse_exact(args.value, old[3])
    elif args.part in ("major", "minor", "patch", "build"):
        new = bump(old, args.part)
    else:
        sys.exit(f"error: unknown part '{args.part}'")

    if new[3] > 2_100_000_000:
        sys.exit("error: build number exceeds Google Play's versionCode limit (2100000000)")

    old_str = f"{old[0]}.{old[1]}.{old[2]}" + (f"+{old[3]}" if old[3] is not None else "")
    new_text = text[: m.start()] + f"{m.group(1)}{fmt(new)}{m.group(8)}" + text[m.end():]
    if not args.dry_run:
        pubspec.write_text(new_text, encoding="utf-8")

    print(f"pubspec.yaml: {old_str} -> {fmt(new)}" + ("  (dry run)" if args.dry_run else ""))
    if not args.no_changelog:
        print("changelog:    " + update_changelog(Path(args.changelog), f"{new[0]}.{new[1]}.{new[2]}", args.dry_run))
    print(f"next:         git commit -am \"chore: release {fmt(new)}\" && git tag v{new[0]}.{new[1]}.{new[2]}")


if __name__ == "__main__":
    main()
