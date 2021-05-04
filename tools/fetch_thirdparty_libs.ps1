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
Set-Location -Path $openpype_root

& poetry run python "$($openpype_root)\tools\fetch_thirdparty_libs.py"
Set-Location -Path $current_dir
