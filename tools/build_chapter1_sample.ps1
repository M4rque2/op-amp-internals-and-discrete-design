param()

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
$chapter = Join-Path $workspace "src\chapter-01"
$sections = Join-Path $chapter "source-sections"
$output = Join-Path $chapter "chapter-01.md"
$cropScript = Join-Path $PSScriptRoot "crop_chapter1_figures.py"

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

# Windows PowerShell 5.1's default input encoding is locale-dependent.
Set-Content -LiteralPath $output -Value $combined -Encoding UTF8

& $python $cropScript
if ($LASTEXITCODE -ne 0) {
    throw "Figure cropping failed with exit code $LASTEXITCODE."
}

Write-Output "Built $output"

