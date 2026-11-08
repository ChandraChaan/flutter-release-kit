# Policy-compliant alternatives to restricted Android permissions

| You want to | Do not use | Use instead |
|---|---|---|
| Read an OTP from SMS | `READ_SMS`, `RECEIVE_SMS` | SMS Retriever API (`sms_autofill`, `smart_auth`) or SMS User Consent API. No permission needed. |
| Let the user send a text | `SEND_SMS` | `url_launcher` with `sms:` URI; the user sends from their SMS app. |
| Call a number | `CALL_PHONE` | `url_launcher` with `tel:` (ACTION_DIAL). |
| Know if the user is on a call / phone number | `READ_PHONE_STATE` | `READ_PHONE_NUMBERS` for the number; `TelephonyCallback` / `AudioManager.mode` for call state. |
| Pick a photo or video | `READ_MEDIA_IMAGES`, `READ_EXTERNAL_STORAGE` | Android Photo Picker via `image_picker` ≥1.0 (`requestFullMetadata: false`) or `file_picker`. No permission. |
| Save a file the user chose | `WRITE_EXTERNAL_STORAGE`, `MANAGE_EXTERNAL_STORAGE` | Storage Access Framework (`file_picker` saveFile, `flutter_file_dialog`) or MediaStore for media. App-private dirs via `path_provider`. |
| See which apps are installed | `QUERY_ALL_PACKAGES` | `<queries>` listing specific `<package>` names or `<intent>` filters. |
| Run a periodic job | `SCHEDULE_EXACT_ALARM` | `WorkManager` (`workmanager` package) or inexact `AlarmManager`. Exact alarms only for alarm/calendar apps. |
| Keep working in the background | `FOREGROUND_SERVICE` with a vague type | Pick the narrowest `foregroundServiceType` (`dataSync`, `location`, `mediaPlayback`...), add `FOREGROUND_SERVICE_<TYPE>`, show a real notification, stop when done. Or use WorkManager if a notification is not needed. |
| Track location when the app is closed | `ACCESS_BACKGROUND_LOCATION` | Ask for foreground location first; only request background if the feature is core, user-initiated and shown in a persistent notification. Expect to submit a video. |
| Auto-fill or read screen content | `BIND_ACCESSIBILITY_SERVICE` | Autofill Framework for credentials; Notification Listener only for approved cases; otherwise redesign. |
| Install updates in-app | `REQUEST_INSTALL_PACKAGES` | Play In-App Updates API (`in_app_update`). |
| Show an incoming call / alarm screen | `USE_FULL_SCREEN_INTENT` | Only calling and alarm apps keep it by default; others use high-priority notifications. |
| Show a floating widget | `SYSTEM_ALERT_WINDOW` | Picture-in-picture, bubbles, or a notification; keep overlays only if core. |
| Scan BLE devices without location | `BLUETOOTH_SCAN` + location | `BLUETOOTH_SCAN` with `android:usesPermissionFlags="neverForLocation"`. |
| Target API 33+ storage | `READ_EXTERNAL_STORAGE` | `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` / `READ_MEDIA_AUDIO` only if you need to browse the whole library; otherwise the Photo Picker. Add `android:maxSdkVersion="32"` to the legacy permission. |

## Manifest snippets

Legacy storage limited to old API levels:

```xml
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="29" />
```

Package visibility without `QUERY_ALL_PACKAGES`:

```xml
<queries>
    <package android:name="com.whatsapp" />
    <intent>
        <action android:name="android.intent.action.VIEW" />
        <data android:scheme="https" />
    </intent>
</queries>
```

Foreground service with a typed permission (targetSdk 34+):

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<application>
    <service
        android:name=".SyncService"
        android:foregroundServiceType="dataSync"
        android:exported="false" />
</application>
```

Bluetooth scanning without implying location:

```xml
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" android:usesPermissionFlags="neverForLocation" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
```
