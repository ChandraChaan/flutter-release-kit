---
name: bump-version
description: Bump the Flutter app version in pubspec.yaml (major, minor, patch or build number) and open a matching CHANGELOG section. Use when the user says "bump version", "new release version", "increase build number", "prepare 2.0", or when release-check reports the current version was already tagged.
argument-hint: "major|minor|patch|build|set X.Y.Z+N [--dry-run]"
allowed-tools: Bash(python3 *), Bash(git *), Read, Edit
---

# Bump version

Flutter keeps one version string in `pubspec.yaml`: `version: 1.4.2+37`. The part before `+` is the user-visible version name (`versionName` / `CFBundleShortVersionString`); the number after `+` is the build number (`versionCode` / `CFBundleVersion`). Stores reject an upload whose build number is not higher than the last one, so the build number must always go up, even for a hotfix.

## Decide the bump

If the user did not say which part, look at what changed since the last tag (`git log $(git describe --tags --abbrev=0)..HEAD --oneline`):

- breaking change, redesign, new major feature set → `major`
- new user-facing features → `minor`
- fixes only → `patch`
- rebuilding the same code for a store re-upload → `build`

Tell the user your choice in one line before running it.

## Run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bump_version.py" $ARGUMENTS
```

Use `--dry-run` first when the user seems unsure. The script:

1. rewrites the `version:` line in `pubspec.yaml`, always incrementing the build number;
2. turns an `## [Unreleased]` section in `CHANGELOG.md` into the new version, or inserts an empty dated section at the top;
3. prints the commit and tag commands.

Pass `--no-changelog` for projects without a changelog that do not want one.

## After the bump

- If the new changelog section has empty bullets, run the `changelog` skill (or draft bullets yourself from the git log) so it is not committed empty.
- Suggest, but do not run unprompted:

```bash
git commit -am "chore: release X.Y.Z+N"
git tag vX.Y.Z
```

- Remind the user that iOS also reads `CFBundleShortVersionString` and `CFBundleVersion` from `$(FLUTTER_BUILD_NAME)` / `$(FLUTTER_BUILD_NUMBER)` in `Info.plist`. If those were hard-coded, the pubspec bump will not reach iOS; fix the plist to use the variables.
