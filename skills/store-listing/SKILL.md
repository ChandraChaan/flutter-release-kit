---
name: store-listing
description: Write or review Google Play and App Store listing copy (title, subtitle, short and full description, keywords, release notes) for a Flutter app, within every character limit. Use when the user asks for store description, app title ideas, keywords, ASO, or "write my Play Store listing".
argument-hint: "[play|appstore|both] [--review]"
allowed-tools: Read, Glob, Grep
---

# Store listing

Produce listing copy that passes review and converts. Work from the real app: read `pubspec.yaml` (name, description), `README.md`, the main screens under `lib/` (feature names, screen titles, empty-state text), and any existing `fastlane/metadata` or `store/` folder. Never invent features that are not in the code.

Read `references/limits.md` for the exact field limits and `references/aso-checklist.md` for the writing rules before drafting.

## Ask only what the code cannot tell you

If not already clear, ask in one message:
1. Who is the app for (one sentence)?
2. The one thing it does better than alternatives?
3. Target countries / languages?
4. Does it have a privacy policy URL and a support email?

Proceed with sensible assumptions if the user does not answer; mark assumptions in the draft.

## Deliver (default: both stores)

### Google Play
- **App name** (30): product name, optional short hook. No "free", "best", emojis, or ALL CAPS.
- **Short description** (80): the value proposition, keywords first.
- **Full description** (4000): opening paragraph that works on its own, then feature bullets, then trust/privacy paragraph, then "Permissions we ask for and why" if any sensitive permission exists.
- **Release notes** (500) for the current version if a CHANGELOG exists.
- **Category** suggestion and **content rating** notes.

### App Store
- **Name** (30), **Subtitle** (30), **Promotional text** (170, editable without a new build), **Description** (4000), **Keywords** (100, comma-separated, no spaces after commas, no words already in name/subtitle, no plurals of existing words, no competitor names), **What's New**.
- **Primary category** suggestion; **age rating** notes.

For each field print the character count in brackets after it, like `[78/80]`, and keep every field under its limit.

## Review mode (`--review`)

When the user pastes existing copy or the project has `fastlane/metadata`, check each field for: length, policy words (free, best, #1, download now, mentions of other platforms or stores, unverifiable claims, medical/financial claims without disclaimers), keyword stuffing, feature claims absent from the code, and missing permission explanations. Return a table of field, issue, suggested rewrite.

## Output

Deliver as plain text blocks per field so the user can copy directly into the consoles. Offer to save to `fastlane/metadata/android/en-US/*.txt` and `fastlane/metadata/ios/en-US/*.txt` only if the project already uses fastlane.
