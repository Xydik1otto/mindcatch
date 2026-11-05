# 📱 Мобільні застосунки / Mobile apps

Mindcatch на мобільних — **тонка оболонка (Capacitor 6), яка підключається до
СВОГО сервера**. UI не вбудований у застосунок: адреса сервера вводиться на
splash-екрані при першому запуску і зберігається в Preferences. Дані не
залишають ваш сервер — self-hosted етос проєкту.

## Чесні обмеження

- **iOS**: App Store вимагає Apple Developer ($99/рік) — НЕ в бюджеті. Шлях:
  unsigned IPA/.app з GitHub Actions → встановлення через **AltStore/Sideloadly**
  (безкоштовно, re-sign кожні 7 днів) або TestFlight у майбутньому.
- **Android**: APK з CI → пряме встановлення (sideload) — повністю безкоштовно.
- Віддалений доступ до свого сервера — через **Tailscale/WireGuard** (free).

---

## Українською

### Скачати готову збірку

1. Відкрийте [Releases](https://github.com/bigpi/mindcatch/releases).
2. **Android**: скачайте `app-debug.apk` з останнього релізу (або з артефактів
   CI-збірки — вкладка Actions, артефакт `mindcatch-debug-apk`, зберігається 30 днів).
3. **iOS**: скачайте `Mindcatch.app.zip` (артефакт `mindcatch-ios-unsigned`).

### Встановлення Android (sideload)

1. Скопіюйте APK на телефон, відкрийте його у файловому менеджері.
2. Дозвольте «Встановлення невідомих застосунків» для файлової програми.
3. Встановіть. Дозвіл у застосунку — **тільки INTERNET**.
4. При першому запуску введіть адресу сервера (наприклад,
   `http://192.168.1.10:8000`) → «Підключитися».

### Встановлення iOS (AltStore)

1. Встановіть [AltServer](https://altstore.io) на компʼютер і AltStore на iPhone.
2. Розпакуйте `Mindcatch.app.zip`; у Sideloadly/AltStore перетягніть `.app` —
   застосунок буде пере-signed вашим Apple ID (безкоштовно, re-sign кожні 7 днів).
3. На iPhone: Налаштування → Основні → VPN та керування пристроєм → довіряти
   своєму сертифікату.
4. При першому запуску введіть адресу сервера. HTTP у LAN дозволено
   (ATS-виняток у Info.plist), тож локальний сервер без TLS працює.

### Налаштування адреси сервера

- Splash-екран: поле «Адреса сервера» → перевірка `GET /api/tags` → редірект
  на повний UI сервера. Адреса зберігається нативно (Preferences).
- Якщо сервер недоступний, splash покаже помилку — введіть адресу знову.
- Скинути збережену адресу: очистіть дані застосунку (Android: Налаштування →
  Застосунки → Mindcatch → Сховище → Очистити дані; iOS: видаліть і
  перевстановіть).

### Віддалений доступ: Tailscale (безкоштовно)

1. Встановіть Tailscale на сервер і на телефон, увійдіть в один акаунт.
2. Адреса сервера в застосунку — Tailscale-IP або MagicDNS-імʼя сервера,
   наприклад `http://mindcatch-server:8000`.
3. Аналогічно працює WireGuard або VPN вашого роутера — будь-який спосіб
   дістатися до порту сервера.

### Збірка локально

Потрібні: Node 20+, JDK 17, Android SDK (для iOS — macOS + Xcode 15+).

```bash
npm ci
npx cap sync android
cd android && ./gradlew assembleDebug
# APK: android/app/build/outputs/apk/debug/app-debug.apk

npx cap sync ios
cd ios/App && pod install
cd .. && xcodebuild build -workspace App.xcworkspace -scheme App \
  -configuration Debug -sdk iphoneos -destination 'generic/platform=iOS' \
  -derivedDataPath build CODE_SIGNING_ALLOWED=NO CODE_SIGN_IDENTITY=""
```

CI збирає обидва: `.github/workflows/android-build.yml` (ubuntu, JDK 17,
attach APK до Release на тег) та `.github/workflows/ios-build.yml`
(macos, unsigned .app → zip артефакт). Артефакти зберігаються 30 днів.

---

## English

### Download a ready build

1. Open the [Releases](https://github.com/bigpi/mindcatch/releases) page.
2. **Android**: download `app-debug.apk` from the latest release (or from CI
   artifacts — Actions tab, artifact `mindcatch-debug-apk`, kept 30 days).
3. **iOS**: download `Mindcatch.app.zip` (artifact `mindcatch-ios-unsigned`).

### Install on Android (sideload)

1. Copy the APK to your phone and open it with a file manager.
2. Allow "Install unknown apps" for that file manager.
3. Install. The app requests **the INTERNET permission only**.
4. On first launch, enter your server address (e.g. `http://192.168.1.10:8000`)
   and tap Connect.

### Install on iOS (AltStore)

1. Install [AltServer](https://altstore.io) on your computer and AltStore on
   your iPhone.
2. Unzip `Mindcatch.app.zip`; drag the `.app` into Sideloadly/AltStore — it
   will be re-signed with your Apple ID (free, re-sign every 7 days).
3. On the iPhone: Settings → General → VPN & Device Management → trust your
   certificate.
4. On first launch, enter the server address. Plain HTTP on the LAN is allowed
   (ATS exception in Info.plist), so a local TLS-less server works.

### Server address setup

- Splash screen: the "Server address" field → validation via `GET /api/tags` →
  redirect to the server's full UI. The address is stored natively
  (Preferences).
- If the server is unreachable, the splash shows an error — enter it again.
- Reset the saved address: clear the app's data (Android: Settings → Apps →
  Mindcatch → Storage → Clear data; iOS: delete and reinstall).

### Remote access: Tailscale (free)

1. Install Tailscale on the server and the phone, sign in to the same account.
2. Use the server's Tailscale IP or MagicDNS name as the address, e.g.
   `http://mindcatch-server:8000`.
3. WireGuard or a router VPN works the same way — anything that reaches the
   server's port.

### Building locally

You need: Node 20+, JDK 17, the Android SDK (for iOS: macOS + Xcode 15+).

```bash
npm ci
npx cap sync android
cd android && ./gradlew assembleDebug
# APK: android/app/build/outputs/apk/debug/app-debug.apk

npx cap sync ios
cd ios/App && pod install
cd .. && xcodebuild build -workspace App.xcworkspace -scheme App \
  -configuration Debug -sdk iphoneos -destination 'generic/platform=iOS' \
  -derivedDataPath build CODE_SIGNING_ALLOWED=NO CODE_SIGN_IDENTITY=""
```

CI builds both: `.github/workflows/android-build.yml` (ubuntu, JDK 17, APK
attached to the Release on a tag) and `.github/workflows/ios-build.yml`
(macos, unsigned .app → zip artifact). Artifacts are kept for 30 days.
