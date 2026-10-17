<#
.SYNOPSIS
  Start an Android emulator and run the demo app on it (Windows).

.DESCRIPTION
  Finds the Android SDK (ANDROID_HOME, ANDROID_SDK_ROOT, or the Android Studio default under
  %LOCALAPPDATA%\Android\Sdk) and Flutter (on PATH, or FLUTTER_ROOT). Starts the named emulator, or
  the first one listed, waits until it has booted, then runs the app from app/ with
  --no-enable-impeller (Flutter's Impeller renderer can hang on emulators without a graphics card).

.PARAMETER Avd
  Emulator to start. Default: the first one `emulator -list-avds` prints.

.PARAMETER Fresh
  Clear the app's data before running, so it starts with no model installed (to try the download).

.EXAMPLE
  .\tools\run_emulator.ps1
  .\tools\run_emulator.ps1 -Avd Pixel_8 -Fresh
#>
param(
    [string]$Avd = "",
    [switch]$Fresh
)
$ErrorActionPreference = "Stop"
$AppId = "io.github.kurtvalcorza.trapcounter"
$Root = Split-Path -Parent $PSScriptRoot

# Android SDK
$Sdk = @($env:ANDROID_HOME, $env:ANDROID_SDK_ROOT, (Join-Path $env:LOCALAPPDATA "Android\Sdk")) |
    Where-Object { $_ -and (Test-Path (Join-Path $_ "platform-tools\adb.exe")) } | Select-Object -First 1
if (-not $Sdk) { throw "Android SDK not found. Set ANDROID_HOME, or install it with Android Studio (see docs/setup.md)." }
$Adb = Join-Path $Sdk "platform-tools\adb.exe"
$Emulator = Join-Path $Sdk "emulator\emulator.exe"
if (-not (Test-Path $Emulator)) { throw "The Android Emulator is not installed. Add it in Android Studio's SDK Manager." }

# Flutter
$Flutter = (Get-Command flutter -ErrorAction SilentlyContinue).Source
if (-not $Flutter -and $env:FLUTTER_ROOT) { $Flutter = Join-Path $env:FLUTTER_ROOT "bin\flutter.bat" }
if (-not $Flutter -or -not (Test-Path $Flutter)) { throw "Flutter not found. Add it to PATH or set FLUTTER_ROOT (see docs/setup.md)." }

# Emulator
if (-not $Avd) {
    $Avd = & $Emulator -list-avds | Select-Object -First 1
    if (-not $Avd) { throw "No emulator found. Create one in Android Studio's Device Manager." }
}
$Running = & $Adb devices | Select-String "^emulator-\d+\s+device"
if ($Running) {
    Write-Host "An emulator is already running; using it."
} else {
    Write-Host "Starting emulator $Avd ..."
    Start-Process -FilePath $Emulator -ArgumentList @("-avd", $Avd) -WindowStyle Minimized
    & $Adb wait-for-device
    $deadline = (Get-Date).AddMinutes(5)
    while ((& $Adb shell getprop sys.boot_completed 2>$null) -ne "1") {
        if ((Get-Date) -gt $deadline) { throw "The emulator did not finish booting within 5 minutes." }
        Start-Sleep -Seconds 3
    }
    Write-Host "Emulator booted."
}
$Device = ((& $Adb devices | Select-String "^(emulator-\d+)\s+device").Matches | Select-Object -First 1).Groups[1].Value

if ($Fresh) {
    Write-Host "Clearing the app's data (no model installed) ..."
    & $Adb -s $Device shell pm clear $AppId 2>$null | Out-Null
}

Push-Location (Join-Path $Root "app")
try {
    & $Flutter run --no-enable-impeller -d $Device
} finally {
    Pop-Location
}
