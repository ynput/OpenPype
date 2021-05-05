<#
.SYNOPSIS
  Download and extract third-party dependencies for OpenPype.

.DESCRIPTION
  This will download third-party dependencies specified in pyproject.toml
  and extract them to vendor/bin folder.

.EXAMPLE

PS> .\fetch_thirdparty_libs.ps1

#>
$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

$env:_INSIDE_OPENPYPE_TOOL = "1"

# make sure Poetry is in PATH
if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$openpype_root\.poetry"
}
$env:PATH = "$($env:PATH);$($env:POETRY_HOME)\bin"

Set-Location -Path $openpype_root


Write-Host ">>> " -NoNewline -ForegroundColor Green
Write-Host "Reading Poetry ... " -NoNewline
if (-not (Test-Path -PathType Container -Path "$openpype_root\.poetry\bin")) {
    Write-Host "NOT FOUND" -ForegroundColor Yellow
    Write-Host "*** " -NoNewline -ForegroundColor Yellow
    Write-Host "We need to install Poetry create virtual env first ..."
    & "$openpype_root\tools\create_env.ps1"
} else {
    Write-Host "OK" -ForegroundColor Green
}

& poetry run python "$($openpype_root)\tools\fetch_thirdparty_libs.py"
Set-Location -Path $current_dir
