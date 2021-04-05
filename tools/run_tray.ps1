<#
.SYNOPSIS
  Helper script OpenPype Tray.

.DESCRIPTION


.EXAMPLE

PS> .\run_tray.ps1

#>
$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName
Set-Location -Path $openpype_root

& poetry run python "$($openpype_root)\start.py" tray --debug
Set-Location -Path $current_dir