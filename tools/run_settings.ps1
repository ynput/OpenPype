<#
.SYNOPSIS
  Helper script to Pype Settings UI

.DESCRIPTION
  This script will run Pype and open Settings UI.

.EXAMPLE

PS> .\run_settings.ps1

#>

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pype_root = (Get-Item $script_dir).parent.FullName
Set-Location -Path $pype_root
& poetry run python "$($pype_root)\start.py" settings --dev
Set-Location -Path $current_dir