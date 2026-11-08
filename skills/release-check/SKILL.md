---
name: release-check
description: Run a release preflight on a Flutter project before building for Google Play or the App Store. Use when the user asks "is my app ready to release", "check before I publish", "release checklist", "why was my app rejected", or before running flutter build appbundle / ipa.
argument-hint: "[--skip-tests] [--platform android|ios|all]"
allowed-tools: Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.sh *), Read, Grep, Glob
---

# Release check

You are helping a Flutter developer ship a release that will not be rejected by Google Play or App Store review. Be concrete: name the file and the exact change for every problem.

## Step 1: run the deterministic preflight

From the Flutter project root run:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.sh" $ARGUMENTS
```

The script prints `PASS` / `WARN` / `FAIL` lines grouped by section (Version, Changelog, Static analysis, Tests, Debug leftovers, Android, iOS) and exits 1 on any FAIL. It may take a minute when tests run. If the user is clearly in the middle of development and only wants a quick look, pass `--skip-tests`.

## Step 2: investigate every FAIL and WARN

For each item, open the file the script names and confirm the finding before reporting it. Common fixes:

| Finding | Fix |
|---|---|
| Version has no build number | Change `version: 1.2.0` to `version: 1.2.0+1` in `pubspec.yaml`. |
| Tag already exists for this version | Run the `bump-version` skill. |
| `com.example` applicationId or bundle id | Use `flutter pub run change_app_package_name:main com.yourco.app` or edit `android/app/build.gradle(.kts)` and the three `PRODUCT_BUNDLE_IDENTIFIER` entries in `ios/Runner.xcodeproj/project.pbxproj`. |
| Release signs with debug key | Add `key.properties` loading and a `release` signingConfig; see `references/android-signing.md`. |
| `key.properties` or `*.jks` tracked by git | Add to `.gitignore`, then `git rm --cached <file>`; rotate the keystore password if the repo is public. |
| No `PrivacyInfo.xcprivacy` | Create `ios/Runner/PrivacyInfo.xcprivacy`; template in `references/privacy-manifest.md`. |
| `debuggable=true`, cleartext traffic, localhost URLs | Remove before release. |
| Analyzer errors / failing tests | Fix them; do not suggest skipping. |

## Step 3: check things the script cannot

Look at the project and consider:

- **Target SDK**: Google Play requires new apps and updates to target a recent Android API level (Play's rolling requirement is roughly the previous year's release). Check `targetSdk` in `android/app/build.gradle(.kts)` or the Flutter default.
- **App icon and splash**: the default Flutter icon is a rejection in review and an instant uninstall for users. Check `flutter_launcher_icons` / `flutter_native_splash` config or the mipmap folders.
- **Permissions**: if the manifest has anything beyond INTERNET, suggest running the `permission-audit` skill.
- **Store assets**: feature graphic 1024x500 (Play), screenshots for each required device class, privacy policy URL (required if the app collects any data or requests sensitive permissions).
- **Account deletion**: both stores require an in-app account deletion path if the app supports account creation.
- **Login for reviewers**: if there is a login screen, remind the user to supply a demo account in the review notes.

Read `references/store-rejections.md` for the full list of common rejection reasons and their fixes when the user asks why they were rejected or wants a deeper review.

## Step 4: report

Return a short report:

1. **Verdict**: READY / NOT READY.
2. **Must fix** (FAIL items, each with file and exact change).
3. **Should fix** (WARN items that matter for this app).
4. **Next commands**: usually `flutter build appbundle --release` and `flutter build ipa --release`, preceded by `bump-version` and `changelog` when the version was already shipped.

Keep it tight. Do not repeat PASS lines unless the user asks for the full output.
