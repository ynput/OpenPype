<#
.SYNOPSIS
  Helper script Pype Tray.

.DESCRIPTION


.EXAMPLE

PS> .\run_tray.ps1

#>
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pype_root = (Get-Item $script_dir).parent.FullName

& "$($pype_root)\venv\Scripts\Activate.ps1"

python "$($pype_root)\start.py" tray --debug
deactivate
