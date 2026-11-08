# Flutter Release Kit

[![CI](https://github.com/ChandraChaan/flutter-release-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/ChandraChaan/flutter-release-kit/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) ![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-5A4FCF) [![Release](https://img.shields.io/github/v/release/ChandraChaan/flutter-release-kit?label=version)](https://github.com/ChandraChaan/flutter-release-kit/releases)

**A Claude Code plugin that gets Flutter apps through Google Play and App Store review the first time.**

Built by [Chandra ObulaReddy](https://github.com/ChandraChaan) after one too many "Your app has been rejected" emails.

Shipping a Flutter app is 10% `flutter build` and 90% remembering the things that get you rejected: a `com.example` package name, a keystore committed to git, an SMS permission Play will never approve, a missing `NSCameraUsageDescription`, a build number you already used. This plugin puts all of that into five skills Claude runs for you, plus a hook that stops secrets from ever reaching a commit.

---

## Table of contents

- [Quick start](#quick-start)
- [What you get](#what-you-get)
- [Using the skills](#using-the-skills)
- [The secret guard hook](#the-secret-guard-hook)
- [Use without Claude Code (CI and scripts)](#use-without-claude-code-ci-and-scripts)
- [Updating and uninstalling](#updating-and-uninstalling)
- [Troubleshooting](#troubleshooting)
- [Share it](#share-it)
- [Tests](#tests)
- [Layout](#layout)
- [Roadmap](#roadmap)
- [License](#license)

---

## Quick start

**1. Install** (inside any Claude Code session, terminal or desktop app):

```
/plugin marketplace add ChandraChaan/flutter-release-kit
/plugin install flutter-release-kit@chandrachaan-plugins
```

Restart Claude Code once so the skills and hook load.

**2. Open your Flutter project** in Claude Code (`cd my_app && claude`).

**3. Ask for a release check:**

```
/flutter-release-kit:release-check
```

or just say "is this app ready to publish?". Claude runs the preflight, opens the files behind every finding, and offers to fix them.

**4. Before you upload**, the usual sequence is:

```
/flutter-release-kit:permission-audit
/flutter-release-kit:bump-version minor
/flutter-release-kit:changelog --store
/flutter-release-kit:store-listing
flutter build appbundle --release
```

Requirements: Flutter on `PATH` for the analyzer and test steps, and `python3` (ships with macOS and most Linux distros; on Windows use Git Bash or WSL). Everything runs locally; nothing is uploaded anywhere.

---

## What you get

| Skill | What it does |
|---|---|
| `release-check` | Full preflight: analyzer, tests, version format, git tag collision, changelog entry, debug leftovers, Android signing and package name, iOS bundle id, team, privacy manifest. Verdict: READY or NOT READY with exact fixes. |
| `bump-version` | `major` / `minor` / `patch` / `build` / `set X.Y.Z+N` on `pubspec.yaml`. Build number always increases. Opens the matching CHANGELOG section. |
| `changelog` | Changelog section from git history grouped by conventional-commit type, or `--store` for a 500-character "What's new" block. |
| `store-listing` | Play and App Store copy (title, subtitle, short and full description, keywords, release notes) written from your actual code, with live character counts against every limit. `--review` audits existing copy. |
| `permission-audit` | Classifies every Android permission as restricted / sensitive / normal, including permissions bound on services (notification listener, accessibility, VPN). Finds foreground-service and storage mistakes, drafts Play Console declaration text, and lists the iOS usage-description keys your pubspec plugins need but `Info.plist` lacks. |

Plus a **secret guard hook** that blocks `git add` / `git commit` when a keystore or credentials file would be committed.

Claude also invokes the skills on its own when you ask things like "is this ready to publish?", "why would Play reject this?", or "write my store description". The slash command form is for when you want to be explicit.

---

## Using the skills

All commands are run from inside Claude Code with your Flutter project as the working directory. Each skill accepts arguments after the command name.

### release-check

```
/flutter-release-kit:release-check
/flutter-release-kit:release-check --skip-tests
/flutter-release-kit:release-check --platform android
```

| Argument | Effect |
|---|---|
| `--skip-tests` | Skip `flutter test` (useful mid-development). |
| `--skip-analyze` | Skip `flutter analyze`. |
| `--platform android\|ios\|all` | Limit platform checks. Default `all`. |

Natural-language triggers: "is my app ready to release", "release checklist", "why was my app rejected", "check before I publish".

What it checks, by section:

- **Version**: `X.Y.Z+BUILD` format, Play's versionCode ceiling, an existing git tag for the same version, dirty working tree.
- **Changelog**: `CHANGELOG.md` exists and mentions the current version.
- **Static analysis and tests**: `flutter analyze`, `flutter test`.
- **Debug leftovers**: bare `print()`, TODO/FIXME, localhost or emulator URLs, forced debug banner.
- **Android**: `com.example` applicationId, release signing config, minify, `key.properties` present and git-ignored, keystores not tracked, app label, cleartext traffic, `debuggable`.
- **iOS**: `com.example` bundle id, `DEVELOPMENT_TEAM`, deployment target, display name, arbitrary loads, `PrivacyInfo.xcprivacy`, Podfile.lock.

Then Claude reviews what a script cannot: target SDK, default icon, store assets, account deletion, reviewer login. The skill's `references/` folder carries the store-rejection catalogue, an Android signing walkthrough and a privacy manifest template that Claude uses for fixes.

### bump-version

```
/flutter-release-kit:bump-version patch
/flutter-release-kit:bump-version minor --dry-run
/flutter-release-kit:bump-version set 2.0.0+40
/flutter-release-kit:bump-version build
```

Rules: the build number always increases by one (stores reject a reused build). `major`/`minor`/`patch` reset the lower parts. A `## [Unreleased]` section in `CHANGELOG.md` becomes the new version; otherwise an empty dated section is inserted. `--no-changelog` skips that. Prints the `git commit` and `git tag` commands but does not run them.

If you give no part, Claude looks at the commits since the last tag and proposes one.

### changelog

```
/flutter-release-kit:changelog
/flutter-release-kit:changelog --since v1.4.0
/flutter-release-kit:changelog --store
```

Groups commits since the last tag by conventional-commit prefix (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `chore:`). `--store` prints a plain "What's new" block under 500 characters from `feat`, `fix` and `perf` only, with fixes prefixed "Fixed:". Claude then rewrites developer wording into user wording and offers to paste it into `CHANGELOG.md`.

### store-listing

```
/flutter-release-kit:store-listing
/flutter-release-kit:store-listing play
/flutter-release-kit:store-listing appstore
/flutter-release-kit:store-listing --review
```

Claude reads `pubspec.yaml`, `README.md` and your screens under `lib/` and drafts every field with its character count, like `[78/80]`. It asks at most four questions (audience, differentiator, countries, privacy policy URL) and proceeds with stated assumptions if you do not answer. `--review` audits copy you paste or copy found under `fastlane/metadata` for over-length fields, policy words ("free", "best", "#1", other platforms), claims absent from the code and missing permission explanations.

### permission-audit

```
/flutter-release-kit:permission-audit
/flutter-release-kit:permission-audit --json
```

Output sections: an Android table (permission, tier, what Play requires), services with `foregroundServiceType` and bound permissions, `<queries>`, draft Play Console declarations with `{placeholders}` to fill, an iOS table of usage descriptions with weak ones flagged, missing iOS keys derived from your pubspec dependencies, privacy-manifest status, and an Issues list.

Claude then recommends in this order: remove, replace with the compliant alternative (SMS Retriever instead of READ_SMS, Photo Picker instead of storage, `<queries>` instead of QUERY_ALL_PACKAGES, WorkManager instead of exact alarms), narrow (`maxSdkVersion`, `neverForLocation`), and only then declare.

---

## The secret guard hook

Registered as a `PreToolUse` hook on Claude's Bash tool. Whenever Claude is about to run `git add`, `git commit` or `git stage`, the hook checks the untracked, modified and staged files for:

```
*.jks  *.keystore  *.p12  *.pepk  *.mobileprovision  AuthKey_*.p8
key.properties  keystore.properties  .env  .env.*
service-account*.json  *-service-account.json  google-play*.json  firebase-adminsdk*.json
upload-keystore*
```

If a sweep command (`git add -A`, `git add .`, `git commit -a`, a directory) or a direct `git add <secret>` would include one, the command is denied and Claude is told which files to add to `.gitignore`. Adding only a safe file by name is allowed. Once the secret files are git-ignored, the same commands pass.

The hook only governs commands Claude runs. Commands you type in your own terminal are not affected.

---

## Use without Claude Code (CI and scripts)

The skills call plain scripts you can run yourself or in CI:

```bash
scripts/preflight.sh [--skip-tests] [--skip-analyze] [--platform android|ios|all] [project_dir]   # exit 1 on FAIL
scripts/bump_version.py (major|minor|patch|build|set X.Y.Z+N) [--dry-run] [--no-changelog]
scripts/changelog.sh [--since TAG] [--store] [--max N]
scripts/permission_audit.py [project_dir] [--json]
```

Example: a release gate in GitHub Actions for a Flutter app.

```yaml
name: Release gate
on:
  pull_request:
    branches: [main]
jobs:
  preflight:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }          # tags are needed for the version check
      - uses: subosito/flutter-action@v2
        with: { channel: stable }
      - uses: actions/checkout@v4
        with:
          repository: ChandraChaan/flutter-release-kit
          ref: v1.0.1
          path: .release-kit
      - run: flutter pub get
      - run: bash .release-kit/scripts/preflight.sh --skip-tests
      - run: python3 .release-kit/scripts/permission_audit.py --json > permission-audit.json
      - uses: actions/upload-artifact@v4
        with: { name: permission-audit, path: permission-audit.json }
```

Pin the `ref` to a release tag so your gate does not change under you.

---

## Updating and uninstalling

```
/plugin marketplace update chandrachaan-plugins
/plugin update flutter-release-kit@chandrachaan-plugins
```

Restart Claude Code after an update. To remove:

```
/plugin uninstall flutter-release-kit@chandrachaan-plugins
/plugin marketplace remove chandrachaan-plugins
```

Try a local checkout without installing:

```bash
git clone https://github.com/ChandraChaan/flutter-release-kit.git
claude --plugin-dir ./flutter-release-kit
```

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `/flutter-release-kit:...` not found | Plugin installed but session not restarted. Restart Claude Code, then `/plugin list` should show it enabled. |
| `pubspec.yaml not found` | Run the skill from the Flutter project root, or pass the project path as the last argument. |
| Analyzer and tests show WARN "skipped" | `flutter` is not on the `PATH` Claude's shell sees. Check `which flutter` in the same session. |
| iOS section missing | No `ios/` folder (Android-only project). This is normal. |
| Hook blocks a file that is not a secret | The filename matched a pattern (for example a sample `.env.example`). Rename it or add it to `.gitignore`; the hook only blocks files git would commit. |
| `python3: command not found` on Windows | Use Git Bash with Python installed, or WSL. |
| Permission audit says a key is missing but the plugin does not use that feature | The plugin links the framework anyway (for example `camera` and the microphone). Either add a truthful usage string or switch to a plugin that does not link it. |

---

## Share it

If this saved you a rejection, three ways to pass it on:

**Link**: https://github.com/ChandraChaan/flutter-release-kit

**One-liner for your project README or a team wiki:**

```markdown
Release checks by [Flutter Release Kit](https://github.com/ChandraChaan/flutter-release-kit), a Claude Code plugin by Chandra ObulaReddy.
```

**Badge:**

```markdown
[![Checked with Flutter Release Kit](https://img.shields.io/badge/release%20checks-Flutter%20Release%20Kit-54C5F8)](https://github.com/ChandraChaan/flutter-release-kit)
```

**Cite it** (in a talk, article, or course): "Flutter Release Kit, Chandra ObulaReddy, 2026, github.com/ChandraChaan/flutter-release-kit".

Stars and issues both help: a star raises it in search, and an issue with the rejection email text (minus personal data) becomes a new check for everyone.

---

## Tests

```bash
bash tests/run.sh
```

Generates a Flutter-shaped fixture with deliberate release mistakes in a temp folder and asserts that every script and the hook catch them. No Flutter SDK needed; CI runs it on Ubuntu and macOS and runs `claude plugin validate --strict`.

---

## Layout

```
flutter-release-kit/
├── .claude-plugin/
│   ├── plugin.json         manifest
│   ├── marketplace.json    lets /plugin marketplace add work on this repo
│   └── icon.png
├── skills/
│   ├── release-check/      SKILL.md + references (store rejections, Android signing, privacy manifest)
│   ├── bump-version/
│   ├── changelog/
│   ├── store-listing/      SKILL.md + references (field limits, ASO rules)
│   └── permission-audit/   SKILL.md + references (Android alternatives, iOS usage strings)
├── hooks/hooks.json        PreToolUse guard on Bash
├── scripts/                preflight.sh, bump_version.py, changelog.sh, permission_audit.py, guard_secrets.sh
├── tests/                  make_fixture.sh, run.sh
└── .github/workflows/ci.yml
```

---

## Roadmap

- Fastlane metadata read/write for `store-listing`
- Screenshot checklist per device class
- Play Developer API upload step
- Localised listing drafts
- Merged-manifest analysis from a built AAB

Ideas and bug reports: [open an issue](https://github.com/ChandraChaan/flutter-release-kit/issues).

## License

MIT © 2026 Chandra ObulaReddy
