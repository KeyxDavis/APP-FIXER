# Release Notes for Desktop Builds

## Overview

This project now supports building desktop releases for Windows, Linux, and macOS using PyInstaller. Each platform has a dedicated build script and the GitHub Actions workflow publishes each artifact separately.

## Supported Platforms

### Windows

- Build script: build_windows.bat
- Output: dist/AsoloAttendance.exe
- Best for: corporate desktop users and users who want a single exe launcher

### Linux

- Build script: build_linux.sh
- Output: dist/AsoloAttendance
- Best for: Ubuntu/Debian-based Linux distributions
- Notes:
  - The generated binary is a self-contained app but still depends on the Linux desktop environment and the correct GTK/Kivy runtime libraries being available.
  - For best compatibility, test on the target distro before sharing widely.

### macOS

- Build script: build_macos.sh
- Output: dist/AsoloAttendance.app
- Best for: macOS users on supported desktop systems
- Notes:
  - Use the windowed PyInstaller mode for the app bundle.
  - Gatekeeper may require the user to approve the app before first launch.
  - The generated app should be tested on a real macOS machine before publishing broadly.

## Build Process

1. Install Python 3.11 or newer.
2. Install the repo dependencies from requirements.txt.
3. Run the platform-specific build script.
4. Copy asolo_config.json next to the final binary only if you intend to ship cloud configuration with the build.
5. Upload the generated artifact to a GitHub release.

## Recommended Release Strategy

- Keep a separate build artifact for each operating system.
- Publish one Windows, one Linux, and one macOS build in the GitHub release.
- Avoid distributing a config file publicly unless it contains only safe public values.
- Prefer uploading the app bundle only and sharing credentials or config separately when needed.

## Release Notes Template

Use this for each version:

### Version X.Y.Z

- Added: <feature or fix>
- Improved: <platform compatibility or packaging improvement>
- Fixed: <important bug fix>
- Known issues: <list or None>

## Distribution Safety

- Never publish service-role keys.
- Use the anon key only for the desktop client.
- Keep RLS enabled in production and only share safe public info with the app.
- Keep cloud configuration files separate from public release assets when the project is deployed to external users.
