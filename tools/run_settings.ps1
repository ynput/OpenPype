<#
.SYNOPSIS
  Helper script to OpenPype Settings UI

.DESCRIPTION
  This script will run OpenPype and open Settings UI.

.EXAMPLE

PS> .\run_settings.ps1

#>

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

# Install PSWriteColor to support colorized output to terminal
$env:PSModulePath = $env:PSModulePath + ";$($openpype_root)\vendor\powershell"

$env:_INSIDE_OPENPYPE_TOOL = "1"

# make sure Poetry is in PATH
if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$openpype_root\.poetry"
}
$env:PATH = "$($env:PATH);$($env:POETRY_HOME)\bin"

Set-Location -Path $openpype_root

Write-Color -Text ">>> ", "Reading Poetry ... " -Color Green, Gray -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Color -Text "NOT FOUND" -Color Yellow
    Install-Poetry
    Write-Color -Text "INSTALLED" -Color Cyan
} else {
    Write-Color -Text "OK" -Color Green
}

& "$env:POETRY_HOME\bin\poetry" run python "$($openpype_root)\start.py" settings --dev
Set-Location -Path $current_dir