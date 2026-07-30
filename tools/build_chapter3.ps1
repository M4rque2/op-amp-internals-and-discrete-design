param()

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
$chapter = Join-Path $workspace "src\chapter-03"
$sections = Join-Path $chapter "source-sections"
$output = Join-Path $chapter "chapter-03.md"
$cropScript = Join-Path $PSScriptRoot "crop_chapter3_assets.py"

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
if ($sourceFiles.Count -ne 4) {
    throw "Expected 4 source sections, found $($sourceFiles.Count)."
}

$parts = foreach ($sourceFile in $sourceFiles) {
    Get-Content -LiteralPath $sourceFile.FullName -Raw -Encoding UTF8
}

$combined = ($parts -join "`r`n`r`n").Replace(
    "](../images/",
    "](images/"
)

Set-Content -LiteralPath $output -Value $combined -Encoding UTF8

& $python $cropScript
if ($LASTEXITCODE -ne 0) {
    throw "Chapter 3 asset cropping failed with exit code $LASTEXITCODE."
}

Write-Output "Built $output"
