param(
  [Parameter(Mandatory = $false)]
  [string] $Path,

  [Parameter(Mandatory = $false)]
  [int] $Tail = 0
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if (-not $Path) {
  $sessionsRoot = Join-Path $env:USERPROFILE '.codex\sessions'
  $Path = Get-ChildItem -LiteralPath $sessionsRoot -Recurse -File -Filter 'rollout-*.jsonl' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
}

if (-not (Test-Path -LiteralPath $Path)) {
  throw "Session log not found: $Path"
}

$lines = if ($Tail -gt 0) {
  Get-Content -LiteralPath $Path -Tail $Tail
} else {
  Get-Content -LiteralPath $Path
}

$previous = $null
$rows = foreach ($line in $lines) {
  try {
    $event = $line | ConvertFrom-Json
  } catch {
    continue
  }

  if ($event.payload.type -ne 'token_count') {
    continue
  }

  $usage = $event.payload.info.total_token_usage
  $row = [pscustomobject]@{
    time = ([datetime] $event.timestamp).ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss')
    input = [int] $usage.input_tokens
    cached = [int] $usage.cached_input_tokens
    uncached_input = [int] ($usage.input_tokens - $usage.cached_input_tokens)
    output = [int] $usage.output_tokens
    reasoning = [int] $usage.reasoning_output_tokens
    total = [int] $usage.total_tokens
    delta_total = if ($previous) { [int] ($usage.total_tokens - $previous.total) } else { [int] $usage.total_tokens }
    delta_input = if ($previous) { [int] ($usage.input_tokens - $previous.input) } else { [int] $usage.input_tokens }
    delta_cached = if ($previous) { [int] ($usage.cached_input_tokens - $previous.cached) } else { [int] $usage.cached_input_tokens }
    delta_output = if ($previous) { [int] ($usage.output_tokens - $previous.output) } else { [int] $usage.output_tokens }
  }

  $previous = [pscustomobject]@{
    input = [int] $usage.input_tokens
    cached = [int] $usage.cached_input_tokens
    output = [int] $usage.output_tokens
    total = [int] $usage.total_tokens
  }

  $row
}

$rows | Format-Table -AutoSize
