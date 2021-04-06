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
Set-Location -Path $openpype_root
& poetry run python "$($openpype_root)\start.py" settings --dev
Set-Location -Path $current_dir