# Platform: Fire tablet (Android)

A ~2015 Amazon Fire tablet (likely Fire 7 / HD 8 / HD 10, 5th gen — to be confirmed) running
**Fire OS 5 = Android 5.1 (API 22)**. Used as a colour touch console. Apps keep their
tablet side under `apps/<app>/fire/`.

No jailbreak or root is needed to develop for it: enable ADB and install APKs from the Mac.

## Status

- [ ] Identify model + Fire OS version (Settings → Device Options → Device Model;
      Settings → Device Options → System Updates)
- [ ] Enable Developer Options (tap **Serial Number** 7×) → **Enable ADB**
- [ ] `adb devices` sees the tablet from the Mac
- [ ] Optional: Google Play Store, debloat, custom launcher
- [ ] Optional: custom ROM — depends on exact model + firmware, check before trying

## Mac setup

```bash
brew install --cask android-platform-tools   # adb
adb devices                                  # accept the RSA prompt on the tablet
adb install -r path/to/app.apk
adb logcat                                   # logs
adb shell wm size                            # screen resolution
```

## How apps work on this platform

The default pattern is a tiny native app that hosts a full‑screen page served by the app's
Mac `server/`, with kiosk mode, keep‑screen‑on and start‑on‑boot. The UI lives in the
server's HTML; the APK rarely changes.

```
Mac server (HTTP / WebSocket) ◄──► Fire tablet: native APK → full‑screen WebView
```

Constraints:

- **Android 5.1 / API 22**: build with `minSdkVersion 22`. Many modern apps and libraries
  have dropped it.
- The system WebView/browser is old. Keep pages to plain HTML/CSS/ES5‑ish JS, or transpile
  for an old Chromium target. Test on the device, not just a desktop browser.
- 1–1.5 GB RAM, slow storage.
- No security updates. Keep it on the home LAN only and don't expose its services.
