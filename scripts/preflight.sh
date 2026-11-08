#!/usr/bin/env bash
# Flutter Release Kit - release preflight
# Author: Chandra ObulaReddy (ChandraChaan)
#
# Usage: preflight.sh [--skip-tests] [--skip-analyze] [--platform android|ios|all] [project_dir]
# Prints a PASS/WARN/FAIL report. Exit code 1 when any check FAILs.


SKIP_TESTS=0
SKIP_ANALYZE=0
PLATFORM="all"
PROJECT_DIR="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-tests) SKIP_TESTS=1 ;;
    --skip-analyze) SKIP_ANALYZE=1 ;;
    --platform) shift; PLATFORM="${1:-all}" ;;
    -h|--help)
      sed -n '2,8p' "$0"; exit 0 ;;
    *) PROJECT_DIR="$1" ;;
  esac
  shift
done

cd "$PROJECT_DIR" 2>/dev/null || { echo "FAIL  Cannot open project dir: $PROJECT_DIR"; exit 1; }

FAILS=0
WARNS=0
pass() { printf 'PASS  %s\n' "$1"; }
warn() { printf 'WARN  %s\n' "$1"; WARNS=$((WARNS+1)); }
fail() { printf 'FAIL  %s\n' "$1"; FAILS=$((FAILS+1)); }
section() { printf '\n## %s\n' "$1"; }

[[ -f pubspec.yaml ]] || { fail "pubspec.yaml not found. Run this from a Flutter project root."; exit 1; }

# ---------------------------------------------------------------- Version
section "Version"
VERSION_LINE=$(grep -E '^version:' pubspec.yaml | head -1 | sed -E 's/^version:[[:space:]]*//; s/[[:space:]]+#.*$//; s/["'"'"']//g')
if [[ -z "$VERSION_LINE" ]]; then
  fail "No 'version:' in pubspec.yaml. Stores need X.Y.Z+BUILD."
else
  if [[ "$VERSION_LINE" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)\+([0-9]+)$ ]]; then
    pass "Version $VERSION_LINE (name ${BASH_REMATCH[1]}.${BASH_REMATCH[2]}.${BASH_REMATCH[3]}, build ${BASH_REMATCH[4]})"
    BUILD_NUM="${BASH_REMATCH[4]}"
    [[ "$BUILD_NUM" -gt 2100000000 ]] && fail "Build number $BUILD_NUM exceeds Google Play's versionCode limit (2100000000)."
  elif [[ "$VERSION_LINE" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    fail "Version '$VERSION_LINE' has no build number. Use '$VERSION_LINE+1' so versionCode / CFBundleVersion are set."
  else
    fail "Version '$VERSION_LINE' is not in X.Y.Z+BUILD form."
  fi
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  SEMVER="${VERSION_LINE%%+*}"
  if [[ -n "$SEMVER" ]] && git tag --list | grep -qxE "v?${SEMVER}(\+.*)?"; then
    warn "A git tag for $SEMVER already exists. Bump the version before publishing again."
  else
    pass "No existing git tag for this version."
  fi
  if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    warn "Working tree has uncommitted changes. Release builds should come from a clean, tagged commit."
  else
    pass "Working tree is clean."
  fi
fi

# --------------------------------------------------------------- Changelog
section "Changelog"
if [[ -f CHANGELOG.md ]]; then
  SEMVER="${VERSION_LINE%%+*}"
  if [[ -n "$SEMVER" ]] && grep -qF "$SEMVER" CHANGELOG.md; then
    pass "CHANGELOG.md mentions $SEMVER."
  else
    warn "CHANGELOG.md has no entry for $SEMVER. Run the changelog skill to draft one."
  fi
else
  warn "No CHANGELOG.md. Store release notes are easier to write from one."
fi

# --------------------------------------------------------------- Analyzer
section "Static analysis"
if ! command -v flutter >/dev/null 2>&1; then
  warn "flutter not on PATH; skipping analyze and tests."
  SKIP_ANALYZE=1; SKIP_TESTS=1
fi
if [[ $SKIP_ANALYZE -eq 0 ]]; then
  ANALYZE_OUT=$(flutter analyze --no-pub 2>&1)
  if echo "$ANALYZE_OUT" | grep -q "No issues found"; then
    pass "flutter analyze: no issues."
  else
    ERR_COUNT=$(echo "$ANALYZE_OUT" | grep -cE '^\s*error •' || true)
    WARN_COUNT=$(echo "$ANALYZE_OUT" | grep -cE '^\s*(warning|info) •' || true)
    if [[ "$ERR_COUNT" -gt 0 ]]; then
      fail "flutter analyze: $ERR_COUNT error(s), $WARN_COUNT warning/info."
    else
      warn "flutter analyze: $WARN_COUNT warning/info item(s)."
    fi
  fi
else
  warn "Analyzer skipped."
fi

# ------------------------------------------------------------------- Tests
section "Tests"
if [[ $SKIP_TESTS -eq 0 ]]; then
  if [[ -d test ]] && find test -name '*_test.dart' | grep -q .; then
    if flutter test --no-pub >/tmp/frk_test_out.txt 2>&1; then
      pass "flutter test: all tests passed."
    else
      fail "flutter test failed. Last lines:"
      tail -n 15 /tmp/frk_test_out.txt | sed 's/^/      /'
    fi
  else
    warn "No tests found under test/."
  fi
else
  warn "Tests skipped."
fi

# ------------------------------------------------------------ Debug leftovers
section "Debug leftovers"
if [[ -d lib ]]; then
  PRINTS=$(grep -rnE '^\s*print\(' lib --include='*.dart' 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$PRINTS" -gt 0 ]]; then warn "$PRINTS bare print() call(s) in lib/. Prefer debugPrint or a logger."; else pass "No bare print() calls in lib/."; fi
  TODOS=$(grep -rnE 'TODO|FIXME' lib --include='*.dart' 2>/dev/null | wc -l | tr -d ' ')
  [[ "$TODOS" -gt 0 ]] && warn "$TODOS TODO/FIXME marker(s) in lib/."
  if grep -rqE 'http://(localhost|127\.0\.0\.1|10\.0\.2\.2)' lib --include='*.dart' 2>/dev/null; then
    fail "Hard-coded localhost / emulator URLs found in lib/."
  else
    pass "No localhost URLs in lib/."
  fi
  if grep -rqE 'debugShowCheckedModeBanner:\s*true' lib --include='*.dart' 2>/dev/null; then
    warn "debugShowCheckedModeBanner is explicitly true somewhere in lib/."
  fi
fi

# ----------------------------------------------------------------- Android
if [[ "$PLATFORM" == "all" || "$PLATFORM" == "android" ]] && [[ -d android ]]; then
  section "Android"
  GRADLE=""
  for f in android/app/build.gradle.kts android/app/build.gradle; do [[ -f "$f" ]] && GRADLE="$f" && break; done
  if [[ -z "$GRADLE" ]]; then
    fail "android/app/build.gradle(.kts) not found."
  else
    APP_ID=$(grep -E 'applicationId' "$GRADLE" | head -1 | sed -E 's/.*applicationId[^"'"'"']*["'"'"']([^"'"'"']+)["'"'"'].*/\1/')
    if [[ -z "$APP_ID" ]]; then
      warn "applicationId not found in $GRADLE."
    elif [[ "$APP_ID" == com.example.* ]]; then
      fail "applicationId is '$APP_ID'. Google Play rejects com.example.* package names."
    else
      pass "applicationId $APP_ID"
    fi

    if grep -qE 'signingConfig\s*=?\s*signingConfigs\.debug' "$GRADLE" && ! grep -qE 'signingConfigs\.release' "$GRADLE"; then
      fail "Release build type still signs with signingConfigs.debug."
    elif grep -qE 'signingConfigs\.release|signingConfigs\.getByName\("release"\)' "$GRADLE"; then
      pass "Release signing config referenced in $GRADLE."
    else
      warn "No release signingConfig found in $GRADLE. Play requires an upload key."
    fi

    if grep -qE 'isMinifyEnabled\s*=\s*true|minifyEnabled\s+true' "$GRADLE"; then
      pass "Code shrinking (minify) enabled."
      [[ -f android/app/proguard-rules.pro ]] || warn "minify is on but android/app/proguard-rules.pro is missing."
    else
      warn "minify is not enabled for release; the app will be larger than needed."
    fi
  fi

  if [[ -f android/key.properties ]]; then
    pass "android/key.properties present."
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      if git check-ignore -q android/key.properties; then
        pass "key.properties is git-ignored."
      else
        fail "android/key.properties is NOT git-ignored. It holds keystore passwords."
      fi
    fi
  else
    warn "android/key.properties not found. Release signing may be unconfigured on this machine."
  fi

  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    TRACKED_KEYS=$(git ls-files | grep -E '\.(jks|keystore|p12|pepk)$' || true)
    if [[ -n "$TRACKED_KEYS" ]]; then
      fail "Keystore files are tracked by git: $(echo "$TRACKED_KEYS" | tr '\n' ' ')"
    else
      pass "No keystore files tracked by git."
    fi
  fi

  MANIFEST=android/app/src/main/AndroidManifest.xml
  if [[ -f "$MANIFEST" ]]; then
    LABEL=$(grep -oE 'android:label="[^"]*"' "$MANIFEST" | head -1 | cut -d'"' -f2)
    if [[ -z "$LABEL" ]]; then
      warn "No android:label in manifest."
    elif [[ "$LABEL" =~ ^[a-z_]+$ ]]; then
      warn "android:label is '$LABEL' (looks like a package/dir name, not a product name)."
    else
      pass "App label: $LABEL"
    fi
    grep -q 'android:usesCleartextTraffic="true"' "$MANIFEST" && warn "usesCleartextTraffic=true in manifest. Remove for release unless required."
    grep -q 'android:debuggable="true"' "$MANIFEST" && fail "android:debuggable=true in manifest. Play rejects debuggable APKs/AABs."
    PERM_COUNT=$(grep -c '<uses-permission' "$MANIFEST" || true)
    pass "$PERM_COUNT uses-permission entries (run the permission-audit skill for details)."
  else
    fail "AndroidManifest.xml not found at $MANIFEST."
  fi
fi

# --------------------------------------------------------------------- iOS
if [[ "$PLATFORM" == "all" || "$PLATFORM" == "ios" ]] && [[ -d ios ]]; then
  section "iOS"
  PBX=ios/Runner.xcodeproj/project.pbxproj
  if [[ -f "$PBX" ]]; then
    BUNDLE_ID=$(grep -oE 'PRODUCT_BUNDLE_IDENTIFIER = [^;]+;' "$PBX" | grep -v RunnerTests | head -1 | sed -E 's/PRODUCT_BUNDLE_IDENTIFIER = (.*);/\1/')
    if [[ "$BUNDLE_ID" == com.example.* ]]; then
      fail "iOS bundle id is '$BUNDLE_ID'. Change it before App Store submission."
    elif [[ -n "$BUNDLE_ID" ]]; then
      pass "Bundle id $BUNDLE_ID"
    else
      warn "Could not read PRODUCT_BUNDLE_IDENTIFIER."
    fi
    if grep -qE 'DEVELOPMENT_TEAM = [A-Z0-9]{10};' "$PBX"; then
      pass "DEVELOPMENT_TEAM set in Xcode project."
    else
      warn "No DEVELOPMENT_TEAM in project.pbxproj. Set your team in Xcode > Signing & Capabilities."
    fi
    DEPLOY=$(grep -oE 'IPHONEOS_DEPLOYMENT_TARGET = [0-9.]+' "$PBX" | head -1 | awk '{print $3}')
    [[ -n "$DEPLOY" ]] && pass "iOS deployment target $DEPLOY"
  else
    fail "ios/Runner.xcodeproj/project.pbxproj not found."
  fi
  PLIST=ios/Runner/Info.plist
  if [[ -f "$PLIST" ]]; then
    DISPLAY=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' "$PLIST" 2>/dev/null || true)
    [[ -n "$DISPLAY" ]] && pass "CFBundleDisplayName: $DISPLAY" || warn "CFBundleDisplayName missing or variable-only."
    if grep -q 'NSAllowsArbitraryLoads' "$PLIST" && grep -A1 'NSAllowsArbitraryLoads' "$PLIST" | grep -q '<true/>'; then
      warn "NSAllowsArbitraryLoads=true. App Review asks for a justification."
    fi
    [[ -f ios/Runner/PrivacyInfo.xcprivacy ]] && pass "PrivacyInfo.xcprivacy present." || warn "No ios/Runner/PrivacyInfo.xcprivacy. Apple requires a privacy manifest when you use required-reason APIs (most apps do via plugins)."
  else
    fail "ios/Runner/Info.plist not found."
  fi
  [[ -f ios/Podfile.lock ]] || warn "ios/Podfile.lock missing; run 'cd ios && pod install'."
fi

# ----------------------------------------------------------------- Summary
printf '\n## Summary\n'
printf 'FAIL: %d   WARN: %d\n' "$FAILS" "$WARNS"
if [[ $FAILS -gt 0 ]]; then
  echo "Result: NOT READY. Fix the FAIL items above before building a release."
  exit 1
fi
echo "Result: READY (review the WARN items)."
exit 0
