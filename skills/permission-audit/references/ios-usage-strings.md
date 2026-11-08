# iOS usage description keys and how to write them

A missing key crashes the app the moment the feature is used and fails App Review with ITMS-90683 if a linked framework references it. A vague string ("App needs camera") gets a 5.1.1 rejection. Pattern: **"<App> uses your <data> to <specific benefit>."**

| Key | Triggered by | Example |
|---|---|---|
| NSCameraUsageDescription | camera, image_picker, mobile_scanner, qr_code_scanner | "Ledger uses the camera to scan receipts so you do not have to type them." |
| NSPhotoLibraryUsageDescription | image_picker, photo_manager | "Ledger reads your photo library so you can attach an existing receipt photo." |
| NSPhotoLibraryAddUsageDescription | gal, image_gallery_saver, photo_manager (save) | "Ledger saves exported charts to your photo library." |
| NSMicrophoneUsageDescription | camera (video), record, speech_to_text, flutter_sound | "Ledger uses the microphone to record voice notes on a transaction." |
| NSSpeechRecognitionUsageDescription | speech_to_text | "Ledger transcribes your voice notes into text on device." |
| NSLocationWhenInUseUsageDescription | geolocator, location, google_maps_flutter, network_info_plus | "Ledger uses your location to tag where a purchase happened." |
| NSLocationAlwaysAndWhenInUseUsageDescription | background location | "Ledger uses background location to log mileage automatically while you drive." |
| NSContactsUsageDescription | flutter_contacts, contacts_service | "Ledger reads your contacts so you can split a bill with friends by name." |
| NSCalendarsUsageDescription / NSCalendarsFullAccessUsageDescription | device_calendar | "Ledger adds bill due dates to your calendar." |
| NSRemindersUsageDescription | reminders plugins | |
| NSFaceIDUsageDescription | local_auth | "Ledger uses Face ID to unlock your financial data." |
| NSBluetoothAlwaysUsageDescription | flutter_blue_plus, flutter_reactive_ble | "Ledger connects to your card reader over Bluetooth." |
| NSMotionUsageDescription | pedometer, sensors_plus | "Ledger uses motion data to detect driving trips." |
| NSHealthShareUsageDescription / NSHealthUpdateUsageDescription | health | |
| NSUserTrackingUsageDescription | google_mobile_ads, app_tracking_transparency, Facebook SDK | "Allowing tracking lets us show ads that are more relevant to you." |
| NFCReaderUsageDescription | nfc_manager | "Ledger reads NFC tags on your receipts." |
| NSLocalNetworkUsageDescription | mDNS, local servers, casting | "Ledger finds printers on your local network." |
| NSSiriUsageDescription | Siri shortcuts | |
| NSAppleMusicUsageDescription | media library | |

## Rules
- Mention the app name and the concrete feature. Apple rejects "for a better experience".
- Only add keys for features that exist. A key for an unused feature invites questions in review, though plugins that link a framework may require the key anyway (then say what the feature is, or remove the plugin).
- Keep strings under ~120 characters; the system dialog truncates longer text.
- Localise them via `InfoPlist.strings` if the app is localised.
- `NSLocationAlwaysUsageDescription` alone is deprecated; use `NSLocationAlwaysAndWhenInUseUsageDescription` plus `NSLocationWhenInUseUsageDescription`.
