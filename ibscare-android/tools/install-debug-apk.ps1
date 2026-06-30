param(
    [string]$Device = "",
    [string]$Apk = "app/build/outputs/apk/debug/ibs-care-v0.1.9-10-debug.apk",
    [switch]$NoBuild,
    [switch]$AllowDowngrade
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue) {
    $global:PSNativeCommandUseErrorActionPreference = $false
}

$workspace = Resolve-Path (Join-Path $PSScriptRoot "..")

function Resolve-Executable([string[]]$Candidates, [string]$Name) {
    foreach ($candidate in $Candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command -ne $null) {
        return $command.Source
    }

    throw "Could not find $Name. Install Android platform-tools or set the expected SDK/Gradle paths."
}

function Resolve-JavaHome() {
    if (-not [string]::IsNullOrWhiteSpace($env:JAVA_HOME) -and
            (Test-Path -LiteralPath (Join-Path $env:JAVA_HOME "bin\java.exe"))) {
        return $env:JAVA_HOME
    }

    $candidates = @(
        "C:\Program Files\Android\Android Studio\jbr",
        "$env:USERPROFILE\.antigravity\extensions\redhat.java-1.54.0-win32-x64\jre\21.0.10-win32-x86_64"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate "bin\java.exe")) {
            return $candidate
        }
    }

    throw "Could not find a Java runtime. Set JAVA_HOME to a JDK/JBR directory."
}

function Resolve-TargetDevice([string]$RequestedDevice, [string]$Adb) {
    if (-not [string]::IsNullOrWhiteSpace($RequestedDevice)) {
        return $RequestedDevice
    }

    $lines = & $Adb devices
    $devices = @()
    foreach ($line in $lines) {
        if ($line -match "^(\S+)\s+device$") {
            $devices += $Matches[1]
        }
    }

    if ($devices.Count -eq 0) {
        throw "No authorized Android device found. Connect the phone with USB debugging enabled."
    }
    if ($devices.Count -gt 1) {
        throw "Multiple devices found: $($devices -join ', '). Re-run with -Device <serial>."
    }

    return $devices[0]
}

$adb = Resolve-Executable @(
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
    "$env:ANDROID_HOME\platform-tools\adb.exe",
    "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe"
) "adb.exe"

if (-not $NoBuild) {
    $gradle = Resolve-Executable @(
        "$env:USERPROFILE\.gradle\wrapper\dists\gradle-8.14-all\c2qonpi39x1mddn7hk5gh9iqj\gradle-8.14\bin\gradle.bat",
        (Join-Path $workspace "gradlew.bat")
    ) "gradle.bat"
    $env:JAVA_HOME = Resolve-JavaHome
    $env:Path = "$env:JAVA_HOME\bin;$env:Path"
    Push-Location $workspace
    try {
        & $gradle ":app:assembleDebug"
        if ($LASTEXITCODE -ne 0) {
            throw "Gradle assembleDebug failed with exit code $LASTEXITCODE."
        }
    } finally {
        Pop-Location
    }
}

$apkPath = Resolve-Path -LiteralPath (Join-Path $workspace $Apk)
$targetDevice = Resolve-TargetDevice $Device $adb
$installArgs = @("-s", $targetDevice, "install", "-r")
if ($AllowDowngrade) {
    $installArgs += "-d"
}
$installArgs += $apkPath.Path

Write-Host "Installing $($apkPath.Path) on $targetDevice"
& $adb @installArgs
if ($LASTEXITCODE -ne 0) {
    throw "adb install failed with exit code $LASTEXITCODE."
}

Write-Host "Installed com.ibscare.android without clearing app data."
