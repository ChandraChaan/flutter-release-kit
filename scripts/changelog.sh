#!/usr/bin/env bash
# Flutter Release Kit - changelog generator
# Author: Chandra ObulaReddy <https://github.com/ChandraChaan>
#
# Usage: changelog.sh [--since REF] [--store] [--max N]
#   default range : last tag..HEAD (or whole history when no tag exists)
#   --since REF   : explicit start ref (tag, commit, branch)
#   --store       : plain "What's new" text for store release notes (<= 500 chars)
#   --max N       : cap on bullets per section (default 30)
set -u
SINCE=""; STORE=0; MAX=30
while [[ $# -gt 0 ]]; do
  case "$1" in
    --since) shift; SINCE="${1:-}" ;;
    --store) STORE=1 ;;
    --max) shift; MAX="${1:-30}" ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
  esac; shift
done

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "error: not a git repository" >&2; exit 1; }
if [[ -z "$SINCE" ]]; then SINCE=$(git describe --tags --abbrev=0 2>/dev/null || true); fi
RANGE="HEAD"; [[ -n "$SINCE" ]] && RANGE="${SINCE}..HEAD"

# subject + short hash, skipping merges and release chores
LOG=$(git log --no-merges --pretty=format:'%s|%h' "$RANGE" 2>/dev/null | grep -viE '^(chore(\([^)]*\))?: (release|bump|version)|merge )' || true)
if [[ -z "$LOG" ]]; then echo "No commits in range ${RANGE}."; exit 0; fi

declare -a FEAT FIX PERF REFACTOR DOCS CHORE OTHER
while IFS='|' read -r subj hash; do
  clean=$(echo "$subj" | sed -E 's/^[a-z]+(\([^)]*\))?!?:[[:space:]]*//')
  clean="$(tr '[:lower:]' '[:upper:]' <<< "${clean:0:1}")${clean:1}"
  item="- ${clean} (${hash})"
  case "$subj" in
    feat*)     FEAT+=("$item") ;;
    fix*)      FIX+=("$item") ;;
    perf*)     PERF+=("$item") ;;
    refactor*) REFACTOR+=("$item") ;;
    docs*)     DOCS+=("$item") ;;
    chore*|build*|ci*|test*|style*) CHORE+=("$item") ;;
    *)         OTHER+=("$item") ;;
  esac
done <<< "$LOG"

emit() { # title, array name
  local title="$1"; shift
  local -a arr=("$@")
  [[ ${#arr[@]} -eq 0 ]] && return
  printf '### %s\n' "$title"
  printf '%s\n' "${arr[@]:0:$MAX}"
  [[ ${#arr[@]} -gt $MAX ]] && printf -- '- ...and %d more\n' $(( ${#arr[@]} - MAX ))
  printf '\n'
}

if [[ $STORE -eq 1 ]]; then
  # Store notes: user-facing only, no hashes, trimmed to 500 chars.
  OUT=""
  store_add() { # prefix, lines...
    local prefix="$1"; shift
    local line txt candidate
    for line in "$@"; do
      [[ -z "$line" ]] && continue
      txt=$(echo "$line" | sed -E 's/ \([0-9a-f]{7,}\)$//; s/^- //')
      if [[ -n "$prefix" ]]; then txt="${prefix}$(tr '[:upper:]' '[:lower:]' <<< "${txt:0:1}")${txt:1}"; fi
      candidate="${OUT}• ${txt}"$'\n'
      [[ ${#candidate} -gt 500 ]] && return
      OUT="$candidate"
    done
  }
  store_add ""         "${FEAT[@]+"${FEAT[@]}"}"
  store_add "Fixed: "  "${FIX[@]+"${FIX[@]}"}"
  store_add "Faster: " "${PERF[@]+"${PERF[@]}"}"
  [[ -z "$OUT" ]] && OUT="• Bug fixes and performance improvements"$'\n'
  printf '%s' "$OUT"
  exit 0
fi

VERSION=$(grep -E '^version:' pubspec.yaml 2>/dev/null | head -1 | sed -E 's/^version:[[:space:]]*//; s/\+.*//; s/["'"'"']//g')
printf '## [%s] - %s\n\n' "${VERSION:-Unreleased}" "$(date +%F)"
[[ -n "$SINCE" ]] && printf '_Changes since %s_\n\n' "$SINCE"
emit "Added"       "${FEAT[@]+"${FEAT[@]}"}"
emit "Fixed"       "${FIX[@]+"${FIX[@]}"}"
emit "Performance" "${PERF[@]+"${PERF[@]}"}"
emit "Changed"     "${REFACTOR[@]+"${REFACTOR[@]}"}" "${OTHER[@]+"${OTHER[@]}"}"
emit "Docs"        "${DOCS[@]+"${DOCS[@]}"}"
emit "Internal"    "${CHORE[@]+"${CHORE[@]}"}"
