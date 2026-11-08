#!/usr/bin/env bash
# Builds a throwaway Flutter-shaped project with deliberate release problems.
# Usage: make_fixture.sh <target_dir>
set -euo pipefail
FIX="${1:?target dir}"
rm -rf "$FIX"; mkdir -p "$FIX"/{lib,android/app/src/main,ios/Runner,ios/Runner.xcodeproj,test}
cd "$FIX"
cat > pubspec.yaml <<'Y'
name: ledger
description: Expense tracker.
version: 1.2.0+5
environment:
  sdk: ^3.5.0
dependencies:
  flutter:
    sdk: flutter
  camera: ^0.11.0
  geolocator: ^13.0.0
  flutter_contacts: ^1.1.9
dev_dependencies:
  flutter_test:
    sdk: flutter
Y
printf '# Changelog\n\n## [Unreleased]\n\n### Added\n- \n\n## [1.2.0] - 2026-10-01\n### Added\n- Receipt scanning\n' > CHANGELOG.md
printf "void main() {\n  print('debug');\n  final api = 'http://localhost:8080';\n}\n" > lib/main.dart
cat > android/app/build.gradle.kts <<'G'
android {
    defaultConfig { applicationId = "com.example.ledger" }
    buildTypes { release { signingConfig = signingConfigs.debug } }
}
G
cat > android/app/src/main/AndroidManifest.xml <<'M'
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.READ_SMS"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
    <uses-permission android:name="android.permission.BLUETOOTH_SCAN"/>
    <application android:label="ledger" android:usesCleartextTraffic="true">
        <service android:name=".SyncService" android:foregroundServiceType="dataSync" android:exported="false"/>
        <service android:name=".Listener" android:exported="true"
                 android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"/>
    </application>
</manifest>
M
printf 'storePassword=secret\nkeyAlias=upload\n' > android/key.properties
echo fake > android/upload-keystore.jks
cat > ios/Runner/Info.plist <<'P'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleDisplayName</key><string>Ledger</string>
  <key>NSCameraUsageDescription</key><string>Needs camera</string>
</dict></plist>
P
printf 'PRODUCT_BUNDLE_IDENTIFIER = com.example.ledger;\nIPHONEOS_DEPLOYMENT_TARGET = 13.0;\n' > ios/Runner.xcodeproj/project.pbxproj
git init -q -b main
git -c user.name=t -c user.email=t@t add pubspec.yaml CHANGELOG.md lib android/app ios
git -c user.name=t -c user.email=t@t commit -qm "feat: receipt scanning"
git tag v1.2.0
echo x >> lib/main.dart; git -c user.name=t -c user.email=t@t commit -qam "fix: crash on login"
echo y >> lib/main.dart; git -c user.name=t -c user.email=t@t commit -qam "feat: export to CSV"
