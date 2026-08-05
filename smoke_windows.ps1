param(
    [string]$Executable = "dist\ChzzkClipMomentCatcher\ChzzkClipMomentCatcher.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Executable)) {
    throw "Packaged executable not found: $Executable"
}

$env:QT_QPA_PLATFORM = "offscreen"
$process = Start-Process -FilePath $Executable -PassThru

try {
    Start-Sleep -Seconds 5
    $process.Refresh()
    if ($process.HasExited) {
        throw "Packaged app exited during smoke test with code $($process.ExitCode)."
    }
}
finally {
    $process.Refresh()
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
}

Write-Host "Packaged app passed the smoke test."
