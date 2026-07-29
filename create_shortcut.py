"""Create 'Resolume Autosave.lnk' with the star icon."""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ICO = APP_DIR / "assets" / "stars.ico"
LNK = APP_DIR / "Resolume Autosave.lnk"
TARGET = APP_DIR / "start.bat"


def create_shortcut() -> Path:
    if not ICO.is_file():
        from icons import generate_all

        generate_all()

    try:
        import win32com.client  # type: ignore
    except ImportError:
        # Fallback via PowerShell COM
        import subprocess

        ps = f"""
$s = New-Object -ComObject WScript.Shell
$l = $s.CreateShortcut('{LNK}')
$l.TargetPath = '{TARGET}'
$l.WorkingDirectory = '{APP_DIR}'
$l.IconLocation = '{ICO},0'
$l.Description = 'Resolume composition autosave'
$l.Save()
"""
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=True,
            capture_output=True,
            text=True,
        )
        return LNK

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(LNK))
    shortcut.Targetpath = str(TARGET)
    shortcut.WorkingDirectory = str(APP_DIR)
    shortcut.IconLocation = f"{ICO},0"
    shortcut.Description = "Resolume composition autosave"
    shortcut.save()
    return LNK


if __name__ == "__main__":
    path = create_shortcut()
    print(path)
    sys.exit(0)
