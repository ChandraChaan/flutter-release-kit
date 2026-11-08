# Flutter Release Kit

[![CI](https://github.com/ChandraChaan/flutter-release-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/ChandraChaan/flutter-release-kit/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) ![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-5A4FCF)

**A Claude Code plugin that gets Flutter apps through Google Play and App Store review the first time.**

Built by [Chandra ObulaReddy](https://github.com/ChandraChaan) after one too many "Your app has been rejected" emails.

Shipping a Flutter app is 10% `flutter build` and 90% remembering the things that get you rejected: a `com.example` package name, a keystore committed to git, an SMS permission Play will never approve, a missing `NSCameraUsageDescription`, a build number you already used. This plugin puts all of that into five skills Claude runs for you, plus a hook that stops secrets from ever reaching a commit.

## What you get

| Skill | What it does |
|---|---|
| `/flutter-release-kit:release-check` | Full preflight: analyzer, tests, version format, git tag collision, changelog entry, debug leftovers, Android signing and package name, iOS bundle id, team, privacy manifest. Verdict: READY or NOT READY with exact fixes. |
| `/flutter-release-kit:bump-version` | `major` / `minor` / `patch` / `build` / `set X.Y.Z+N` on `pubspec.yaml`. Build number always increases. Opens the matching CHANGELOG section. |
| `/flutter-release-kit:changelog` | Changelog section from git history grouped by conventional-commit type, or `--store` for a 500-character "What's new" block. |
| `/flutter-release-kit:store-listing` | Play and App Store copy (title, subtitle, short and full description, keywords, release notes) written from your actual code, with live character counts against every limit. `--review` audits existing copy for policy words and over-length fields. |
| `/flutter-release-kit:permission-audit` | Classifies every Android permission as restricted / sensitive / normal, finds foreground-service and storage mistakes, drafts the Play Console declaration text, and lists the iOS usage-description keys your pubspec plugins need but `Info.plist` lacks. |

Plus a **secret guard hook**: any `git add` or `git commit` that would include `*.jks`, `*.keystore`, `key.properties`, `*.p12`, `*.mobileprovision`, `AuthKey_*.p8`, `.env`, or service-account JSON is blocked with a message telling you what to ignore.

Claude also invokes the skills on its own when you ask things like "is this ready to publish?", "why would Play reject this?", or "write my store description".

## Install

Inside Claude Code:

```
/plugin marketplace add ChandraChaan/flutter-release-kit
/plugin install flutter-release-kit@chandrachaan-plugins
```

Or try it without installing, from a clone:

```bash
claude --plugin-dir ./flutter-release-kit
```

Requirements: Flutter on `PATH` for the analyzer and test steps, `python3` (ships with macOS and most Linux distros) for the version and permission scripts. Everything runs locally; nothing is uploaded anywhere.

## Example session

```
> /flutter-release-kit:release-check --skip-tests

## Version
PASS  Version 1.3.0+12 (name 1.3.0, build 12)
WARN  A git tag for 1.3.0 already exists. Bump the version before publishing again.
## Android
FAIL  applicationId is 'com.example.ledger'. Google Play rejects com.example.* package names.
FAIL  android/key.properties is NOT git-ignored. It holds keystore passwords.
## iOS
WARN  No ios/Runner/PrivacyInfo.xcprivacy. Apple requires a privacy manifest ...

Result: NOT READY.
```

Claude then opens the files, explains each fix, and offers to apply them.

```
> /flutter-release-kit:permission-audit

| Permission | Tier | Notes |
| READ_SMS | restricted | SMS/Call Log policy: only default SMS handler or approved use case (OTP is NOT enough; use SMS Retriever API). |
| WRITE_EXTERNAL_STORAGE | sensitive | Legacy and ignored on API 30+. Add android:maxSdkVersion="29" or remove. |
...
### Missing usage descriptions (from your pubspec dependencies)
- NSLocationWhenInUseUsageDescription ← geolocator
- NSContactsUsageDescription ← flutter_contacts
```

## Scripts

The skills call plain scripts you can also run yourself or in CI:

```bash
scripts/preflight.sh [--skip-tests] [--skip-analyze] [--platform android|ios|all]   # exit 1 on FAIL
scripts/bump_version.py (major|minor|patch|build|set X.Y.Z+N) [--dry-run]
scripts/changelog.sh [--since TAG] [--store]
scripts/permission_audit.py [project_dir] [--json]
```

`preflight.sh` is a good pre-release CI gate; `permission_audit.py --json` feeds dashboards.

## Tests

```bash
bash tests/run.sh
```

Generates a Flutter-shaped fixture with deliberate release mistakes in a temp folder and asserts that every script and the hook catch them. No Flutter SDK needed; CI runs it on Ubuntu and macOS.

## Layout

```
flutter-release-kit/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   ├── release-check/      SKILL.md + references (store rejections, Android signing, privacy manifest)
│   ├── bump-version/
│   ├── changelog/
│   ├── store-listing/      SKILL.md + references (field limits, ASO rules)
│   └── permission-audit/   SKILL.md + references (Android alternatives, iOS usage strings)
├── hooks/hooks.json        PreToolUse guard on Bash
├── scripts/                preflight.sh, bump_version.py, changelog.sh, permission_audit.py, guard_secrets.sh
└── tests/                  make_fixture.sh, run.sh
```

## Roadmap

- Fastlane metadata read/write for `store-listing`
- Screenshot checklist per device class
- Play Developer API upload step
- Localised listing drafts

Ideas and bug reports: [open an issue](https://github.com/ChandraChaan/flutter-release-kit/issues).

## License

MIT © 2026 Chandra ObulaReddy
