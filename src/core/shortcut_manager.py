"""Desktop shortcut management for Transcripter."""

import os
import sys
import subprocess
from pathlib import Path


def create_desktop_shortcut() -> tuple[bool, str]:
    """Creates a Windows Desktop shortcut pointing to Transcripter.exe with AppUserModelID."""
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        exe_path = project_root / "Transcripter.exe"

        # If compiled launcher exists, use it to install shortcuts with native AppUserModelID
        if exe_path.exists():
            res = subprocess.run(
                [str(exe_path), "--install-shortcuts"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if res.returncode == 0:
                desktop_path = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "Transcripter.lnk"
                return True, f"Shortcut successfully created at:\n{desktop_path}"

        # Fallback to PowerShell WScript.Shell
        pythonw_path = project_root / ".venv" / "Scripts" / "pythonw.exe"
        if not pythonw_path.exists():
            pythonw_path = Path(sys.executable).parent / "pythonw.exe"
            if not pythonw_path.exists():
                pythonw_path = Path(sys.executable)

        target_bin = str(exe_path) if exe_path.exists() else str(pythonw_path)
        args_str = "" if exe_path.exists() else "-m src.main"

        icon_path = project_root / "assets" / "icon.ico"
        if not icon_path.exists():
            icon_path = project_root / "assets" / "icon.png"

        ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
$shortcutPath = Join-Path $desktop 'Transcripter.lnk'
$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = '{target_bin}'
$shortcut.Arguments = '{args_str}'
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
