# Staff Attendance Application

A Kivy desktop application for registering staff, recording daily attendance, tracking late arrivals, managing term summaries, and exporting reports.

## Project files

- `STAFF ATTENDANCE(GENERAL)KIVY.py`: Kivy user interface and application flow.
- `db.py`: Built-in SQLite database used for local mode.
- `local_schema.sql`: Reference schema for the local SQLite database.
- `supabase_db.py`: Optional Supabase/PostgreSQL database adapter.
- `database_schema.sql`: Supabase database schema, policies, and attendance functions.
- `requirements.txt`: Python dependencies.
- `asolo_config.example.json`: Safe configuration template for cloud mode.
- `run_windows.bat`: Windows launcher.
- `build_windows.bat`: Builds a shareable Windows executable.
- `.vscode/launch.json`: VS Code debug configuration.

## Local setup

1. Install Python 3.10 or newer.
2. Open PowerShell in this folder.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

5. Start the application:

   ```powershell
   python "STAFF ATTENDANCE(GENERAL)KIVY.py"
   ```

   You can also double-click `run_windows.bat`.

The local SQLite database is created automatically in the user's `AsoloAttendanceApp` data directory. The first account created becomes an administrator. Later accounts are regular staff accounts.

On the first launch, the app requires a school name and logo before it displays the login page. Branding is saved in the Kivy user data directory.

## Supabase setup

1. Create a Supabase project.
2. Open the Supabase SQL Editor and run `database_schema.sql`.
3. Create a user in Supabase Authentication.
4. Insert the school, settings, application status, membership, and user profile records shown in the example section of the SQL file. Replace the placeholder school id and user UUID.
5. Copy `asolo_config.example.json` to `asolo_config.json`.
6. Replace the URL, anon key, and school ids with your project values.
7. Start the app normally.

Cloud mode is selected only when a valid Supabase URL, anon key, and school id are configured. Otherwise the app uses local SQLite mode.

## Build shareable desktop releases

Install PyInstaller once:

```powershell
python -m pip install pyinstaller
```

### Windows

Double-click `build_windows.bat`, or run it from PowerShell:

```powershell
./build_windows.bat
```

The executable is created at `dist/AsoloAttendance.exe`.

### Linux

```bash
bash ./build_linux.sh
```

The Linux binary is created in `dist/AsoloAttendance`.

### macOS

```bash
bash ./build_macos.sh
```

The macOS app bundle is created in `dist/AsoloAttendance.app`.

If `asolo_config.json` exists, the build scripts copy it beside the executable or app bundle. Keep that file beside the shipped app only if it contains only public values. Do not include service-role keys or sensitive deployment details.

To give people a download link, create a GitHub Release in this repository and upload the matching OS artifact. The installed app checks the repository's latest public release after startup and shows users an update prompt with a button to open the release download page. Users do not need to be sent a new link manually.

Before building a release, update `APP_VERSION` in `STAFF ATTENDANCE(GENERAL)KIVY.py` (for example, `1.0.1`), then create a matching Git tag and GitHub Release such as `v1.0.1`. Mark it as the latest release and upload the Windows, Linux, and macOS artifacts. The checker continues to work offline; it simply shows no prompt when GitHub cannot be reached.

If the releases move to another GitHub repository, set `ASOLO_RELEASE_REPOSITORY` to `owner/repository` beside the executable or in the environment before starting the app.

## Release readiness

This app is versioned as `1.0.0` and includes cross-platform packaging scripts for Windows, Linux, and macOS. Before shipping, run the smoke tests and a real desktop launch on the target OS.

## Security notes

- Do not commit `asolo_config.json` or any service-role key.
- Use only the Supabase anon key in the desktop client.
- Keep database RLS enabled in production.
- Passwords are hashed before they are stored in local SQLite mode.
- Supabase passwords are managed by Supabase Auth.

## Validation

Run the basic checks from PowerShell:

```powershell
python -m py_compile "STAFF ATTENDANCE(GENERAL)KIVY.py" db.py supabase_db.py
python -c "from db import Database; print('Database module loaded')"
```
