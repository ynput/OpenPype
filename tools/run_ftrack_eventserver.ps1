<#
.SYNOPSIS
  Helper script to start OpenPype Ftrack EventServer without relying on built executables.

.DESCRIPTION


.EXAMPLE

PS> .\run_eventserver.ps1

#>
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

$env:_INSIDE_OPENPYPE_TOOL = "1"
$env:OPENPYPE_DEBUG = "1"
# $env:OPENPYPE_MONGO = "mongodb://127.0.0.1:27017"

# make sure Poetry is in PATH
if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$openpype_root\.poetry"
}
$env:PATH = "$($env:PATH);$($env:POETRY_HOME)\bin"

Set-Location -Path $openpype_root

Write-Host ">>> " -NoNewline -ForegroundColor Green
Write-Host "Reading Poetry ... " -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Host "NOT FOUND" -ForegroundColor Yellow
    Write-Host "*** " -NoNewline -ForegroundColor Yellow
    Write-Host "We need to install Poetry create virtual env first ..."
    & "$openpype_root\tools\create_env.ps1"
} else {
    Write-Host "OK" -ForegroundColor Green
}

& "$($env:POETRY_HOME)\bin\poetry" run python "$($openpype_root)\start.py" eventserver