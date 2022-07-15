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

# Install PSWriteColor to support colorized output to terminal
$env:PSModulePath = $env:PSModulePath + ";$($openpype_root)\vendor\powershell"

$env:_INSIDE_OPENPYPE_TOOL = "1"

if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$openpype_root\.poetry"
}

Set-Location -Path $openpype_root

Write-Color -Text ">>> ", "Reading Poetry ... " -Color Green, Gray -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Color -Text "NOT FOUND" -Color Yellow
    Write-Color -Text "*** ", "We need to install Poetry create virtual env first ..." -Color Yellow, Gray
    & "$openpype_root\tools\create_env.ps1"
} else {
    Write-Color -Text "OK" -Color Green
}
$startTime = [int][double]::Parse((Get-Date -UFormat %s))
& "$($env:POETRY_HOME)\bin\poetry" run python "$($openpype_root)\tools\fetch_thirdparty_libs.py"
$endTime = [int][double]::Parse((Get-Date -UFormat %s))
Set-Location -Path $current_dir
New-BurntToastNotification -AppLogo "$openpype_root/openpype/resources/icons/openpype_icon.png" -Text "OpenPype", "Dependencies downloaded", "All done in $($endTime - $startTime) secs."
