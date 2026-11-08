---
name: changelog
description: Generate a changelog section or store "What's new" release notes from git history for a Flutter app. Use when the user asks for release notes, "what's new text", "changelog for this version", or when bump-version left an empty section.
argument-hint: "[--since TAG] [--store]"
allowed-tools: Bash(bash *), Bash(git *), Read, Edit
---

# Changelog and release notes

## Generate the raw list

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/changelog.sh" $ARGUMENTS
```

Default range is last tag to HEAD. The script groups commits by conventional-commit prefix into Added / Fixed / Performance / Changed / Docs / Internal and includes short hashes. With `--store` it prints a plain bulleted "What's new" block under 500 characters, from `feat`, `fix` and `perf` commits only, with no hashes.

## Rewrite for humans

Raw commit subjects are developer language. Before pasting into CHANGELOG.md or a store listing:

- Merge related commits into one bullet ("Fix crash on login" + "Fix login spinner" → "Fixed login crashes and the stuck spinner").
- Drop internal items (dependency bumps, CI, refactors) from store notes; keep them under **Internal** in the changelog only if the project tracks them.
- Write from the user's point of view, past tense in changelogs ("Added dark mode") and present tense in store notes ("Dark mode is here").
- Never mention other platforms in App Store notes (no "same as Android").

## Store limits

| Store | Field | Limit |
|---|---|---|
| Google Play | Release notes per language | 500 characters |
| App Store | What's New | 4000 characters, but the first ~3 lines are what users see |

## Write it back

- **CHANGELOG.md**: replace the empty bullets in the current version section (created by `bump-version`) with the edited list. Keep the Keep-a-Changelog headings.
- **Store notes**: show the final text in a code block so the user can copy it; offer to save to `release-notes/<version>.txt` if the project has such a folder.

If there are no tags yet, say so and use `--since <first-commit-or-branch>` or the whole history.
