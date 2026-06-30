# ibscare-android Codex Handoff

## Current Status

This project was copied from:

- `C:\Users\mymelodyPC\Documents\Codex\2026-06-25\ultraresearch\work\ibs-care-android`

The active project path is now:

- `C:\MyProject\ibscare-android`

The Android debug build is currently complete at version:

- `versionName`: `0.1.9`
- `versionCode`: `10`
- UI label: `버전 0.1.9 (10)`

Continuation audit, latest regenerated on 2026-06-30 for notification actions:

- The likely-session phone notification now exposes two actions: `똥싸는 중이 아님` and `기록하러 가기`.
- `기록하러 가기` opens the app through the pending-session confirmation path and pre-fills the suggested record time without auto-saving.
- `똥싸는 중이 아님` records the current foreground candidate or stored background pending candidate feature summary as a false-positive pattern, then clears the likely-session notification.
- The alert dialog copy is aligned to `똥싸는 중이 아님` / `똥싸는 중이 아님으로 기록됨`.
- Current versioned debug artifacts:
  - `app/build/outputs/apk/debug/ibs-care-v0.1.9-10-debug.apk`
  - `app/build/outputs/apk/debug/ibs-care-v0.1.9-10-debug-phone-test.zip`
  - `ibs-care-v0.1.9-10-debug-apk.zip`
- Current artifact SHA256:
  - APK: `DC5B81EE139D768205E11E74B7F6AF8E32A9B14279F0E6E83159641B2A3F023D`
  - phone-test ZIP: `CBB4F42CB8E7E8B7632A7004E5069508712F17EDB9D9FE5BD7532077F7C0B774`
  - root ZIP: `CE08B1081B5A5AA859F2150F1702284B252C96B0C575451B3EC22452BD0380D1`
- Verification: `:app:testDebugUnitTest`, `:app:lintDebug`, `:app:assembleDebug`, `aapt dump badging`, `apksigner verify`, forbidden permission/network scan, emulator UI QA, and `dumpsys notification --noredact` action inspection passed.
- Android UI QA and notification evidence for 0.1.9 is under `.omo/evidence/ibscare-v0.1.9-notification-actions`.
- Local-only release notes now keep 0.1.9 current through `C:\MyProject\yulchive-astro\src\data\ibsCareReleases.mjs`, `src\pages\ibs-care.astro`, and `src\pages\ibs-care\[version].astro`; historical pages remain available for 0.1.4 through 0.1.8.

Continuation audit, latest regenerated on 2026-06-30 for multiple daily bowel movements:

- IBS users may record multiple bowel movements per day. The app no longer suppresses likely-session scoring or prompting just because `BowelLogRepository.hasMovementToday(today())` is true.
- `BowelSessionScorer.evaluate()` now only scores the current `MotionFeatures`; same-day record count is no longer an input to prompt eligibility.
- Immediate duplicate prompts are throttled by `PromptCooldownGate` with a 10-minute cooldown after a prompt, instead of a day-long block. This gate is used in both `MainActivity` and `BackgroundBowelDetectionService`.
- Current versioned debug artifacts:
  - `app/build/outputs/apk/debug/ibs-care-v0.1.8-9-debug.apk`
  - `app/build/outputs/apk/debug/ibs-care-v0.1.8-9-debug-phone-test.zip`
  - `ibs-care-v0.1.8-9-debug-apk.zip`
- Current artifact SHA256:
  - APK: `FD141F2BFA83CE1A8C04A77302858DFD3B40EF38EB0CFAD2C8165E36E4F59E4D`
  - phone-test ZIP: `4BFD2DDF0EFC9256457CE6BE9B836D196070397647B381D14D55E3F06CF65E66`
  - root ZIP: `F674382D18C89A53E1E2820A4B94261E7A76E6588AB49D738A71EC2F9D20221B`
- Verification: `:app:testDebugUnitTest`, `:app:lintDebug`, `:app:assembleDebug`, `aapt dump badging`, `apksigner verify`, forbidden permission/network scan, and emulator UI QA passed.
- Android UI QA evidence for 0.1.8 is under `.omo/evidence/ibscare-v0.1.8-multiple-daily`.
- Local-only release notes now use `C:\MyProject\yulchive-astro\src\data\ibsCareReleases.mjs`, `src\pages\ibs-care.astro`, and `src\pages\ibs-care\[version].astro`. The index keeps 0.1.8 current and links historical pages `/ibs-care/0.1.4/` through `/ibs-care/0.1.8/`; Yulchive local-only tests, production build, sitemap/RSS exclusion, local/proxy HTTP checks, and desktop/mobile Chrome QA passed.

Continuation audit, latest regenerated on 2026-06-30:

- The likely-session alert no longer has a `나중에` button. The negative action is now `똥싸는 중 아님`.
- Tapping `똥싸는 중 아님` records the current candidate feature summary as a false-positive pattern and immediately updates the proposal panel to `똥싸는 중 아님으로 기록됨`.
- False-positive correction uses the same local feature-summary boundary as positive post-event learning: stationary minutes, variance, and posture evidence are stored; raw sensor axes are not stored.
- Repeated patterns matching the false-positive feature summary are scored with `shouldPrompt=false`.
- `app/build.gradle` wires `:app:assembleDebug` to generate the current versioned debug artifacts:
  - `app/build/outputs/apk/debug/ibs-care-v0.1.7-8-debug.apk`
  - `app/build/outputs/apk/debug/ibs-care-v0.1.7-8-debug-phone-test.zip`
  - `ibs-care-v0.1.7-8-debug-apk.zip`
- Current artifact SHA256:
  - APK: `8F7DC7D305D797F6C1A181B28543837D011A7A357DCCF459F28622B6CD70DBEC`
  - phone-test ZIP: `5C4AE356D58682E875E3C2934CA3157979DD9A4988F567C9FA5C18E9EA3DF7E2`
  - root ZIP: `774137080C71D65CB113A50E51C272C8ED53D231F1EE18E61D0956BDB7645436`
- Verification: `:app:testDebugUnitTest`, `:app:lintDebug`, `:app:assembleDebug`, `aapt dump badging`, `apksigner verify`, forbidden permission/network scan, and emulator UI QA all passed.
- Android UI QA evidence for 0.1.7 is under `.omo/evidence/ibscare-v0.1.7-alert-false-positive`.
- Local-only release note `C:\MyProject\yulchive-astro\src\pages\ibs-care.astro` was updated to 0.1.7, including the new screenshot `public\ibs-care\v0.1.7-after-save.png`; Yulchive local-only tests, production build, sitemap/RSS exclusion, local/proxy HTTP checks, and desktop/mobile Chrome QA passed.

Continuation audit, latest regenerated on 2026-06-29:

- Detection v2 adds gravity pitch/roll rolling-window posture evidence and local post-event pattern learning from feature summaries.
- Button UX now gives visible feedback for weak candidates, fills the suggested time only for likely candidates, and preserves explicit `기록 저장` as the only durable save action.
- `app/build.gradle` wires `:app:assembleDebug` to generate the current versioned debug artifacts:
  - `app/build/outputs/apk/debug/ibs-care-v0.1.6-7-debug.apk`
  - `app/build/outputs/apk/debug/ibs-care-v0.1.6-7-debug-phone-test.zip`
  - `ibs-care-v0.1.6-7-debug-apk.zip`
- Current artifact SHA256:
  - APK: `A6E31536EC4E9DEFAAC7F0446EF55F2EE2E1BACA42DF44CCFAC07B722DA979A0`
  - phone-test ZIP: `B43C7D1A4BA2DD5CA917667016A93391D9B1BB6B24107F24930EE029507B722B`
  - root ZIP: `E9735EAF7BA97B2C96FC6A6DC7AB089ECA61E5DD89AD4C0095D84E5F0E0E4090`
- Verification: `:app:testDebugUnitTest`, `:app:lintDebug`, `:app:assembleDebug`, `aapt dump badging`, `apksigner verify`, forbidden permission/network scan, and emulator UI QA all passed.
- Android UI QA evidence for 0.1.6 is under `.omo/ulw-loop/two-improvements-impl-20260629/evidence`.
- Local-only release note `C:\MyProject\yulchive-astro\src\pages\ibs-care.astro` was updated to 0.1.6, built successfully, checked against local-only route tests, and visually verified on desktop/mobile Chrome screenshots.
- Post-review fixes on 2026-06-29:
  - `windowedPostureLikely` now requires real orientation samples, not accelerometer-only stillness.
  - Personal learning now uses `PersonalPatternSnapshot`/`PersonalPatternStore` feature-summary keys; the unused `PersonalPatternProfile.rawSampleCount()` mirror was removed.
  - `BackgroundBowelDetectionService` no longer reads location while the activity is not visible. Pending background candidates are movement-checked in foreground before prefill.
  - `DeviceFeatureCoordinator` split sensor/learning coordination out of `MainActivity`; current pure-ish LOC is `MainActivity.java` 246 and `BackgroundBowelDetectionService.java` 162.
  - Post-FGS evidence: `post-fgs-gradle-regression-1.txt`, `post-fgs-android-ui-qa-v0.1.6-7.txt`, `post-review-code-security-report.md`, `post-review-manual-qa-matrix.md`.

Continuation audit, latest regenerated on 2026-06-28:

- `app/build.gradle` now wires `:app:assembleDebug` to generate reproducible versioned debug artifacts:
  - `app/build/outputs/apk/debug/ibs-care-v0.1.5-6-debug.apk`
  - `ibs-care-v0.1.5-6-debug-apk.zip`
- 2026-06-28 `app-debug.apk` and `ibs-care-v0.1.5-6-debug.apk` SHA256:
  `1A86957B326D7B88C19A190F5366D6C8BCD972BB6CC9880B5F9E964BC058F010`
- 2026-06-28 regenerated ZIP SHA256:
  `EE3E41D79B344E1B4E073FC03119D4C2FE3075A3763688C9B17B0954DC49A883`
- `:app:testDebugUnitTest` and `:app:assembleDebug` were re-run successfully in `C:\MyProject\ibscare-android`.
- 2026-06-28 APK badging re-confirmed `versionCode='6'`, `versionName='0.1.5'`.
- Targeted scan found no `INTERNET`, Bluetooth, `ACCESS_BACKGROUND_LOCATION`, app logging, or common HTTP client references in source/build files.
- APK update UI QA was later run on `emulator-5554`; evidence remains under `.codex-handoff/evidence`.

APK self-update implementation on 2026-06-27:

- Implemented the local APK update launcher path requested for phone testing.
- `MainActivity` now shows a `폰 테스트 업데이트` panel with `APK 파일 선택`.
- The app opens Android DocumentsUI with `ACTION_OPEN_DOCUMENT`, also accepts APK `ACTION_SEND` shares, stages the selected APK with `PackageInstaller`, and launches Android's user-confirmed update dialog on `STATUS_PENDING_USER_ACTION`.
- Update responsibilities are split into `LocalApkUpdateController`, `PackageInstallerApkStager`, and pure `LocalApkUpdatePolicy` with real JUnit coverage.
- `AndroidManifest.xml` now declares `REQUEST_INSTALL_PACKAGES`, keeps `INTERNET` absent, sets `MainActivity` to `singleTop`, and adds APK share MIME filters for `application/vnd.android.package-archive` and `application/octet-stream`.
- If the phone has not allowed this app to request unknown-app installs, the app shows `설치 권한 필요` and opens this app's `Install unknown apps` settings screen.
- 2026-06-28 APK SHA256: `1A86957B326D7B88C19A190F5366D6C8BCD972BB6CC9880B5F9E964BC058F010`.
- 2026-06-28 phone-test ZIP SHA256: `DF9C9A0048B024F281CD639144DCA191F737785595C2E0A1161244B62FA8F421`.
- 2026-06-28 root debug ZIP SHA256: `EE3E41D79B344E1B4E073FC03119D4C2FE3075A3763688C9B17B0954DC49A883`.
- Verification: `:app:testDebugUnitTest` with 6 executed JUnit tests, `:app:lintDebug`, `:app:assembleDebug`, `aapt` permission/manifest inspection, `apksigner verify`, emulator UI QA through DocumentsUI and PackageInstaller.
- Emulator QA reached the Android package installer dialog showing `Do you want to update this app?` and the `Update` button with the final APK. Evidence: `.codex-handoff/evidence/apk-update-final-verification.md`, `.codex-handoff/evidence/apk-update-final-packageinstaller-window.xml`, `.codex-handoff/evidence/apk-update-final-packageinstaller-screen.png`, and `.codex-handoff/evidence/apk-update-manual-qa-matrix.md`.
- Release note rule: every new IBS Care `versionName`, `versionCode`, APK/ZIP artifact, or artifact hash must update `C:\MyProject\yulchive-astro\src\data\ibsCareReleases.mjs` and the local-only `/ibs-care` pages in the same task before the work is considered done. This rule is also recorded in `C:\MyProject\AGENTS.md` and the project Wiki.

## Product Context

The app is an IBS bowel-record assistant. It helps users avoid missing bowel movement records, but it is not medical diagnosis.

Core user-facing requirements established so far:

- Explain Bristol stool types in plain Korean labels rather than only `1형`, `2형`, etc.
- Show app version in the UI and APK file names so old APKs are not confused with current ones.
- Detect likely bowel-session candidates even when the app is closed.
- Candidate detection should not auto-save. It should prompt the user to confirm.
- Moving situations such as subway, bus, or GPS movement should be excluded.
- Location should not be monitored continuously. It is checked briefly only after a high-likelihood candidate appears.
- Battery/data impact should remain low: normal mode uses accelerometer-based sensing; location is only a short candidate-time gate; no server data use.

## Implemented Detection Logic

Likely-session scoring is centered in:

- `app/src/main/java/com/ibscare/android/session/BowelSessionScorer.java`
- `app/src/main/java/com/ibscare/android/session/MotionSessionSampler.java`
- `app/src/main/java/com/ibscare/android/session/MotionFeatures.java`

Movement exclusion is centered in:

- `app/src/main/java/com/ibscare/android/session/CandidateMovementGate.java`
- `app/src/main/java/com/ibscare/android/session/LocationMovementSnapshot.java`

Movement gate rules:

- Exclude if reliable current location speed is `>= 0.9 m/s`.
- Exclude if reliable fixes move `>= 75 m` within `5 minutes`.
- Ignore unreliable locations with accuracy worse than `80 m`.
- Foreground and background checks use an `8 s` timeout.
- Foreground and background checks ignore stale pre-candidate cached locations and retry for a fresh fix before falling back.

Usual bowel-window scoring:

- As of 2026-06-27, `MotionSessionSampler.isUsualWindow()` excludes only `01:00` through `07:59`.
- Hours `00` and `08` through `23` are eligible for the usual-window `+10` score.
- `MotionSessionSamplerCliTest` covers the `00`, `01`, `07`, and `08` hour boundaries.

Posture scoring:

- `seatedPostureLikely` is set when the phone is screen-active and stationary long enough with either stable posture or hand-held viewing evidence.
- `sitTransitionLikely` and `handheldViewingLikely` are explicit `MotionFeatures` signals.
- `MotionSessionSampler` separates large body movement from hand-held phone micro-motion so a phone held while seated can be scored without requiring perfectly low acceleration variance.
- `BowelSessionScorer.hasCandidateEvidence()` is the foreground/background gate. It allows the old 3+ minute stationary path and the new 2+ minute hand-held viewing/seated posture path.
- This adds to candidate confidence but does not auto-save records.

2026-06-28 posture refinement:

- Added RED/GREEN coverage for the phone-test failure mode where toilet sitting with a hand-held screen-active phone did not reach prompt confidence.
- `BowelSessionScorerTest` now wraps the CLI scenario tests so `:app:testDebugUnitTest` executes the detection scenarios in Gradle.
- Verification: `:app:testDebugUnitTest` succeeded with JUnit 7 tests, `:app:lintDebug` succeeded, `:app:assembleDebug` succeeded, and corrected permission scan found no new `INTERNET`, microphone, Accessibility, Activity Recognition, or high-rate sensor permissions.
- Evidence root: `.omo/ulw-loop/ibs-posture-code-20260628/evidence`.
- Local-only release note `C:\MyProject\yulchive-astro\src\pages\ibs-care.astro` was updated with the new detection change and artifact hashes.

## Android Runtime Behavior

Foreground flow:

- `MainActivity` prompts after a high-likelihood candidate only if movement gate does not exclude it.
- If movement is detected, UI shows `이동 중 제외 · 가능성 0점` and does not show the confirmation popup.

Background flow:

- `BackgroundBowelDetectionService` runs as a foreground service.
- After the app is sent HOME, dumpsys confirmed `isForeground=true`.
- The foreground service notification title is `배변 기록 후보 감지 중`.

Permissions intentionally present:

- `POST_NOTIFICATIONS`
- `ACCESS_COARSE_LOCATION`
- `ACCESS_FINE_LOCATION`
- `FOREGROUND_SERVICE`
- `FOREGROUND_SERVICE_SPECIAL_USE`
- `REQUEST_INSTALL_PACKAGES`

Permissions intentionally absent:

- `ACCESS_BACKGROUND_LOCATION`
- `INTERNET`
- Bluetooth permissions

## Build Artifacts

Current APK artifacts:

- `app/build/outputs/apk/debug/app-debug.apk`
- `app/build/outputs/apk/debug/ibs-care-v0.1.6-7-debug.apk`
- `app/build/outputs/apk/debug/ibs-care-v0.1.6-7-debug-phone-test.zip`
- `ibs-care-v0.1.6-7-debug-apk.zip`

The versioned APK and ZIP are generated automatically by `:app:assembleDebug`.

Development install/update:

- FOTA is not applicable to this debug APK workflow; it is an OS/firmware update channel, not a normal app update channel.
- The app still has no `INTERNET` permission, so it does not download APKs from a server. This is separate from Play In-App Updates, where Play/Play Core owns the update flow.
- Use `powershell -ExecutionPolicy Bypass -File tools\install-debug-apk.ps1` for USB updates. It builds the latest debug APK and runs `adb install -r`, preserving app data.
- If no authorized device is connected, the script fails with `No authorized Android device found. Connect the phone with USB debugging enabled.`
- For USB-free phone testing, transfer the APK or phone-test ZIP to the phone, unzip if needed, open IBS Care, tap `APK 파일 선택`, choose the APK, and accept Android's update confirmation.

Local APK self-update feasibility:

- As of 2026-06-27, option 3 is implemented as a user-confirmed local APK install launcher, not silent FOTA-style auto-update on an ordinary personal phone.
- Android update acceptance requires the same application ID, same signing certificate, and same-or-higher versionCode; user acceptance can still be required.
- `PackageInstaller` can stage app installs, but ordinary apps may require user intervention at commit. Silent completion is for device owner / affiliated profile owner style managed-device cases.
- Newer no-user-action `PackageInstaller` paths also require strict conditions such as installer/update-owner/self-update state plus `UPDATE_PACKAGES_WITHOUT_USER_ACTION`; always be ready for `STATUS_PENDING_USER_ACTION`.
- Implementation is networkless: the user transfers an APK file, then IBS Care accepts/picks that file and launches Android's installer through `PackageInstaller`.
- First device QA found `Files still open` because the APK write stream was still open at `commit()`. The implementation now closes the stream before commit, and the emulator reaches Android's update confirmation dialog.
- Evidence: `.omo/ulw-loop/evidence/apk-self-update-feasibility.md`.

SHA256 hashes are recorded in:

- `.codex-handoff/evidence/android-location-posture-artifact-hashes-final-3.txt`

The continuation audit above records the current regenerated ZIP hash after Gradle artifact automation.

## Verification Evidence

Final copied evidence is under:

- `.codex-handoff/evidence`

Key files:

- RED evidence: `.codex-handoff/evidence/android-location-posture-red.txt`
- Unit tests: `.codex-handoff/evidence/android-location-posture-green-tests-9.txt`
- Build: `.codex-handoff/evidence/android-location-posture-build-8.txt`
- UI QA: `.codex-handoff/evidence/android-location-posture-ui-qa-final-11.txt`
- Movement exclusion QA: `.codex-handoff/evidence/android-movement-gate-final-qa.txt`
- Movement screenshot: `.codex-handoff/evidence/android-movement-gate-final.png`
- Foreground service after HOME: `.codex-handoff/evidence/android-location-posture-dumpsys-services-final-3.txt`
- Notification dump: `.codex-handoff/evidence/android-location-posture-dumpsys-notification-final-3.txt`
- APK metadata: `.codex-handoff/evidence/android-location-posture-aapt-final-3.txt`
- Privacy scan: `.codex-handoff/evidence/android-location-posture-privacy-scan-final-4.txt`
- ULW notepad: `.codex-handoff/evidence/notepad-ibs-android-location-gate.md`
- New project test evidence: `.codex-handoff/evidence/new-project-testDebugUnitTest.txt`
- New project build evidence: `.codex-handoff/evidence/new-project-assembleDebug.txt`

Verified final signals:

- `assembleDebug`: success
- `testDebugUnitTest`: success
- After copying to `C:\MyProject\ibscare-android`, `testDebugUnitTest` and `assembleDebug` were run again successfully.
- UI QA: `ANDROID_UI_QA_PASS`
- Movement exclusion QA: `MOVEMENT_GATE_FINAL_QA_PASS`
- 2026-06-28 APK metadata: `versionCode='6'`, `versionName='0.1.5'`
- Privacy scan: `NO_INTERNET_BLUETOOTH_BACKGROUND_LOCATION_OR_APP_LOGGING_MATCHES`

## Useful Commands

Set Java before Gradle commands if needed:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
```

Build:

```powershell
& 'C:\Users\mymelodyPC\.gradle\wrapper\dists\gradle-8.14-all\c2qonpi39x1mddn7hk5gh9iqj\gradle-8.14\bin\gradle.bat' clean :app:assembleDebug
```

Unit tests:

```powershell
& 'C:\Users\mymelodyPC\.gradle\wrapper\dists\gradle-8.14-all\c2qonpi39x1mddn7hk5gh9iqj\gradle-8.14\bin\gradle.bat' :app:testDebugUnitTest
```

UI QA:

```powershell
powershell -ExecutionPolicy Bypass -File tools\qa-android-ui.ps1
```

## Next Thread Startup Prompt

Use this when starting a new Codex thread in project `C:\MyProject\ibscare-android`:

```text
이 프로젝트는 IBS 배변 기록 Android 앱입니다. 먼저 CODEX_HANDOFF.md와 C:\MyProject\wiki\projects\ibscare-android.md를 읽고, 현재 구현/검증 상태를 파악한 뒤 이어서 작업해 주세요.
```

