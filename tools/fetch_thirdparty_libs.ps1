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
$repo_root = (Get-Item $script_dir).parent.FullName

# Install PSWriteColor to support colorized output to terminal
$env:PSModulePath = $env:PSModulePath + ";$($repo_root)\tools\modules\powershell"

$env:_INSIDE_OPENPYPE_TOOL = "1"

if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$repo_root\.poetry"
}

Set-Location -Path $repo_root

Write-Color -Text ">>> ", "Reading Poetry ... " -Color Green, Gray -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Color -Text "NOT FOUND" -Color Yellow
    Write-Color -Text "*** ", "We need to install Poetry create virtual env first ..." -Color Yellow, Gray
    & "$repo_root\tools\create_env.ps1"
} else {
    Write-Color -Text "OK" -Color Green
}
$startTime = [int][double]::Parse((Get-Date -UFormat %s))
& "$($env:POETRY_HOME)\bin\poetry" run python "$($repo_root)\tools\fetch_thirdparty_libs.py"
$endTime = [int][double]::Parse((Get-Date -UFormat %s))
Set-Location -Path $current_dir
try
{
    New-BurntToastNotification -AppLogo "$repo_root/common/ayon_common/resources/AYON.png" -Text "OpenPype", "Dependencies downloaded", "All done in $( $endTime - $startTime ) secs."
} catch {}
