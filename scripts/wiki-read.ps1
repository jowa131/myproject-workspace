param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [int]$StartLine = 1,

    [int]$First = 80,

    [string]$Pattern
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if ($First -lt 1) {
    throw "First must be greater than 0."
}

$resolvedPath = (Resolve-Path -LiteralPath $Path).Path
$wikiRoot = (Resolve-Path -LiteralPath "C:\MyProject\wiki").Path

if (-not $resolvedPath.StartsWith($wikiRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "wiki-read.ps1 only reads files under $wikiRoot."
}

$bytes = [System.IO.File]::ReadAllBytes($resolvedPath)
$strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
$text = $strictUtf8.GetString($bytes)

if ($text.Contains([char]0xFFFD)) {
    throw "Decoded text contains the Unicode replacement character. Run scripts\wiki-encoding-check.ps1."
}

$lines = $text -split "`r`n|`n|`r"

if ($Pattern) {
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i] -match $Pattern) {
            "{0}: {1}" -f ($i + 1), $lines[$i]
        }
    }
    return
}

if ($StartLine -lt 1) {
    throw "StartLine must be greater than 0."
}

$startIndex = $StartLine - 1
$endIndex = [Math]::Min($startIndex + $First - 1, $lines.Length - 1)

if ($startIndex -gt $endIndex) {
    return
}

for ($i = $startIndex; $i -le $endIndex; $i++) {
    "{0}: {1}" -f ($i + 1), $lines[$i]
}
