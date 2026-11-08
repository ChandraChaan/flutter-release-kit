# Common store rejection reasons and fixes

Compiled by Chandra ObulaReddy from Google Play policy, App Store Review Guidelines and real review feedback. Use as a checklist when a submission is rejected or before the first submission.

## Google Play

| Rejection | Cause | Fix |
|---|---|---|
| "Violation of Permissions policy" | Requesting SMS, Call Log, all-files, accessibility, background location, exact alarm or QUERY_ALL_PACKAGES without an eligible use case | Remove the permission or move to the approved alternative (SMS Retriever API, Photo Picker, `<queries>`, WorkManager). If truly needed, complete the declaration form and record a short video showing the feature. |
| "Deceptive behavior / misleading claims" | Store listing promises features the app does not have, or screenshots from another app | Make listing match the build; use real screenshots. |
| "User Data policy: prominent disclosure" | Collecting personal/sensitive data without an in-app disclosure before the permission prompt | Show a dialog explaining what is collected and why, then request permission. |
| "Data safety form inaccurate" | Form says no data collected but SDKs (Firebase Analytics, Ads, Crashlytics) collect it | Fill the form for every SDK; most analytics SDKs collect device IDs and crash logs. |
| "Target API level" | `targetSdk` below the current requirement | Raise `targetSdk` (Flutter's `flutter.targetSdkVersion` usually follows); test on the newest Android. |
| "Debuggable APK" | `android:debuggable="true"` or a debug build uploaded | Build with `flutter build appbundle --release`. |
| "Package name com.example" | Default Flutter package | Rename before first upload; it cannot change later. |
| "Broken functionality" | Crashes on launch, dead buttons, placeholder screens | Test the release build on a real device, not only the emulator. |
| "Login required, no credentials" | Reviewer could not get past login | Provide a demo account in App content > App access. |
| "Account deletion" | App has sign-up but no in-app deletion and no web deletion URL | Add delete-account flow and the URL in the Data safety form. |
| "Ads policy / full-screen ads" | Unexpected interstitials at app launch or during gameplay | Show interstitials only at natural breakpoints and never before the first screen. |
| "Health / financial content" | Health or finance apps missing required disclosures or licences | Add disclaimers, privacy policy and any required declaration form. |
| "Foreground service declaration" | targetSdk 34+ with foreground services and no Play Console declaration | Declare each type under App content and upload a demo video. |

## App Store

| Guideline | Cause | Fix |
|---|---|---|
| 2.1 App Completeness | Crashes, placeholder text, broken links, demo account missing | Test the IPA from TestFlight; fill App Review notes with a demo login. |
| 2.3 Accurate Metadata | Screenshots or description do not match the app; mentions Android | Remove references to other platforms; use real device screenshots. |
| 2.5.4 Background modes | Background mode enabled without a visible feature | Remove unused UIBackgroundModes. |
| 3.1.1 In-App Purchase | Selling digital content outside IAP, or linking to external purchase | Use StoreKit for digital goods; physical goods may use other payments. |
| 4.0 Design | Looks like a web page wrapper or has non-native controls that break | Add native value; ensure a smooth iOS experience. |
| 4.2 Minimum Functionality | Too simple, mostly static content | Add real functionality; the bar is higher than Play's. |
| 4.8 Sign in with Apple | Offers third-party login (Google, Facebook) without Sign in with Apple | Add Sign in with Apple, or another login that limits data collection. |
| 5.1.1 Data Collection | Missing or vague `NS*UsageDescription`; asking for data not needed | Write specific usage strings; request only what the feature needs. |
| 5.1.1(v) Account deletion | Sign-up without in-app account deletion | Add a deletion flow accessible in-app. |
| 5.1.2 Data Use and Sharing | Tracking without `NSUserTrackingUsageDescription` and the ATT prompt | Add App Tracking Transparency before any tracking SDK runs. |
| Privacy manifest missing | App or SDK uses required-reason APIs with no `PrivacyInfo.xcprivacy` | Add the manifest with `NSPrivacyAccessedAPITypes` entries; update plugins to versions that ship their own. |
| ITMS-90683 | Missing purpose string in Info.plist for a linked framework | Add the key the email names, even if the feature is unused (plugins link the framework). |

## Things reviewers notice that scripts cannot

- Default Flutter launcher icon or "flutter_app" name.
- Lorem ipsum, "TODO", "Coming soon" screens.
- A privacy policy link that 404s or points to a generic template with another company's name.
- Push notification permission requested at first launch with no context.
- Non-functional back navigation on Android.
- Text cut off on small devices or in the largest accessibility font size.
