# J.A.R.V.I.S — Install & Update Guide (Android, Tablet, PC)

This guide distinguishes the current supported desktop application from future mobile builds. The current application is a Python/Tkinter desktop program; it is **not an Android APK** and should not be installed on Android by renaming the Windows installer.

## Platform support today

| Device | Current supported route | Notes |
|---|---|---|
| Windows 11 PC/laptop | Windows installer or portable build | Primary supported platform. Use a 64-bit Windows build. |
| Windows tablet | Same Windows installer/portable build | Works only when the tablet runs supported Windows; touch optimization may be limited. |
| Android phone/tablet | No native APK currently published | A native Android app requires a separate mobile UI/build and device testing. Windows .exe/.zip cannot install on Android. |
| macOS/Linux PC | Not currently packaged/supported by the Windows installer | Python source may require platform-specific dependency and UI work; do not assume compatibility. |

## Recommended Windows install

1. Open the repository's [Releases page](https://github.com/zobaerio/jarvisai/releases).
2. Download JARVIS-Setup.exe and JARVIS-Setup.exe.sha256 from the latest published release.
3. In PowerShell, from the download folder, run:
   ```powershell
   Get-FileHash .\JARVIS-Setup.exe -Algorithm SHA256
   Get-Content .\JARVIS-Setup.exe.sha256
   ```
4. Compare the printed SHA-256 value with the checksum file. If they differ, do not run the installer.
5. Run JARVIS-Setup.exe. It installs per-user, so administrator permission is not normally required. Choose the optional Desktop shortcut if wanted.
6. Open J.A.R.V.I.S from the Start Menu/Desktop shortcut and configure your AI provider in Settings.
7. Keep your settings and task history: uninstall intentionally preserves user data in %APPDATA%\Zobaerio\Jarvis\.

**SmartScreen:** The current installer is unsigned. A reputation warning may appear. Only use artifacts from the trusted repository's Releases page after checking provenance and checksum; do not blindly bypass security warnings.

## Temporary CI artifact (testing only)

1. Open the [Windows Installer Package workflow](https://github.com/zobaerio/jarvisai/actions/workflows/windows-installer-build.yml).
2. Open a successful run for the commit you intend to test.
3. Download the JARVIS-Windows-Installer artifact and extract it.
4. Run JARVIS-Setup.exe from the extracted folder.

CI artifacts expire and are not the permanent release channel.

## Source install (developers / advanced users)

1. Install 64-bit Python 3.12 on Windows.
2. Download/clone the repository and open Zobaerio-Jarvis-AI\.
3. Run install.bat, then run.bat.
4. Follow README_BN.md for Bengali setup and AI provider configuration.

## How updates work — important distinction

A commit or merged Pull Request on GitHub does **not by itself update an already-installed copy**. A distributable installer must be built and published as a versioned GitHub Release first.

The repository's release workflow is tag-triggered: it expects a tag such as v1.7.3 to match APP_VERSION, builds the Windows installer, checks required payload files, and publishes the installer plus SHA-256 checksum. Therefore:

- **GitHub code update only:** source changes; installed app stays unchanged.
- **Merged code + version bump + matching release tag + successful workflow:** a new installer appears on Releases.
- **Installed app:** for now, install the new published JARVIS-Setup.exe to update. The installer is designed for the same per-user location; back up important data before major upgrades.
- **Automatic update:** a future app update-checker can notify the user when a newer *published release* exists and offer to download/launch its installer after confirmation. It must not silently run arbitrary code just because any repository commit changed. This guide does not claim that an in-app automatic updater is already implemented.

A safe updater should verify HTTPS release metadata, compare semantic versions, verify the published checksum, ask for user confirmation, close the app cleanly, preserve user data, and provide a rollback/recovery path. It should check Releases—not raw commits—and never download/run unverified executable assets.

## Android / tablet future plan

For Android phones and Android tablets, the project needs a dedicated mobile interface and build pipeline (for example, a separately maintained Android client or a mobile-compatible web app). After implementation, the team must test install, permissions, screen sizes, offline behavior, secure API-key storage, updates and uninstall on real devices before publishing an APK/AAB. Until a verified release is published, there is no supported Android installer to download.

## Release checklist for maintainers

1. Finish changes in a PR and run the required CI checks.
2. Merge the PR only after reviewing the diff and CI results.
3. Update APP_VERSION in the source when preparing a release.
4. Push the matching tag v<APP_VERSION>.
5. Confirm the release workflow succeeds and the installer/checksum are attached.
6. Test fresh install and upgrade on a Windows machine; verify app launch, shortcuts, saved settings and task history.
7. Link users to the Release asset, not a temporary CI artifact.
