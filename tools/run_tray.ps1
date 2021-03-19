<#
.SYNOPSIS
  Helper script Pype Tray.

.DESCRIPTION


.EXAMPLE

PS> .\run_tray.ps1

#>
$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pype_root = (Get-Item $script_dir).parent.FullName
Set-Location -Path $pype_root

& poetry run python "$($pype_root)\start.py" tray --debug
Set-Location -Path $current_dir