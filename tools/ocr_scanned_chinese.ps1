param(
    [Parameter(Mandatory = $true)]
    [string]$InputDirectory,

    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,

    [string]$LanguageTag = "zh-Hans-CN"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Runtime.WindowsRuntime
[void][Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStreamWithContentType, Windows.Storage, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
[void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

function Wait-WinRtOperation {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Operation,

        [Parameter(Mandatory = $true)]
        [Type]$ResultType
    )

    $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq "AsTask" -and
            $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1
        } |
        Select-Object -First 1

    $task = $asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}

$resolvedInput = (Resolve-Path -LiteralPath $InputDirectory).Path
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$resolvedOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path

$language = [Windows.Globalization.Language]::new($LanguageTag)
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if ($null -eq $engine) {
    throw "No Windows OCR engine is installed for language '$LanguageTag'."
}

$images = Get-ChildItem -LiteralPath $resolvedInput -Filter "*.png" |
    Sort-Object Name

foreach ($image in $images) {
    $storageFile = Wait-WinRtOperation `
        ([Windows.Storage.StorageFile]::GetFileFromPathAsync($image.FullName)) `
        ([Windows.Storage.StorageFile])
    $stream = Wait-WinRtOperation `
        ($storageFile.OpenReadAsync()) `
        ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
    $decoder = Wait-WinRtOperation `
        ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) `
        ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Wait-WinRtOperation `
        ($decoder.GetSoftwareBitmapAsync()) `
        ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Wait-WinRtOperation `
        ($engine.RecognizeAsync($bitmap)) `
        ([Windows.Media.Ocr.OcrResult])

    $lines = foreach ($line in $result.Lines) {
        ($line.Words.Text -join "")
    }

    $outputPath = Join-Path $resolvedOutput ($image.BaseName + ".txt")
    Set-Content -LiteralPath $outputPath -Value $lines -Encoding utf8
    $stream.Dispose()
    $bitmap.Dispose()

    Write-Output "$($image.Name) -> $(Split-Path -Leaf $outputPath)"
}
