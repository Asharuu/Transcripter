"""Windows Startup Apps and Start Menu integration for Transcripter."""

import os
import sys
import subprocess
from pathlib import Path

if os.name == "nt":
    import winreg

RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
APP_NAME = "Transcripter"


def get_project_paths() -> tuple[Path, Path, Path]:
    """Returns (project_root, pythonw_path, icon_path)."""
    project_root = Path(__file__).resolve().parent.parent.parent
    pythonw_path = project_root / ".venv" / "Scripts" / "pythonw.exe"
    if not pythonw_path.exists():
        pythonw_path = Path(sys.executable).parent / "pythonw.exe"
        if not pythonw_path.exists():
            pythonw_path = Path(sys.executable)

    icon_path = project_root / "assets" / "icon.ico"
    if not icon_path.exists():
        icon_path = project_root / "assets" / "icon.png"

    return project_root, pythonw_path, icon_path


def register_app_user_model_id() -> bool:
    """Registers AppUserModelID and icon associations in HKCU Software\\Classes."""
    if os.name != "nt":
        return False

    try:
        project_root, _, icon_path = get_project_paths()
        app_id = "Asharuu.Transcripter.Desktop.1.0"
        icon_str = str(icon_path.resolve())

        # Register AUMID for taskbar & notification branding
        key_path = rf"Software\Classes\AppUserModelId\{app_id}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "Transcripter")
            winreg.SetValueEx(k, "IconUri", 0, winreg.REG_SZ, icon_str)
            winreg.SetValueEx(k, "IconBackgroundColor", 0, winreg.REG_SZ, "0")

        # Register application DefaultIcon
        app_key = r"Software\Classes\Applications\Transcripter.exe"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key) as k:
            winreg.SetValueEx(k, "FriendlyAppName", 0, winreg.REG_SZ, "Transcripter")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key + r"\DefaultIcon") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, f"{icon_str},0")

        # Broadcast shell change
        import ctypes
        shell32 = ctypes.windll.shell32
        shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
        return True
    except Exception:
        return False


def install_start_menu_shortcut() -> tuple[bool, str]:
    """Installs Transcripter shortcut in Start Menu Programs so Windows Settings resolves its icon and metadata."""
    if os.name != "nt":
        return False, "Not running on Windows"

    try:
        register_app_user_model_id()
        project_root, pythonw_path, icon_path = get_project_paths()
        exe_path = project_root / "Transcripter.exe"

        # If compiled launcher exists, use it to set native AppUserModelID on shortcut
        if exe_path.exists():
            res = subprocess.run(
                [str(exe_path), "--install-shortcuts"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if res.returncode == 0:
                programs_path = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Transcripter.lnk"
                return True, str(programs_path)

        target_bin = str(exe_path) if exe_path.exists() else str(pythonw_path)
        args_str = "" if exe_path.exists() else "-m src.main"

        ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$programs = [Environment]::GetFolderPath([Environment+SpecialFolder]::Programs)
$shortcutPath = Join-Path $programs 'Transcripter.lnk'
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
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if res.returncode == 0:
            return True, res.stdout.strip()
        return False, res.stderr.strip()
    except Exception as e:
        return False, str(e)


def is_startup_enabled() -> bool:
    """Checks if Transcripter is configured in HKCU Run registry and not disabled in Windows Settings."""
    if os.name != "nt":
        return False

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
        winreg.CloseKey(key)

        # Check if disabled by user in Windows Settings -> Apps > Startup
        try:
            appr_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_KEY, 0, winreg.KEY_READ)
            bin_data, _ = winreg.QueryValueEx(appr_key, APP_NAME)
            winreg.CloseKey(appr_key)
            if bin_data and len(bin_data) > 0 and (bin_data[0] & 0x01 != 0 or bin_data[0] == 0x03):
                # Disabled in Windows Settings
                return False
        except (FileNotFoundError, OSError):
            pass

        return True
    except Exception:
        return False


def set_startup_enabled(enabled: bool, start_minimized: bool = True) -> tuple[bool, str]:
    """Enables or disables Transcripter in Windows Startup Apps."""
    if os.name != "nt":
        return False, "Not running on Windows"

    try:
        project_root, pythonw_path, _ = get_project_paths()
        exe_path = project_root / "Transcripter.exe"

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
        if enabled:
            if exe_path.exists():
                cmd = f'"{exe_path}"'
            else:
                cmd = f'"{pythonw_path}" -m src.main'

            if start_minimized:
                cmd += " --startup"

            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)

            # Re-enable in StartupApproved if previously disabled in Windows Settings
            try:
                appr_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
                # 0x02 indicates enabled in Windows Startup
                enabled_bytes = bytes([0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                winreg.SetValueEx(appr_key, APP_NAME, 0, winreg.REG_BINARY, enabled_bytes)
                winreg.CloseKey(appr_key)
            except (FileNotFoundError, OSError):
                pass

            # Also ensure Start Menu shortcut exists for icon and publisher recognition
            install_start_menu_shortcut()

            return True, "Transcripter added to Windows Startup Apps."
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True, "Transcripter removed from Windows Startup Apps."
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    print("Currently enabled:", is_startup_enabled())
    ok, msg = set_startup_enabled(True, start_minimized=True)
    print("Enable result:", ok, msg)
    print("Now enabled:", is_startup_enabled())
