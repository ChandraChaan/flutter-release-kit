---
name: permission-audit
description: Audit Android manifest permissions and iOS Info.plist usage descriptions in a Flutter project, flag what Google Play and App Store will reject, and draft the Play Console declaration text. Use when the user asks about permissions, "will Play reject my SMS permission", foreground services, background location, usage descriptions, privacy manifest, or gets a permissions policy email.
argument-hint: "[project_dir] [--json]"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/permission_audit.py *), Read, Grep, Glob
---

# Permission audit

Permission policy is the most common reason Flutter apps get rejected or removed. Your job: find every permission the app declares, classify it, and tell the user exactly what to remove, replace, or declare.

## Step 1: run the audit

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/permission_audit.py" $ARGUMENTS
```

It reads `android/app/src/main/AndroidManifest.xml`, `ios/Runner/Info.plist` and `pubspec.yaml` and prints:

- an Android table with each permission's tier (**restricted** = Play declaration form, **sensitive** = runtime permission needing disclosure, **normal** = auto-granted);
- services with `foregroundServiceType`, `<queries>` entries;
- draft Play Console justification paragraphs with `{placeholders}`;
- iOS usage-description keys present, keys **missing** for the plugins in `pubspec.yaml`, weak/generic strings, and whether `PrivacyInfo.xcprivacy` exists;
- an Issues list.

## Step 2: check what the script cannot see

Plugins merge their own permissions into the final manifest. If the user has a built APK/AAB, the truth is:

```bash
# merged manifest from a debug build
cat build/app/intermediates/merged_manifests/release/AndroidManifest.xml 2>/dev/null | grep uses-permission
```

Also grep `lib/` for `Permission.` (permission_handler) and `requestPermission` to see which permissions the code actually asks for. A declared-but-never-requested permission is dead weight that still triggers review.

## Step 3: recommend, in order of preference

1. **Remove** the permission if no code path uses it.
2. **Replace** with the policy-compliant alternative. Read `references/android-alternatives.md`.
3. **Narrow** it: `android:maxSdkVersion`, `neverForLocation`, a specific `<queries>` list instead of `QUERY_ALL_PACKAGES`.
4. **Declare** it: fill the justification template with the app's real purpose, and tell the user where in Play Console it goes (Policy > App content > the matching declaration) and that a short screen-recording of the feature is usually required.

For iOS, write the missing `NS*UsageDescription` strings yourself in the form "<App> uses <data> to <user-visible benefit>." and offer to add them to `Info.plist`. Read `references/ios-usage-strings.md` for the key list and good examples. If the privacy manifest is missing, point to the release-check skill's `references/privacy-manifest.md` template.

## Step 4: report

- **Blockers**: restricted permissions without an eligible use case (say plainly that Play will reject it and what to use instead).
- **Declarations needed**: list with the filled-in justification text, ready to paste.
- **iOS fixes**: missing keys with proposed strings; privacy manifest status.
- **Cleanups**: maxSdkVersion, dead permissions, flags.

Where you edit `AndroidManifest.xml` or `Info.plist`, show the diff and keep the change minimal.
