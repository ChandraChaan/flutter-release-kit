#!/usr/bin/env python3
"""Flutter Release Kit - permission audit.
Author: Chandra ObulaReddy <https://github.com/ChandraChaan>

Reads android/app/src/main/AndroidManifest.xml, ios/Runner/Info.plist and
pubspec.yaml, then reports:
  * every Android permission with its risk tier and Play Console requirements
  * foreground service types, package visibility (<queries>) and exact alarms
  * iOS usage-description keys that are missing for the plugins you depend on
  * whether a privacy manifest (PrivacyInfo.xcprivacy) exists
  * draft justification text for each sensitive permission

Usage: permission_audit.py [project_dir] [--json]
"""
import json
import plistlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"

# tier: "restricted" needs a Play Console declaration form + policy fit,
#       "sensitive" needs a clear in-app purpose and privacy policy disclosure,
#       "normal" is auto-granted.
ANDROID_PERMS = {
    "android.permission.READ_SMS": ("restricted", "SMS/Call Log policy: only default SMS handler or approved use case (e.g. OTP is NOT enough; use SMS Retriever API).",),
    "android.permission.RECEIVE_SMS": ("restricted", "SMS/Call Log policy. Prefer SMS Retriever / SMS User Consent API for OTP.",),
    "android.permission.SEND_SMS": ("restricted", "SMS/Call Log policy. Requires default SMS handler or approved exception.",),
    "android.permission.RECEIVE_MMS": ("restricted", "SMS/Call Log policy.",),
    "android.permission.RECEIVE_WAP_PUSH": ("restricted", "SMS/Call Log policy.",),
    "android.permission.READ_CALL_LOG": ("restricted", "SMS/Call Log policy: only default Phone/Assistant handler or approved exception.",),
    "android.permission.WRITE_CALL_LOG": ("restricted", "SMS/Call Log policy.",),
    "android.permission.PROCESS_OUTGOING_CALLS": ("restricted", "Deprecated and covered by Call Log policy.",),
    "android.permission.READ_PHONE_STATE": ("sensitive", "Runtime permission. Play asks why; many uses are replaced by READ_PHONE_NUMBERS or telephony callbacks.",),
    "android.permission.READ_PHONE_NUMBERS": ("sensitive", "Runtime permission; explain the phone-number use in the listing.",),
    "android.permission.CALL_PHONE": ("sensitive", "Runtime permission. Use ACTION_DIAL intent instead when you only need to start a call.",),
    "android.permission.ANSWER_PHONE_CALLS": ("sensitive", "Runtime permission; usually only for call-screening apps.",),
    "android.permission.READ_CONTACTS": ("sensitive", "Runtime permission; disclose in Data safety form.",),
    "android.permission.WRITE_CONTACTS": ("sensitive", "Runtime permission; disclose in Data safety form.",),
    "android.permission.ACCESS_FINE_LOCATION": ("sensitive", "Runtime permission; disclose in Data safety and show in-app prominent disclosure.",),
    "android.permission.ACCESS_COARSE_LOCATION": ("sensitive", "Runtime permission; disclose in Data safety.",),
    "android.permission.ACCESS_BACKGROUND_LOCATION": ("restricted", "Background location declaration form in Play Console + video showing the feature. Core feature only.",),
    "android.permission.CAMERA": ("sensitive", "Runtime permission; also add <uses-feature android:name=\"android.hardware.camera\" android:required=\"false\"/> if optional.",),
    "android.permission.RECORD_AUDIO": ("sensitive", "Runtime permission; disclose in Data safety.",),
    "android.permission.BODY_SENSORS": ("sensitive", "Runtime permission; health data disclosure.",),
    "android.permission.ACTIVITY_RECOGNITION": ("sensitive", "Runtime permission; fitness/health disclosure.",),
    "android.permission.READ_EXTERNAL_STORAGE": ("sensitive", "Legacy. On API 33+ use READ_MEDIA_IMAGES/VIDEO/AUDIO; add android:maxSdkVersion=\"32\".",),
    "android.permission.WRITE_EXTERNAL_STORAGE": ("sensitive", "Legacy and ignored on API 30+. Add android:maxSdkVersion=\"29\" or remove.",),
    "android.permission.MANAGE_EXTERNAL_STORAGE": ("restricted", "All files access declaration form. Only file managers, backup, antivirus etc. Most apps get rejected.",),
    "android.permission.READ_MEDIA_IMAGES": ("sensitive", "Photo/Video permissions policy: only if media access is core. Otherwise use the Photo Picker.",),
    "android.permission.READ_MEDIA_VIDEO": ("sensitive", "Photo/Video permissions policy: prefer the Photo Picker.",),
    "android.permission.READ_MEDIA_AUDIO": ("sensitive", "Runtime permission.",),
    "android.permission.QUERY_ALL_PACKAGES": ("restricted", "Package visibility declaration form. Use <queries> with specific packages/intents instead.",),
    "android.permission.REQUEST_INSTALL_PACKAGES": ("restricted", "Only for app stores / approved use. Play rejects most apps that self-update.",),
    "android.permission.SYSTEM_ALERT_WINDOW": ("sensitive", "Draw over other apps; explain the feature. Flagged in review.",),
    "android.permission.BIND_ACCESSIBILITY_SERVICE": ("restricted", "Accessibility API policy: declaration form, must be for users with disabilities or an approved exception.",),
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": ("restricted", "Notification listener: explain in review; frequently rejected.",),
    "android.permission.BIND_DEVICE_ADMIN": ("restricted", "Device admin; enterprise use only.",),
    "android.permission.USE_FULL_SCREEN_INTENT": ("restricted", "Android 14+: auto-granted only for calling/alarm apps; others need a Play declaration.",),
    "android.permission.SCHEDULE_EXACT_ALARM": ("restricted", "Android 14+: only for alarm/clock/calendar apps. Others should use USE_EXACT_ALARM only if core, or WorkManager.",),
    "android.permission.USE_EXACT_ALARM": ("restricted", "Play policy: only alarm clocks, timers, calendars. Declaration required.",),
    "android.permission.POST_NOTIFICATIONS": ("sensitive", "Runtime permission on Android 13+. Request in context, not on first launch.",),
    "android.permission.BLUETOOTH_SCAN": ("sensitive", "Add android:usesPermissionFlags=\"neverForLocation\" if you don't derive location.",),
    "android.permission.BLUETOOTH_CONNECT": ("sensitive", "Runtime permission on Android 12+.",),
    "android.permission.NEARBY_WIFI_DEVICES": ("sensitive", "Runtime permission on Android 13+.",),
    "android.permission.FOREGROUND_SERVICE": ("sensitive", "Android 14+: every <service> needs android:foregroundServiceType and the matching FOREGROUND_SERVICE_<TYPE> permission; Play Console asks for a declaration + video per type.",),
    "android.permission.AD_ID": ("sensitive", "Declare advertising-ID use in the Data safety form.",),
    "android.permission.INTERNET": ("normal", "Auto-granted."),
    "android.permission.ACCESS_NETWORK_STATE": ("normal", "Auto-granted."),
    "android.permission.VIBRATE": ("normal", "Auto-granted."),
    "android.permission.WAKE_LOCK": ("normal", "Auto-granted."),
    "android.permission.RECEIVE_BOOT_COMPLETED": ("normal", "Auto-granted; make sure boot work is minimal."),
}

# Permissions that appear on a <service android:permission=...> rather than as
# <uses-permission>. They bind the service to a privileged system API.
SERVICE_BOUND_PERMS = {
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": "Notification access: Play reviews this as a sensitive API. Explain the user-facing feature in the listing and the review notes; apps that read notifications for analytics or ads are removed.",
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "Accessibility API policy: declaration form required, must serve users with disabilities or an approved exception.",
    "android.permission.BIND_DEVICE_ADMIN": "Device admin: enterprise/MDM use only; most consumer apps are rejected.",
    "android.permission.BIND_VPN_SERVICE": "VpnService policy: declaration form, must be a real VPN or approved use (no ad-blocking by default route tricks).",
    "android.permission.BIND_AUTOFILL_SERVICE": "Autofill service: allowed for password managers; disclose data handling.",
    "android.permission.BIND_INPUT_METHOD": "Keyboard (IME): disclose network use; keyboards that send keystrokes off-device are heavily reviewed.",
    "android.permission.BIND_CALL_SCREENING_SERVICE": "Call screening: eligible exception for call-log style data; describe the feature.",
    "android.permission.BIND_SCREENING_SERVICE": "Call screening: eligible exception for call-log style data; describe the feature.",
    "android.permission.BIND_TELECOM_CONNECTION_SERVICE": "Telecom connection service: calling apps only.",
    "android.permission.BIND_JOB_SERVICE": None,  # normal
    "android.permission.BIND_QUICK_SETTINGS_TILE": None,
    "android.permission.BIND_REMOTEVIEWS": None,
    "android.permission.BIND_WALLPAPER": None,
}

FGS_TYPES_NEEDING_DECLARATION = {
    "location", "camera", "microphone", "health", "remoteMessaging", "specialUse",
    "dataSync", "mediaProjection", "phoneCall", "connectedDevice", "mediaPlayback", "systemExempted",
}

# Flutter package -> iOS Info.plist keys it typically requires
IOS_KEYS_BY_PACKAGE = {
    "camera": ["NSCameraUsageDescription", "NSMicrophoneUsageDescription"],
    "image_picker": ["NSPhotoLibraryUsageDescription", "NSCameraUsageDescription", "NSMicrophoneUsageDescription"],
    "file_picker": [],
    "photo_manager": ["NSPhotoLibraryUsageDescription", "NSPhotoLibraryAddUsageDescription"],
    "gal": ["NSPhotoLibraryAddUsageDescription"],
    "image_gallery_saver": ["NSPhotoLibraryAddUsageDescription"],
    "geolocator": ["NSLocationWhenInUseUsageDescription"],
    "location": ["NSLocationWhenInUseUsageDescription"],
    "google_maps_flutter": ["NSLocationWhenInUseUsageDescription"],
    "flutter_contacts": ["NSContactsUsageDescription"],
    "contacts_service": ["NSContactsUsageDescription"],
    "speech_to_text": ["NSSpeechRecognitionUsageDescription", "NSMicrophoneUsageDescription"],
    "record": ["NSMicrophoneUsageDescription"],
    "flutter_sound": ["NSMicrophoneUsageDescription"],
    "audio_recorder": ["NSMicrophoneUsageDescription"],
    "local_auth": ["NSFaceIDUsageDescription"],
    "flutter_blue_plus": ["NSBluetoothAlwaysUsageDescription"],
    "flutter_reactive_ble": ["NSBluetoothAlwaysUsageDescription"],
    "health": ["NSHealthShareUsageDescription", "NSHealthUpdateUsageDescription"],
    "device_calendar": ["NSCalendarsUsageDescription"],
    "flutter_local_notifications": [],
    "mobile_scanner": ["NSCameraUsageDescription"],
    "qr_code_scanner": ["NSCameraUsageDescription"],
    "app_tracking_transparency": ["NSUserTrackingUsageDescription"],
    "google_mobile_ads": ["NSUserTrackingUsageDescription"],
    "facebook_audience_network": ["NSUserTrackingUsageDescription"],
    "network_info_plus": ["NSLocationWhenInUseUsageDescription"],
    "nfc_manager": ["NFCReaderUsageDescription"],
    "pedometer": ["NSMotionUsageDescription"],
    "sensors_plus": ["NSMotionUsageDescription"],
    "siri_shortcuts": ["NSSiriUsageDescription"],
}

JUSTIFICATION_TEMPLATES = {
    "android.permission.READ_SMS": "{app} reads incoming SMS to {purpose}. The app {handler}. Messages are processed on-device and never uploaded.",
    "android.permission.RECEIVE_SMS": "{app} listens for incoming SMS to {purpose}. No message content leaves the device.",
    "android.permission.SEND_SMS": "{app} sends SMS to {purpose}. Users confirm each message before it is sent.",
    "android.permission.READ_CALL_LOG": "{app} reads the call log to {purpose}. Data stays on-device.",
    "android.permission.ACCESS_BACKGROUND_LOCATION": "{app} uses background location to {purpose}. The feature is user-initiated, shown with a persistent notification, and can be turned off at any time.",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "{app} needs all-files access to {purpose}; scoped storage and the Storage Access Framework cannot provide this because {why_not_saf}.",
    "android.permission.QUERY_ALL_PACKAGES": "{app} needs the full package list to {purpose}; a <queries> declaration cannot work because {why_not_queries}.",
    "android.permission.FOREGROUND_SERVICE": "{app} runs a foreground service of type {type} to {purpose}. The service stops when the task finishes.",
    "android.permission.SCHEDULE_EXACT_ALARM": "{app} schedules exact alarms because {purpose}; inexact alarms would break the user-visible feature.",
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "{app} uses the Accessibility API to {purpose} for users with {disability}. It does not read screen content for any other purpose.",
    "android.permission.USE_FULL_SCREEN_INTENT": "{app} shows full-screen intents for {purpose} (time-critical, user-expected).",
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": "{app} reads notifications only from {source_apps} to {purpose}. Notification content is processed on-device, never stored longer than {retention}, and never used for advertising or analytics. Users enable access in Settings and can revoke it at any time.",
    "android.permission.BIND_VPN_SERVICE": "{app} provides a VPN service to {purpose}. Traffic is routed to {endpoint}; the app does not inspect or sell traffic data.",
    "android.permission.BIND_DEVICE_ADMIN": "{app} uses device admin to {purpose} for managed devices enrolled by {organisation}.",
}


def read_manifest(root: Path):
    path = root / "android/app/src/main/AndroidManifest.xml"
    if not path.exists():
        return None
    tree = ET.parse(path)
    m = tree.getroot()
    perms = []
    for el in m.iter():
        if el.tag in ("uses-permission", "uses-permission-sdk-23"):
            name = el.get(ANDROID_NS + "name", "")
            max_sdk = el.get(ANDROID_NS + "maxSdkVersion")
            flags = el.get(ANDROID_NS + "usesPermissionFlags")
            perms.append({"name": name, "maxSdkVersion": max_sdk, "flags": flags})
    services = []
    for svc in m.iter("service"):
        actions = [a.get(ANDROID_NS + "name", "") for a in svc.iter("action")]
        services.append({
            "name": svc.get(ANDROID_NS + "name", ""),
            "foregroundServiceType": svc.get(ANDROID_NS + "foregroundServiceType"),
            "exported": svc.get(ANDROID_NS + "exported"),
            "permission": svc.get(ANDROID_NS + "permission"),
            "actions": actions,
        })
    queries = m.find("queries")
    query_items = []
    if queries is not None:
        for q in queries:
            query_items.append(q.tag + ":" + (q.get(ANDROID_NS + "name") or (q.find("action").get(ANDROID_NS + "name") if q.find("action") is not None else "")))
    app = m.find("application")
    label = app.get(ANDROID_NS + "label") if app is not None else None
    return {"permissions": perms, "services": services, "queries": query_items, "label": label, "path": str(path)}


def read_plist(root: Path):
    path = root / "ios/Runner/Info.plist"
    if not path.exists():
        return None
    with path.open("rb") as fh:
        data = plistlib.load(fh)
    usage = {k: v for k, v in data.items() if k.endswith("UsageDescription")}
    return {"usage": usage, "all_keys": sorted(data.keys()), "path": str(path),
            "privacy_manifest": (root / "ios/Runner/PrivacyInfo.xcprivacy").exists(),
            "display_name": data.get("CFBundleDisplayName") or data.get("CFBundleName")}


def read_pubspec_deps(root: Path):
    path = root / "pubspec.yaml"
    if not path.exists():
        return [], None
    deps, in_deps, name = [], False, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("'\"")
        if re.match(r"^dependencies:\s*$", line):
            in_deps = True
            continue
        if in_deps and re.match(r"^\S", line):
            in_deps = False
        if in_deps:
            m = re.match(r"^  ([A-Za-z0-9_]+):", line)
            if m:
                deps.append(m.group(1))
    return deps, name


def placeholder_text(value: str) -> bool:
    v = (value or "").strip().lower()
    return len(v) < 20 or "needs access" in v and len(v) < 40 or v in ("", "todo", "tbd")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    root = Path(args[0] if args else ".").resolve()
    manifest = read_manifest(root)
    plist = read_plist(root)
    deps, app_name = read_pubspec_deps(root)
    app = (manifest or {}).get("label") or (plist or {}).get("display_name") or app_name or "This app"
    if app.startswith("@string/"):
        app = app_name or "This app"

    report = {"app": app, "android": {}, "ios": {}, "issues": []}

    if manifest:
        rows = []
        for p in manifest["permissions"]:
            tier, note = ANDROID_PERMS.get(p["name"], ("unknown", "Not in the built-in list; check Play policy for this permission."))
            if p["name"].startswith("android.permission.FOREGROUND_SERVICE_"):
                tier, note = "restricted", "Foreground service type permission: Play Console needs a declaration and demo video for this type."
            if p["name"].endswith("BILLING") or p["name"].endswith("c2dm.permission.RECEIVE") or p["name"].startswith("com.google.android.gms"):
                tier, note = "normal", "Vendor permission; auto-granted."
            rows.append({**p, "tier": tier, "note": note})
            if p["name"] in ("android.permission.WRITE_EXTERNAL_STORAGE",) and not p["maxSdkVersion"]:
                report["issues"].append("WRITE_EXTERNAL_STORAGE without android:maxSdkVersion=\"29\" (it does nothing on API 30+ and looks careless in review).")
            if p["name"] == "android.permission.READ_EXTERNAL_STORAGE" and not p["maxSdkVersion"]:
                report["issues"].append("READ_EXTERNAL_STORAGE without android:maxSdkVersion=\"32\"; use READ_MEDIA_* on API 33+.")
            if p["name"] == "android.permission.BLUETOOTH_SCAN" and (p["flags"] or "") != "neverForLocation":
                report["issues"].append("BLUETOOTH_SCAN without usesPermissionFlags=\"neverForLocation\" implies location derivation.")
        report["android"]["permissions"] = rows
        report["android"]["services"] = manifest["services"]
        report["android"]["queries"] = manifest["queries"]
        report["android"]["path"] = manifest["path"]
        names = {p["name"] for p in manifest["permissions"]}
        fgs = [s for s in manifest["services"] if s["foregroundServiceType"]]
        if "android.permission.FOREGROUND_SERVICE" in names and not fgs:
            report["issues"].append("FOREGROUND_SERVICE declared but no <service> has android:foregroundServiceType (required on targetSdk 34+).")
        for s in fgs:
            for t in s["foregroundServiceType"].split("|"):
                t = t.strip()
                perm = "android.permission.FOREGROUND_SERVICE_" + re.sub(r"(?<!^)(?=[A-Z])", "_", t).upper()
                if perm not in names:
                    report["issues"].append(f"Service {s['name']} uses type '{t}' but {perm} is not declared.")
                if t in FGS_TYPES_NEEDING_DECLARATION:
                    report["issues"].append(f"Foreground service type '{t}' needs a Play Console declaration (App content > Foreground service permissions) plus a short demo video.")
        for s_ in manifest["services"]:
            perm = s_.get("permission")
            if not perm:
                if (s_.get("exported") or "").lower() == "true":
                    report["issues"].append(f"Service {s_['name']} is exported=true with no android:permission; any app can bind to it.")
                continue
            if perm in SERVICE_BOUND_PERMS and SERVICE_BOUND_PERMS[perm]:
                rows.append({"name": perm, "maxSdkVersion": None, "flags": None, "tier": "restricted",
                             "note": SERVICE_BOUND_PERMS[perm] + f" (bound on service {s_['name']})"})
                report["issues"].append(f"Service {s_['name']} binds {perm.replace('android.permission.', '')}: restricted API, expect a Play policy review; see the draft declaration below.")
        if "android.permission.QUERY_ALL_PACKAGES" in names and manifest["queries"]:
            report["issues"].append("Both QUERY_ALL_PACKAGES and <queries> are present; drop QUERY_ALL_PACKAGES if <queries> covers your needs.")
        if any(n in names for n in ("android.permission.SCHEDULE_EXACT_ALARM", "android.permission.USE_EXACT_ALARM")):
            report["issues"].append("Exact alarm permission present: Play only allows it for alarm/timer/calendar core features.")
        report["android"]["justifications"] = {
            p["name"]: JUSTIFICATION_TEMPLATES[p["name"]] for p in manifest["permissions"] if p["name"] in JUSTIFICATION_TEMPLATES
        }
        for p in manifest["permissions"]:
            if p["name"].startswith("android.permission.FOREGROUND_SERVICE_"):
                report["android"]["justifications"][p["name"]] = JUSTIFICATION_TEMPLATES["android.permission.FOREGROUND_SERVICE"]
        for s_ in manifest["services"]:
            perm = s_.get("permission")
            if perm in JUSTIFICATION_TEMPLATES:
                report["android"]["justifications"][perm] = JUSTIFICATION_TEMPLATES[perm]

    if plist:
        expected = {}
        for dep in deps:
            for key in IOS_KEYS_BY_PACKAGE.get(dep, []):
                expected.setdefault(key, []).append(dep)
        missing = {k: v for k, v in expected.items() if k not in plist["usage"]}
        weak = {k: v for k, v in plist["usage"].items() if placeholder_text(str(v))}
        report["ios"] = {
            "path": plist["path"],
            "usage_descriptions": plist["usage"],
            "expected_from_packages": expected,
            "missing": missing,
            "weak_descriptions": weak,
            "privacy_manifest": plist["privacy_manifest"],
        }
        for k, pkgs in missing.items():
            report["issues"].append(f"iOS: {k} missing but required by {', '.join(sorted(set(pkgs)))}. App Store rejects or crashes on first use.")
        for k in weak:
            report["issues"].append(f"iOS: {k} text is too short/generic. Apple wants a specific sentence saying what the data is used for.")
        if not plist["privacy_manifest"]:
            report["issues"].append("iOS: no PrivacyInfo.xcprivacy. Required when the app or its plugins use required-reason APIs (UserDefaults, file timestamps, etc.), which nearly every Flutter app does.")

    if as_json:
        print(json.dumps(report, indent=2))
        return

    print(f"# Permission audit for {app}\n")
    if manifest:
        print(f"## Android ({manifest['path']})\n")
        print("| Permission | Tier | Notes |")
        print("|---|---|---|")
        order = {"restricted": 0, "sensitive": 1, "unknown": 2, "normal": 3}
        for r in sorted(report["android"]["permissions"], key=lambda r: order[r["tier"]]):
            extra = f" maxSdk={r['maxSdkVersion']}" if r["maxSdkVersion"] else ""
            print(f"| `{r['name'].replace('android.permission.', '')}`{extra} | **{r['tier']}** | {r['note']} |")
        if manifest["services"]:
            print("\n### Services")
            for s in manifest["services"]:
                perm = (s.get("permission") or "-").replace("android.permission.", "")
                print(f"- `{s['name']}` foregroundServiceType={s['foregroundServiceType'] or '-'} exported={s['exported'] or 'unset'} permission={perm}")
        if manifest["queries"]:
            print("\n### Package visibility (<queries>)")
            for q in manifest["queries"]:
                print(f"- {q}")
        if report["android"]["justifications"]:
            print("\n### Draft Play Console declarations (fill the {placeholders})")
            for name, text in report["android"]["justifications"].items():
                print(f"\n**{name.replace('android.permission.', '')}**\n> {text.replace('{app}', app)}")
    else:
        print("## Android\n\nNo AndroidManifest.xml found.")

    print("\n## iOS\n")
    if plist:
        print(f"Info.plist: {plist['path']}")
        print(f"Privacy manifest: {'present' if plist['privacy_manifest'] else 'MISSING'}\n")
        if plist["usage"]:
            print("| Key | Text |")
            print("|---|---|")
            for k, v in plist["usage"].items():
                flag = " ⚠ weak" if k in report["ios"]["weak_descriptions"] else ""
                print(f"| `{k}`{flag} | {str(v).replace('|', '/')} |")
        else:
            print("No *UsageDescription keys present.")
        if report["ios"]["missing"]:
            print("\n### Missing usage descriptions (from your pubspec dependencies)")
            for k, pkgs in report["ios"]["missing"].items():
                print(f"- `{k}` ← {', '.join(sorted(set(pkgs)))}")
    else:
        print("No ios/Runner/Info.plist found.")

    print("\n## Issues\n")
    if report["issues"]:
        for i in report["issues"]:
            print(f"- {i}")
    else:
        print("None found by static checks.")
    print(f"\n{len(report['issues'])} issue(s).")


if __name__ == "__main__":
    main()
