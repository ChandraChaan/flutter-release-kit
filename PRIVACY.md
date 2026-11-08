# Privacy policy

**Flutter Release Kit** by Chandra ObulaReddy.

Flutter Release Kit runs entirely on your machine inside Claude Code, Cowork, or the Claude apps.

- It does not collect, store, or transmit any personal data, telemetry, or analytics.
- Its scripts read files in the Flutter project you point them at (`pubspec.yaml`, `AndroidManifest.xml`, `Info.plist`, Gradle and Xcode project files, git history) and print a report to your terminal. Nothing is written outside that project except the version and changelog edits you ask for.
- It makes no network requests of its own. The only network activity is Claude Code fetching the plugin from GitHub when you install or update it.
- It does not read, copy, or transmit signing keys, passwords, or credential files. The secret-guard hook only checks file *names* against a pattern list to stop them being committed.

If you believe the plugin behaves differently, please [open an issue](https://github.com/ChandraChaan/flutter-release-kit/issues).

Last updated: 2026-11-08
