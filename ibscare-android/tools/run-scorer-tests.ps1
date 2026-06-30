$ErrorActionPreference = "Stop"

$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$buildDir = Join-Path $rootDir "build\scorer-cli-test"
if (Test-Path $buildDir) {
    Remove-Item -LiteralPath $buildDir -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $buildDir "classes") | Out-Null

$jdkHome = $env:JDK_HOME
if ([string]::IsNullOrWhiteSpace($jdkHome)) {
    $candidates = @(
        "C:\Program Files\Android\Android Studio\jbr",
        "$env:USERPROFILE\.antigravity\extensions\redhat.java-1.54.0-win32-x64\jre\21.0.10-win32-x86_64"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path (Join-Path $candidate "bin\javac.exe")) {
            $jdkHome = $candidate
            break
        }
    }
}

if ([string]::IsNullOrWhiteSpace($jdkHome)) {
    throw "No JDK with javac found. Set JDK_HOME."
}

$sourceRoots = @(
    "app\src\main\java\com\ibscare\android\session",
    "app\src\test\java"
)
$sources = foreach ($sourceRoot in $sourceRoots) {
    $path = Join-Path $rootDir $sourceRoot
    if (Test-Path $path) {
        Get-ChildItem -LiteralPath $path -Recurse -Filter "*.java" | Select-Object -ExpandProperty FullName
    }
}
$sources += Join-Path $rootDir "app\src\main\java\com\ibscare\android\ui\UiCopy.java"

& (Join-Path $jdkHome "bin\javac.exe") -encoding UTF-8 -d (Join-Path $buildDir "classes") @sources
& (Join-Path $jdkHome "bin\java.exe") -cp (Join-Path $buildDir "classes") com.ibscare.android.session.BowelSessionScorerCliTest
