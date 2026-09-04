# PowerShell script to create Desktop Shortcut for Transcripter
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    $pythonw = "pythonw.exe"
}

$icon = Join-Path $projectRoot "assets\icon.ico"
if (-not (Test-Path $icon)) {
    $icon = Join-Path $projectRoot "assets\icon.png"
}

$wsh = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
$shortcutPath = Join-Path $desktop "Transcripter.lnk"

$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "-m src.main"
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = $icon
$shortcut.Description = "Transcripter - Real-time AI Audio & Meeting Transcription"
$shortcut.Save()

Write-Host "Created desktop shortcut at: $shortcutPath" -ForegroundColor Green
