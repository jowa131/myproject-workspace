param(
    [string]$Root = "C:\MyProject"
)

$ErrorActionPreference = "Stop"

$generatedNames = @(
    "node_modules",
    ".next",
    "dist",
    ".astro",
    ".cache",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "__pycache__",
    "logs",
    "runs",
    "tokens",
    "secrets",
    "graphify-out"
)

function Get-RepoStatus {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath (Join-Path $Path ".git"))) {
        return
    }

    $short = @(git -C $Path status --short 2>$null)
    [pscustomobject]@{
        Project = Split-Path -Leaf $Path
        Path = $Path
        DirtyCount = $short.Count
        DirtyPreview = ($short | Select-Object -First 5) -join "; "
    }
}

function Get-GeneratedHit {
    param([string]$Path)

    foreach ($name in $generatedNames) {
        $candidate = Join-Path $Path $name
        if (Test-Path -LiteralPath $candidate) {
            [pscustomobject]@{
                Project = Split-Path -Leaf $Path
                Artifact = $name
                Path = $candidate
            }
        }
    }
}

$rootItem = Get-Item -LiteralPath $Root
$projectDirs = @(Get-ChildItem -LiteralPath $Root -Directory -Force | Where-Object {
    $_.Name -notin @(".git", ".agents")
})

"## Git repositories"
$repoStatuses = @()
$repoStatuses += @(Get-RepoStatus -Path $rootItem.FullName)
foreach ($dir in $projectDirs) {
    $repoStatuses += @(Get-RepoStatus -Path $dir.FullName)
}
$repoStatuses | Format-Table -AutoSize

""
"## Generated/local artifact directories"
$generatedHits = @()
foreach ($dir in @($rootItem) + $projectDirs) {
    $generatedHits += @(Get-GeneratedHit -Path $dir.FullName)
}
$generatedHits | Format-Table -AutoSize
