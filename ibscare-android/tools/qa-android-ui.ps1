param(
    [string]$Device = "emulator-5554",
    [string]$Apk = "app/build/outputs/apk/debug/app-debug.apk",
    [string]$EvidenceDir = ".codex-handoff/evidence"
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue) {
    $global:PSNativeCommandUseErrorActionPreference = $false
}

$workspace = Resolve-Path (Join-Path $PSScriptRoot "..")
$adb = "C:\Users\mymelodyPC\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$apkPath = Resolve-Path (Join-Path $workspace $Apk)
$evidencePath = Resolve-Path (Join-Path $workspace $EvidenceDir)
$pythonScript = Join-Path $evidencePath "android-ui-qa-helper.py"

@'
import re
import sys
import xml.etree.ElementTree as ET

TEXTS = {
    "confirm": "\ubc30\ubcc0 \uae30\ub85d \ud655\uc778\ud558\uae30",
    "sample": "\ud14c\uc2a4\ud2b8\uc6a9 \ud6c4\ubcf4 \uc810\uc218 \uacc4\uc0b0",
    "alert_title": "\ubc30\ubcc0 \uae30\ub85d\uc744 \ud655\uc778\ud560\uae4c\uc694?",
    "alert_confirm": "\uae30\ub85d \ud655\uc778\ud558\uae30",
    "alert_false_positive": "\ub625\uc2f8\ub294 \uc911\uc774 \uc544\ub2d8",
    "alert_later": "\ub098\uc911\uc5d0",
    "false_positive_recorded": "\ub625\uc2f8\ub294 \uc911\uc774 \uc544\ub2d8\uc73c\ub85c \uae30\ub85d\ub428",
    "save": "\uae30\ub85d \uc800\uc7a5",
    "saved": "\uc624\ub298 1\ud68c \uc800\uc7a5\ub428",
    "version": "\ubc84\uc804 0.1.9 (10)",
}

def iter_nodes(path):
    return ET.parse(path).getroot().iter("node")

def center(path, key):
    target = TEXTS[key]
    for node in iter_nodes(path):
        if node.attrib.get("text") != target:
            continue
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib["bounds"])
        if match is None:
            raise SystemExit(f"bad bounds for {key}")
        x1, y1, x2, y2 = [int(value) for value in match.groups()]
        print(f"{(x1 + x2) // 2} {(y1 + y2) // 2}")
        return
    raise SystemExit(f"missing node {key}")

def assert_after_confirm(path):
    edit_texts = [node.attrib.get("text", "") for node in iter_nodes(path) if node.attrib.get("class") == "android.widget.EditText"]
    if not edit_texts or re.fullmatch(r"\d{2}:\d{2}", edit_texts[0]) is None:
        raise SystemExit("Confirm did not prefill HH:mm time.")
    checked = [node for node in iter_nodes(path) if node.attrib.get("class") == "android.widget.CheckBox" and node.attrib.get("checked") == "true"]
    if checked:
        raise SystemExit("Confirm changed checkbox state.")
    saved = [node for node in iter_nodes(path) if TEXTS["saved"] in node.attrib.get("text", "")]
    if saved:
        raise SystemExit("Confirm auto-saved before explicit save.")
    print("AFTER_CONFIRM_PASS")

def assert_after_false_positive(path):
    recorded = [node for node in iter_nodes(path) if TEXTS["false_positive_recorded"] in node.attrib.get("text", "")]
    if not recorded:
        raise SystemExit("False-positive action did not update the proposal panel.")
    print("AFTER_FALSE_POSITIVE_PASS")

def assert_initial(path):
    version = [node for node in iter_nodes(path) if node.attrib.get("text") == TEXTS["version"]]
    if not version:
        raise SystemExit("Version label was not rendered.")
    print("INITIAL_VERSION_PASS")

def assert_alert(path):
    title = [node for node in iter_nodes(path) if node.attrib.get("text") == TEXTS["alert_title"]]
    confirm = [node for node in iter_nodes(path) if node.attrib.get("text") == TEXTS["alert_confirm"]]
    false_positive = [node for node in iter_nodes(path) if node.attrib.get("text") == TEXTS["alert_false_positive"]]
    later = [node for node in iter_nodes(path) if node.attrib.get("text") == TEXTS["alert_later"]]
    if not title or not confirm or not false_positive:
        raise SystemExit("Likely-session alert dialog was not rendered.")
    if later:
        raise SystemExit("Likely-session alert still contains the old later button.")
    print("LIKELY_SESSION_ALERT_PASS")

def assert_after_save(path):
    saved = [node for node in iter_nodes(path) if TEXTS["saved"] in node.attrib.get("text", "")]
    if not saved:
        raise SystemExit("Explicit save summary was not rendered.")
    print("AFTER_SAVE_PASS")

command = sys.argv[1]
if command == "center":
    center(sys.argv[2], sys.argv[3])
elif command == "after-confirm":
    assert_after_confirm(sys.argv[2])
elif command == "after-false-positive":
    assert_after_false_positive(sys.argv[2])
elif command == "after-save":
    assert_after_save(sys.argv[2])
elif command == "initial":
    assert_initial(sys.argv[2])
elif command == "alert":
    assert_alert(sys.argv[2])
else:
    raise SystemExit(f"unknown command {command}")
'@ | Set-Content -LiteralPath $pythonScript -Encoding ASCII

function Invoke-Adb {
    & $adb -s $Device @args
}

function Dump-Ui([string]$remote, [string]$local) {
    Invoke-Adb shell uiautomator dump $remote | Out-Host
    $localPath = Join-Path $evidencePath $local
    cmd /c "`"$adb`" -s $Device pull `"$remote`" `"$localPath`" >NUL 2>NUL"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to pull UI dump $remote"
    }
}

function Save-Screenshot([string]$local) {
    $path = Join-Path $evidencePath $local
    cmd /c "`"$adb`" -s $Device exec-out screencap -p > `"$path`""
}

function Get-Center([string]$xmlPath, [string]$key) {
    $output = python $pythonScript center $xmlPath $key
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to locate UI node $key"
    }
    $parts = $output.Trim().Split(" ")
    return @([int]$parts[0], [int]$parts[1])
}

function Assert-Ui([string]$Command, [string]$XmlPath) {
    python $pythonScript $Command $XmlPath
    if ($LASTEXITCODE -ne 0) {
        throw "UI assertion failed: $Command"
    }
}

function Prepare-App() {
    Invoke-Adb shell pm clear com.ibscare.android | Out-Host
    Invoke-Adb shell pm grant com.ibscare.android android.permission.POST_NOTIFICATIONS | Out-Host
    Invoke-Adb shell pm grant com.ibscare.android android.permission.ACCESS_FINE_LOCATION | Out-Host
    Invoke-Adb shell pm grant com.ibscare.android android.permission.ACCESS_COARSE_LOCATION | Out-Host
    Invoke-Adb shell settings put secure location_mode 3 | Out-Host
    Invoke-Adb emu geo fix 126.9780 37.5665 0 5 0.0 | Out-Host
    Invoke-Adb shell am start -n com.ibscare.android/.MainActivity | Out-Host
    Start-Sleep -Seconds 5
}

Invoke-Adb install -r $apkPath | Out-Host
Prepare-App
Dump-Ui "/sdcard/ibs-care-qa-initial.xml" "android-qa-initial.xml"
Save-Screenshot "android-qa-initial.png"

$initialXml = Join-Path $evidencePath "android-qa-initial.xml"
Assert-Ui "initial" $initialXml
$sample = Get-Center $initialXml "sample"
Invoke-Adb shell input tap $sample[0] $sample[1] | Out-Host
Start-Sleep -Seconds 10

Dump-Ui "/sdcard/ibs-care-qa-alert.xml" "android-qa-alert.xml"
$alertXml = Join-Path $evidencePath "android-qa-alert.xml"
Assert-Ui "alert" $alertXml
$alertFalsePositive = Get-Center $alertXml "alert_false_positive"
Invoke-Adb shell input tap $alertFalsePositive[0] $alertFalsePositive[1] | Out-Host
Start-Sleep -Seconds 2

Dump-Ui "/sdcard/ibs-care-qa-after-false-positive.xml" "android-qa-after-false-positive.xml"
$falsePositiveXml = Join-Path $evidencePath "android-qa-after-false-positive.xml"
Assert-Ui "after-false-positive" $falsePositiveXml

Prepare-App
Dump-Ui "/sdcard/ibs-care-qa-confirm-initial.xml" "android-qa-confirm-initial.xml"
$confirmInitialXml = Join-Path $evidencePath "android-qa-confirm-initial.xml"
$sample = Get-Center $confirmInitialXml "sample"
Invoke-Adb shell input tap $sample[0] $sample[1] | Out-Host
Start-Sleep -Seconds 10

Dump-Ui "/sdcard/ibs-care-qa-confirm-alert.xml" "android-qa-confirm-alert.xml"
$alertXml = Join-Path $evidencePath "android-qa-confirm-alert.xml"
Assert-Ui "alert" $alertXml
$alertConfirm = Get-Center $alertXml "alert_confirm"
Invoke-Adb shell input tap $alertConfirm[0] $alertConfirm[1] | Out-Host
Start-Sleep -Seconds 2

Dump-Ui "/sdcard/ibs-care-qa-after-confirm.xml" "android-qa-after-confirm.xml"
$confirmXml = Join-Path $evidencePath "android-qa-after-confirm.xml"
Assert-Ui "after-confirm" $confirmXml

Invoke-Adb shell input swipe 540 1980 540 1500 300 | Out-Host
Start-Sleep -Seconds 1
Dump-Ui "/sdcard/ibs-care-qa-before-save.xml" "android-qa-before-save.xml"
$confirmXml = Join-Path $evidencePath "android-qa-before-save.xml"
$save = Get-Center $confirmXml "save"
Invoke-Adb shell input tap $save[0] $save[1] | Out-Host
Start-Sleep -Seconds 2

Dump-Ui "/sdcard/ibs-care-qa-after-save.xml" "android-qa-after-save.xml"
Save-Screenshot "android-qa-after-save.png"
$saveXml = Join-Path $evidencePath "android-qa-after-save.xml"
python $pythonScript after-save $saveXml
if ($LASTEXITCODE -ne 0) {
    Invoke-Adb shell input tap $save[0] $save[1] | Out-Host
    Start-Sleep -Seconds 2
    Dump-Ui "/sdcard/ibs-care-qa-after-save.xml" "android-qa-after-save.xml"
    Save-Screenshot "android-qa-after-save.png"
    Assert-Ui "after-save" $saveXml
}

Write-Output "ANDROID_UI_QA_PASS"
