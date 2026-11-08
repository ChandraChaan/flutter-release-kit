# Android release signing for Flutter

## 1. Create an upload keystore (once)

```bash
keytool -genkey -v -keystore ~/upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

Keep this file and its password outside the repository and backed up. Losing it means losing the ability to update the app unless Play App Signing is enabled (it is by default for new apps, which is why this is called the upload key).

## 2. android/key.properties (git-ignored)

```properties
storePassword=<password>
keyPassword=<password>
keyAlias=upload
storeFile=/Users/you/upload-keystore.jks
```

Add to `.gitignore`:

```
android/key.properties
**/*.jks
**/*.keystore
```

## 3. android/app/build.gradle.kts

```kotlin
import java.util.Properties
import java.io.FileInputStream

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    signingConfigs {
        create("release") {
            keyAlias = keystoreProperties["keyAlias"] as String?
            keyPassword = keystoreProperties["keyPassword"] as String?
            storeFile = keystoreProperties["storeFile"]?.let { file(it) }
            storePassword = keystoreProperties["storePassword"] as String?
        }
    }
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
}
```

Groovy (`build.gradle`) equivalent:

```groovy
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}
android {
    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile keystoreProperties['storeFile'] ? file(keystoreProperties['storeFile']) : null
            storePassword keystoreProperties['storePassword']
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

## 4. Build

```bash
flutter build appbundle --release
```

Upload `build/app/outputs/bundle/release/app-release.aab`.

## CI note

In CI, decode the keystore from a base64 secret into a temp path and write `key.properties` at build time. Never commit either file.
