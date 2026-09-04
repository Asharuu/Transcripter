"""Desktop shortcut management for Transcripter."""

import os
import sys
import subprocess
from pathlib import Path


def create_desktop_shortcut() -> tuple[bool, str]:
    """Creates a Windows Desktop shortcut pointing to pythonw.exe running Transcripter silently."""
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        pythonw_path = project_root / ".venv" / "Scripts" / "pythonw.exe"
        if not pythonw_path.exists():
            pythonw_path = Path(sys.executable).parent / "pythonw.exe"
            if not pythonw_path.exists():
                pythonw_path = Path(sys.executable)

        icon_path = project_root / "assets" / "icon.ico"
        if not icon_path.exists():
            # Fallback to PNG if ICO doesn't exist
            icon_path = project_root / "assets" / "icon.png"

        # PowerShell command using WScript.Shell
        ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
$shortcutPath = Join-Path $desktop 'Transcripter.lnk'
$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = '{pythonw_path}'
$shortcut.Arguments = '-m src.main'
$shortcut.WorkingDirectory = '{project_root}'
$shortcut.IconLocation = '{icon_path}'
$shortcut.Description = 'Transcripter - Real-time AI Audio & Meeting Transcription'
$shortcut.Save()
Write-Output $shortcutPath
"""
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        if res.returncode == 0:
            created_path = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else "Desktop/Transcripter.lnk"
            return True, f"Shortcut successfully created at:\n{created_path}"
        else:
            return False, f"PowerShell error: {res.stderr.strip()}"
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    success, msg = create_desktop_shortcut()
    print("Success:", success)
    print("Message:", msg)
