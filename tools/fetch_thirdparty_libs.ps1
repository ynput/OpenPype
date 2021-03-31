<#
.SYNOPSIS
  Download and extract third-party dependencies for Pype.

.DESCRIPTION
  This will download third-party dependencies specified in pyproject.toml
  and extract them to vendor/bin folder.
 #>

.EXAMPLE

PS> .\fetch_thirdparty_libs.ps1

#>
$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pype_root = (Get-Item $script_dir).parent.FullName
Set-Location -Path $pype_root

& poetry run python "$($pype_root)\tools\fetch_thirdparty_libs.py"
Set-Location -Path $current_dir
