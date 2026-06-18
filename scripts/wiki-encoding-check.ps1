param(
    [string]$Root = "C:\MyProject\wiki"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
$strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
$failed = $false

Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File |
    Sort-Object FullName |
    ForEach-Object {
        $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
        $relative = $_.FullName.Substring($resolvedRoot.Length).TrimStart("\")
        $head = ($bytes | Select-Object -First 4 | ForEach-Object { $_.ToString("X2") }) -join " "

        try {
            $text = $strictUtf8.GetString($bytes)
            $hasReplacement = $text.Contains([char]0xFFFD)
            $bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF

            if ($hasReplacement) {
                $failed = $true
                [pscustomobject]@{
                    Status = "WARN_REPLACEMENT_CHAR"
                    Bytes = $bytes.Length
                    BOM = $bom
                    Head = $head
                    Path = $relative
                }
            } else {
                [pscustomobject]@{
                    Status = "OK_UTF8"
                    Bytes = $bytes.Length
                    BOM = $bom
                    Head = $head
                    Path = $relative
                }
            }
        } catch {
            $failed = $true
            [pscustomobject]@{
                Status = "FAIL_INVALID_UTF8"
                Bytes = $bytes.Length
                BOM = $false
                Head = $head
                Path = $relative
            }
        }
    } | Format-Table -AutoSize

if ($failed) {
    exit 1
}
