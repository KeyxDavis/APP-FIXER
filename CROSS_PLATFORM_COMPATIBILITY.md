# Cross-Platform Compatibility Notes

## Summary
The app is already written as a Kivy desktop application and can be packaged for Windows, Linux, and macOS. The main compatibility work is not in the app logic itself, but in packaging, file access, and your release process.

## What helps compatibility

### 1. Use platform-specific build scripts
The repo now includes separate build scripts for Linux and macOS in addition to the Windows build.

### 2. Keep paths resilient
The app already tries to handle packaged environments using sys._MEIPASS and app user data directories. That is important for packaged builds.

### 3. Keep all config values externalized
Use environment variables or a sidecar config file instead of hardcoding secrets into the binary. This keeps the app portable and safer across environments.

### 4. Test on real target OS machines
A build can be created on one machine and still fail on another because of desktop environment differences, permissions, or library availability. Testing should happen on a real Linux or macOS system before release.

## Linux-specific tuning
- Prefer building on an Ubuntu or Debian GitHub runner first.
- Keep the build script simple and reproducible.
- Test the resulting binary on a desktop environment with the same package family as your intended users.
- If you want the best experience, package in the same distro family used by your target audience.

## macOS-specific tuning
- Use the macOS workflow in GitHub Actions or build on a Mac machine.
- Use a windowed app bundle for desktop users.
- Check for Gatekeeper restrictions and app security approvals.
- Test the app bundle on a real Mac before publishing to a broad audience.

## Windows-specific notes
- The existing Windows workflow remains the most straightforward path for desktop deployment.
- The executable is a good option for users who want a simple launcher without Python installed.

## Recommended final setup
- Maintain a dedicated build artifact for each OS.
- Use GitHub Actions to generate all three builds consistently.
- Publish the artifact directly from the release page.
- Keep a short and clear OS note in the release announcement.

## Extra improvement suggestions
- Add a version banner in the app UI.
- Show the build platform in the About or Settings page.
- Add a small diagnostics page for startup checks and configuration status.
- Add a basic startup validation that checks whether the app is running in local or cloud mode before the UI opens.
