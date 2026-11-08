#!/usr/bin/env bash
# Flutter Release Kit test suite. Runs every script against a generated fixture
# and asserts on the findings. No Flutter SDK required.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIX="$(mktemp -d)/fixture_app"
bash "$ROOT/tests/make_fixture.sh" "$FIX"
cd "$FIX"

PASS=0; FAILN=0
check() { # name, condition-exit-code
  if [[ "$2" -eq 0 ]]; then echo "ok   $1"; PASS=$((PASS+1)); else echo "FAIL $1"; FAILN=$((FAILN+1)); fi
}
has() { grep -qF -- "$2" <<< "$1"; }

echo "## syntax"
bash -n "$ROOT/scripts/preflight.sh" "$ROOT/scripts/guard_secrets.sh" "$ROOT/tests/make_fixture.sh"; check "bash -n" $?
python3 -m py_compile "$ROOT/scripts/bump_version.py" "$ROOT/scripts/permission_audit.py" "$ROOT/scripts/changelog.py"; check "py_compile" $?
python3 -c "import json,sys;[json.load(open(f)) for f in sys.argv[1:]]" "$ROOT/.claude-plugin/plugin.json" "$ROOT/.claude-plugin/marketplace.json" "$ROOT/hooks/hooks.json"; check "json manifests" $?

echo "## preflight"
OUT=$(bash "$ROOT/scripts/preflight.sh" --skip-tests --skip-analyze 2>&1); RC=$?
check "exits 1 on failures" $([[ $RC -eq 1 ]]; echo $?)
for s in "com.example.ledger" "signingConfigs.debug" "NOT git-ignored" "localhost" "iOS bundle id is 'com.example.ledger'" "tag for 1.2.0 already exists" "PrivacyInfo.xcprivacy" "usesCleartextTraffic"; do
  has "$OUT" "$s"; check "preflight reports: $s" $?
done
has "$OUT" "FAIL: 5"; check "preflight counts 5 FAIL" $?

echo "## permission audit"
OUT=$(python3 -I "$ROOT/scripts/permission_audit.py" . 2>&1); RC=$?
check "audit exits 0" $RC
for s in "READ_SMS" "restricted" "FOREGROUND_SERVICE_DATA_SYNC is not declared" "maxSdkVersion=\"29\"" "neverForLocation" "BIND_NOTIFICATION_LISTENER_SERVICE" "NSLocationWhenInUseUsageDescription" "NSContactsUsageDescription" "NSMicrophoneUsageDescription" "too short/generic" "PrivacyInfo.xcprivacy"; do
  has "$OUT" "$s"; check "audit reports: $s" $?
done
python3 -I "$ROOT/scripts/permission_audit.py" . --json | python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d['issues'])>=10, d['issues']"; check "audit --json has >=10 issues" $?

echo "## changelog"
OUT=$(python3 -I "$ROOT/scripts/changelog.py" 2>&1)
has "$OUT" "### Added" && has "$OUT" "Export to CSV" && has "$OUT" "### Fixed" && has "$OUT" "Crash on login"; check "changelog groups feat/fix" $?
OUT=$(python3 -I "$ROOT/scripts/changelog.py" --store 2>&1)
has "$OUT" "• Export to CSV" && has "$OUT" "• Fixed: crash on login" && ! has "$OUT" "("; check "store notes plain, no hashes" $?
[[ ${#OUT} -le 500 ]]; check "store notes <= 500 chars" $?

echo "## bump version"
OUT=$(python3 -I "$ROOT/scripts/bump_version.py" minor --dry-run); has "$OUT" "1.2.0+5 -> 1.3.0+6"; check "dry-run minor" $?
grep -q '^version: 1.2.0+5' pubspec.yaml; check "dry-run leaves pubspec untouched" $?
python3 -I "$ROOT/scripts/bump_version.py" patch >/dev/null; grep -q '^version: 1.2.1+6' pubspec.yaml; check "patch bump written" $?
grep -q '^## \[1.2.1\]' CHANGELOG.md && ! grep -q 'Unreleased' CHANGELOG.md; check "Unreleased renamed to 1.2.1" $?
python3 -I "$ROOT/scripts/bump_version.py" exact 2.0.0 --no-changelog >/dev/null; grep -q '^version: 2.0.0+7' pubspec.yaml; check "exact keeps build increasing" $?
python3 -I "$ROOT/scripts/bump_version.py" build >/dev/null; grep -q '^version: 2.0.0+8' pubspec.yaml; check "build-only bump" $?

echo "## secret guard hook"
hook() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" | CLAUDE_PROJECT_DIR="$FIX" bash "$ROOT/scripts/guard_secrets.sh"; }
OUT=$(hook 'git add -A'); has "$OUT" '"permissionDecision": "deny"' && has "$OUT" "key.properties" && has "$OUT" "upload-keystore.jks"; check "denies git add -A with secrets present" $?
OUT=$(hook 'git commit -am msg'); has "$OUT" 'deny'; check "denies git commit -a" $?
OUT=$(hook 'git add android/key.properties'); has "$OUT" 'deny'; check "denies adding the secret by name" $?
OUT=$(hook 'git add pubspec.yaml'); [[ -z "$OUT" ]]; check "allows adding a safe file" $?
OUT=$(hook 'flutter build apk'); [[ -z "$OUT" ]]; check "ignores non-git commands" $?
printf 'android/key.properties\n*.jks\n' > .gitignore
OUT=$(hook 'git add -A'); [[ -z "$OUT" ]]; check "allows once secrets are git-ignored" $?

echo
echo "passed: $PASS  failed: $FAILN"
rm -rf "$(dirname "$FIX")"
[[ $FAILN -eq 0 ]]
