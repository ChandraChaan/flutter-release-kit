# Store listing field limits

Verify against the consoles before submitting; limits occasionally change.

## Google Play Console (Main store listing)

| Field | Limit | Notes |
|---|---|---|
| App name | 30 chars | No emojis, no "free", no rankings. Capitalisation must be normal. |
| Short description | 80 chars | Shown above the fold on mobile; first thing users read. |
| Full description | 4000 chars | Basic formatting only; emojis allowed but reviewed. |
| Release notes | 500 chars per language | Wrapped in `<en-US>` tags when editing via API/fastlane. |
| App icon | 512 x 512 PNG, 32-bit, <1 MB | No transparency recommended. |
| Feature graphic | 1024 x 500 JPG/PNG | Required for Play Store listing. |
| Phone screenshots | 2 to 8, 16:9 or 9:16, 320 to 3840 px | Required. |
| 7-inch and 10-inch tablet screenshots | up to 8 each | Required for tablet listing quality badge. |
| Promo video | YouTube URL | Optional. |
| Privacy policy URL | required if any sensitive permission or data collection | Must be live and specific to this app. |
| Contact email | required | Visible publicly. |

## App Store Connect

| Field | Limit | Notes |
|---|---|---|
| Name | 30 chars | Indexed for search. |
| Subtitle | 30 chars | Indexed for search. |
| Promotional text | 170 chars | Editable without a new build; not indexed. |
| Description | 4000 chars | Not indexed for search; first 3 lines show before "more". |
| Keywords | 100 chars | Comma-separated, no spaces, no app name words, no duplicates. |
| What's New | 4000 chars | First version can be empty. |
| Support URL | required | |
| Marketing URL | optional | |
| Privacy policy URL | required | |
| Screenshots | 6.9" (or 6.5") iPhone required; 13" iPad required if iPad supported; up to 10 per size | PNG/JPG, no alpha. |
| App preview videos | up to 3 per size, 15 to 30 s | Optional. |
| Age rating | questionnaire | Must match content. |
| App Privacy | nutrition label | Must match SDK behaviour and the privacy manifest. |
