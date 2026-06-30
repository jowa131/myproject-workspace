param(
  [Parameter(Mandatory = $false)]
  [string] $Path,

  [Parameter(Mandatory = $false)]
  [int] $Tail = 0,

  [Parameter(Mandatory = $false)]
  [string] $Date,

  [Parameter(Mandatory = $false)]
  [switch] $Json,

  [Parameter(Mandatory = $false)]
  [switch] $SummaryOnly
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function EmptyUsage {
  [pscustomobject]@{
    input = [int64] 0
    cached = [int64] 0
    output = [int64] 0
    reasoning = [int64] 0
    total = [int64] 0
  }
}

function UsageFromEvent($event) {
  $usage = $event.payload.info.total_token_usage
  [pscustomobject]@{
    input = [int64] $usage.input_tokens
    cached = [int64] $usage.cached_input_tokens
    output = [int64] $usage.output_tokens
    reasoning = [int64] $usage.reasoning_output_tokens
    total = [int64] $usage.total_tokens
  }
}

function UsageDelta($current, $previous) {
  [pscustomobject]@{
    input = [int64] ($current.input - $previous.input)
    cached = [int64] ($current.cached - $previous.cached)
    output = [int64] ($current.output - $previous.output)
    reasoning = [int64] ($current.reasoning - $previous.reasoning)
    total = [int64] ($current.total - $previous.total)
  }
}

function SessionFiles($targetPath) {
  if ($targetPath) {
    if (-not (Test-Path -LiteralPath $targetPath)) {
      throw "Session log not found: $targetPath"
    }

    $item = Get-Item -LiteralPath $targetPath
    if ($item.PSIsContainer) {
      return Get-ChildItem -LiteralPath $item.FullName -Recurse -File -Filter 'rollout-*.jsonl' |
        Sort-Object FullName
    }

    return @($item)
  }

  $sessionsRoot = Join-Path $env:USERPROFILE '.codex\sessions'
  return Get-ChildItem -LiteralPath $sessionsRoot -Recurse -File -Filter 'rollout-*.jsonl' |
    Sort-Object FullName
}

function TokenEvents($file, $tailCount) {
  $lines = if ($tailCount -gt 0) {
    Get-Content -LiteralPath $file.FullName -Tail $tailCount
  } else {
    Get-Content -LiteralPath $file.FullName
  }

  foreach ($line in $lines) {
    try {
      $event = $line | ConvertFrom-Json
    } catch {
      continue
    }

    if ($event.payload.type -ne 'token_count') {
      continue
    }

    $event
  }
}

function DailySummary($files, $dateText) {
  $targetDate = [datetime]::ParseExact($dateText, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture).Date
  $nextDate = $targetDate.AddDays(1)
  $total = EmptyUsage
  $sessions = @()
  $eventCount = 0

  foreach ($file in $files) {
    if ($file.LastWriteTime -lt $targetDate) {
      continue
    }

    $baseline = EmptyUsage
    $lastInWindow = $null
    $sessionEventCount = 0

    foreach ($event in TokenEvents $file 0) {
      $localTime = ([datetime] $event.timestamp).ToLocalTime()
      $usage = UsageFromEvent $event

      if ($localTime -lt $targetDate) {
        $baseline = $usage
        continue
      }

      if ($localTime -ge $nextDate) {
        break
      }

      $lastInWindow = $usage
      $sessionEventCount += 1
    }

    if (-not $lastInWindow) {
      continue
    }

    $delta = UsageDelta $lastInWindow $baseline
    $eventCount += $sessionEventCount
    $total.input += $delta.input
    $total.cached += $delta.cached
    $total.output += $delta.output
    $total.reasoning += $delta.reasoning
    $total.total += $delta.total

    $sessions += [pscustomobject]@{
      path = $file.FullName
      eventCount = $sessionEventCount
      inputTokens = $delta.input
      cachedInputTokens = $delta.cached
      uncachedInputTokens = [int64] ($delta.input - $delta.cached)
      outputTokens = $delta.output
      reasoningOutputTokens = $delta.reasoning
      totalTokens = $delta.total
    }
  }

  $summary = [ordered]@{
    date = $dateText
    timezone = [TimeZoneInfo]::Local.Id
    source = 'codex session token_count'
    sessionCount = $sessions.Count
    eventCount = $eventCount
    inputTokens = $total.input
    cachedInputTokens = $total.cached
    uncachedInputTokens = [int64] ($total.input - $total.cached)
    outputTokens = $total.output
    reasoningOutputTokens = $total.reasoning
    totalTokens = $total.total
  }

  if (-not $SummaryOnly) {
    $summary.sessions = $sessions
  }

  [pscustomobject] $summary
}

if ($Date) {
  $summary = DailySummary (SessionFiles $Path) $Date
  if ($Json) {
    $summary | ConvertTo-Json -Depth 6
  } else {
    $summary
  }
  return
}

$files = SessionFiles $Path
$file = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$previous = $null
$rows = foreach ($event in TokenEvents $file $Tail) {
  $usage = UsageFromEvent $event
  $row = [pscustomobject]@{
    time = ([datetime] $event.timestamp).ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss')
    input = $usage.input
    cached = $usage.cached
    uncached_input = [int64] ($usage.input - $usage.cached)
    output = $usage.output
    reasoning = $usage.reasoning
    total = $usage.total
    delta_total = if ($previous) { [int64] ($usage.total - $previous.total) } else { $usage.total }
    delta_input = if ($previous) { [int64] ($usage.input - $previous.input) } else { $usage.input }
    delta_cached = if ($previous) { [int64] ($usage.cached - $previous.cached) } else { $usage.cached }
    delta_output = if ($previous) { [int64] ($usage.output - $previous.output) } else { $usage.output }
  }

  $previous = $usage
  $row
}

if ($Json) {
  $rows | ConvertTo-Json -Depth 4
} else {
  $rows
}
