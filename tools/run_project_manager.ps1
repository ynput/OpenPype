<#
.SYNOPSIS
  Helper script to run Project Manager.

.DESCRIPTION


.EXAMPLE

PS> .\run_project_manager.ps1

#>
$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName
Set-Location -Path $openpype_root
& poetry run python "$($openpype_root)\start.py" projectmanager
Set-Location -Path $current_dir
