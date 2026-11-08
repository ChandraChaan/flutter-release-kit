# Changelog

All notable changes to Flutter Release Kit are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-11-08

### Added
- `release-check`: one-shot release preflight for Flutter projects (analyze, tests, versioning, Android/iOS signing, bundle IDs, changelog, debug leftovers).
- `bump-version`: semantic version and build-number bumps in `pubspec.yaml` with a matching changelog section.
- `changelog`: Markdown changelog and store-ready "What's new" text generated from git history.
- `store-listing`: Google Play and App Store listing copy that respects every character limit.
- `permission-audit`: Android manifest and iOS Info.plist review with Play Console declaration drafts and missing usage-string detection.
- Secret guard hook that blocks `git add` / `git commit` when keystores, `key.properties`, provisioning profiles, or `.env` files would be committed.
