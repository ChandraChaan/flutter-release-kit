#!/usr/bin/env bash
# Flutter Release Kit - secret guard (PreToolUse hook on Bash)
# Author: Chandra ObulaReddy (ChandraChaan)
#
# Blocks `git add` / `git commit -a` / `git commit` when a signing secret or
# credentials file would be committed. Reads the hook JSON on stdin.
set -u
INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))
except Exception: print("")')

# Only care about staging/committing.
echo "$CMD" | grep -qE '(^|[;&|[:space:]])git[[:space:]]+(add|commit|stage)([[:space:]]|$)' || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

PATTERN='(^|/)(key\.properties|keystore\.properties|\.env(\..+)?|service-account.*\.json|.*-service-account\.json|google-play.*\.json|AuthKey_.*\.p8|.*\.jks|.*\.keystore|.*\.p12|.*\.mobileprovision|.*\.pepk|upload-keystore.*|firebase-adminsdk.*\.json)$'

# Candidates: untracked-not-ignored + modified + already staged files.
CANDIDATES=$( { git ls-files --others --exclude-standard; git diff --name-only; git diff --cached --name-only; } 2>/dev/null | sort -u | grep -E "$PATTERN" || true)
[[ -z "$CANDIDATES" ]] && exit 0

# If the command names specific paths, only block when one of them is a secret
# (or the path is a directory / wildcard / -A / . that could sweep it in).
if echo "$CMD" | grep -qE 'git[[:space:]]+add[[:space:]]' && ! echo "$CMD" | grep -qE 'git[[:space:]]+add[[:space:]]+(-A|--all|-u|\.|\*|[^ ]+/)'; then
  HIT=0
  for f in $CANDIDATES; do
    base=$(basename "$f")
    echo "$CMD" | grep -qF -- "$base" && HIT=1
  done
  [[ $HIT -eq 0 ]] && exit 0
fi

LIST=$(echo "$CANDIDATES" | sed 's/^/  - /')
python3 - "$LIST" <<'PY'
import json, sys
files = sys.argv[1]
print(json.dumps({
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": (
      "Flutter Release Kit blocked this git command: it would commit signing or credential files:\n"
      + files +
      "\nAdd them to .gitignore (and remove from the index with `git rm --cached <file>` if already tracked), then retry."
    )
  }
}))
PY
exit 0
