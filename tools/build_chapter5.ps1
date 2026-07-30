param()

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
$chapter = Join-Path $workspace "src\chapter-05"
$sections = Join-Path $chapter "source-sections"
$output = Join-Path $chapter "chapter-05.md"
$cropScript = Join-Path $PSScriptRoot "crop_chapter5_assets.py"

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue |
    Select-Object -First 1
$bundledPython = Join-Path $env:USERPROFILE (
    ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)
if ($null -ne $pythonCommand) {
    $python = $pythonCommand.Source
} elseif (Test-Path -LiteralPath $bundledPython) {
    $python = $bundledPython
} else {
    throw "Python was not found on PATH or in the Codex bundled runtime."
}

$sourceFiles = Get-ChildItem -LiteralPath $sections -Filter "*.md" |
    Sort-Object Name
if ($sourceFiles.Count -ne 5) {
    throw "Expected 5 source sections, found $($sourceFiles.Count)."
}

$parts = foreach ($sourceFile in $sourceFiles) {
    Get-Content -LiteralPath $sourceFile.FullName -Raw -Encoding UTF8
}

$combined = ($parts -join "`r`n`r`n").Replace(
    "](../images/",
    "](images/"
)

[System.IO.File]::WriteAllText(
    $output,
    $combined,
    [System.Text.UTF8Encoding]::new($false)
)

& $python $cropScript
if ($LASTEXITCODE -ne 0) {
    throw "Chapter 5 asset cropping failed with exit code $LASTEXITCODE."
}

Write-Output "Built $output"
