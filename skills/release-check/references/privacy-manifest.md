# iOS privacy manifest (PrivacyInfo.xcprivacy)

Apple requires a privacy manifest when the app or any linked SDK uses "required reason" APIs. Nearly every Flutter app does through `shared_preferences` (UserDefaults), `path_provider` (file timestamps) and similar plugins. Modern plugin versions ship their own manifest, but the app target needs one too.

Create `ios/Runner/PrivacyInfo.xcprivacy` and add it to the Runner target in Xcode (File > Add Files to "Runner"). A starting point for an app that stores preferences and reads file timestamps and does not track users:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyTracking</key>
    <false/>
    <key>NSPrivacyTrackingDomains</key>
    <array/>
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>CA92.1</string>
            </array>
        </dict>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryFileTimestamp</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>C617.1</string>
            </array>
        </dict>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategorySystemBootTime</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>35F9.1</string>
            </array>
        </dict>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryDiskSpace</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>E174.1</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
```

Reason codes: CA92.1 (UserDefaults, app's own data), C617.1 (file timestamps inside the app container), 35F9.1 (boot time for elapsed-time measurement), E174.1 (disk space to check before writing). Remove entries you do not use.

If the app collects data (analytics, crash logs, account info), fill `NSPrivacyCollectedDataTypes`; the values must match the App Privacy answers in App Store Connect. If you use the IDFA or any cross-app tracking, set `NSPrivacyTracking` to true and list the domains.
