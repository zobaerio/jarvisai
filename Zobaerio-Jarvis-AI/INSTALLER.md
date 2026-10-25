# J.A.R.V.I.S Windows Installer

The Windows installer is built in CI from the same PyInstaller payload as the portable package.

- Installs per-user into \`%LOCALAPPDATA%\Programs\Zobaerio\JARVIS\`; administrator rights are not required.
- Adds a Start Menu shortcut and offers an optional Desktop shortcut.
- Offers to launch J.A.R.V.I.S after setup.
- Uninstall removes the installed application but intentionally preserves user settings and task history under \`%APPDATA%\Zobaerio\Jarvis\`.
- The current CI output is an **unsigned installer**. Windows SmartScreen may show a reputation warning. Do not bypass security controls; only run builds from the trusted repository workflow after reviewing the source and artifact provenance.

The artifact is considered ready for user testing only after the Windows Installer Package workflow succeeds and package verification passes. CI compilation alone does not replace manual testing on a supported Windows PC (install, launch, app icon, shortcuts, startup setting, task history, upgrade and uninstall).
