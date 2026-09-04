# Build script to compile Launcher.cs into Transcripter.exe with embedded icon and metadata
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$icon = Join-Path $projectRoot 'assets\icon.ico'
$csSource = Join-Path $projectRoot 'Launcher.cs'
$outputExe = Join-Path $projectRoot 'Transcripter.exe'

Write-Host 'Compiling Transcripter.exe using csc.exe...' -ForegroundColor Cyan
& $csc /target:winexe /win32icon:$icon /out:$outputExe $csSource

if ($LASTEXITCODE -eq 0) {
    Write-Host 'Successfully built Transcripter.exe!' -ForegroundColor Green
    & $outputExe --install-shortcuts
} else {
    Write-Host 'Failed to compile Transcripter.exe' -ForegroundColor Red
}

$w = New-Object -ComObject WScript.Shell
$desk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Transcripter.lnk'
$prog = Join-Path ([Environment]::GetFolderPath('Programs')) 'Transcripter.lnk'
$dl = $w.CreateShortcut($desk)
$pl = $w.CreateShortcut($prog)
Write-Host "Desktop Target: $($dl.TargetPath)" -ForegroundColor Yellow
Write-Host "Desktop Icon:   $($dl.IconLocation)" -ForegroundColor Yellow
Write-Host "Programs Target: $($pl.TargetPath)" -ForegroundColor Yellow
Write-Host "Programs Icon:   $($pl.IconLocation)" -ForegroundColor Yellow


