# J.A.R.V.I.S Windows Installer

The Windows installer is built in CI from the same PyInstaller payload as the portable package.

- Installs per-user into \`%LOCALAPPDATA%\Programs\Zobaerio\JARVIS\`; administrator rights are not required.
- Adds a Start Menu shortcut and offers an optional Desktop shortcut.
- Offers to launch J.A.R.V.I.S after setup.
- Uninstall removes the installed application but intentionally preserves user settings and task history under \`%APPDATA%\Zobaerio\Jarvis\`.
- The current CI output is an **unsigned installer**. Windows SmartScreen may show a reputation warning. Do not bypass security controls; only run builds from the trusted repository workflow after reviewing the source and artifact provenance.

The artifact is considered ready for user testing only after the Windows Installer Package workflow succeeds and package verification passes. CI compilation alone does not replace manual testing on a supported Windows PC (install, launch, app icon, shortcuts, startup setting, task history, upgrade and uninstall).


## Download options

### CI artifact (temporary)

1. Open the [Windows Installer Package workflow runs](https://github.com/zobaerio/jarvisai/actions/workflows/windows-installer-build.yml).
2. Open a successful run on the intended commit.
3. Under **Artifacts**, download `JARVIS-Windows-Installer` and extract the ZIP.
4. Run `JARVIS-Setup.exe` from the extracted folder.

Artifacts expire according to the workflow retention policy, so they are not permanent download links.

### GitHub Release (persistent)

For a published version, open the repository's [Releases page](https://github.com/zobaerio/jarvisai/releases) and download `JARVIS-Setup.exe` plus `JARVIS-Setup.exe.sha256`. The release workflow runs only when a matching version tag (`v<APP_VERSION>`, for example `v1.7.3`) is pushed. It checks that the tag matches the application's `APP_VERSION`, builds the installer, verifies required payload files, and publishes a SHA-256 checksum.

To verify a downloaded installer in PowerShell, run this from the folder containing both files:

```powershell
Get-FileHash .\JARVIS-Setup.exe -Algorithm SHA256
Get-Content .\JARVIS-Setup.exe.sha256
```

Compare the hash printed by the first command with the hash in the checksum file. Do not run the installer if the values differ. A matching checksum confirms file integrity against the published checksum; it does not prove the installer is code-signed or independently audited.


## Platform installation and update behavior

For Android/tablet/PC support boundaries, step-by-step install instructions, and the current release/update lifecycle, see [INSTALL_AND_UPDATE_GUIDE.md](INSTALL_AND_UPDATE_GUIDE.md). The current desktop app does not yet include an in-app automatic updater, and a GitHub commit alone does not update installed copies.
