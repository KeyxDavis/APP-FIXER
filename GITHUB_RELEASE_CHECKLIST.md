# GitHub Release Checklist

## Before release

- [ ] Confirm the app builds on Windows.
- [ ] Confirm the app builds on Linux.
- [ ] Confirm the app builds on macOS.
- [ ] Validate at least one smoke test on each platform.
- [ ] Ensure no confidential keys or secrets are included in the release artifacts.
- [ ] Review the project changelog or release notes.
- [ ] Check the app version number before tagging.

## Build and artifact checks

- [ ] Run the Windows build and confirm the exe is produced.
- [ ] Run the Linux build and confirm the binary is produced.
- [ ] Run the macOS build and confirm the app bundle is produced.
- [ ] Verify each artifact is named clearly for the target OS.
- [ ] Confirm the config file is either included only where required or intentionally omitted.

## GitHub release steps

- [ ] Create the Git tag for the release.
- [ ] Push the tag to GitHub.
- [ ] Open the GitHub Releases page.
- [ ] Create a new release with the release notes.
- [ ] Upload the Windows artifact.
- [ ] Upload the Linux artifact.
- [ ] Upload the macOS artifact.
- [ ] Mark the release as the latest stable version if appropriate.
- [ ] Share a short download note for end users explaining which build to use.

## Post-release verification

- [ ] Download one build from the release.
- [ ] Confirm the downloaded file launches on the target OS.
- [ ] Test login and admin setup on each OS build.
- [ ] Test one attendance flow on each OS build.
- [ ] Capture any issues for the next patch release.
