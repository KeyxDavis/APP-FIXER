#!/usr/bin/env bash
set -eu

cd "$(dirname "$0")"

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name AsoloAttendance \
  --exclude-module pygments \
  --exclude-module IPython \
  --exclude-module pytest \
  --exclude-module notebook \
  --exclude-module setuptools \
  --exclude-module pkg_resources \
  "STAFF ATTENDANCE(GENERAL)KIVY.py"

if [ -f "asolo_config.json" ]; then
  cp "asolo_config.json" "dist/asolo_config.json"
fi

echo "Build complete: dist/AsoloAttendance.app"
