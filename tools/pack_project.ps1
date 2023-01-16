<#
.SYNOPSIS
  Helper script OpenPype Packing project.

.DESCRIPTION
  Once you are happy with the project and want to preserve it for future work, just change the project name on line 38 and copy the file into .\OpenPype\tools. Then use the cmd form .EXAMPLE

.EXAMPLE

PS> .\tools\run_pack_project.ps1

#>
$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

$env:_INSIDE_OPENPYPE_TOOL = "1"

# make sure Poetry is in PATH
if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$openpype_root\.poetry"
}
$env:PATH = "$($env:PATH);$($env:POETRY_HOME)\bin"

Set-Location -Path $openpype_root

Write-Host ">>> " -NoNewline -ForegroundColor Green
Write-Host "Reading Poetry ... " -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Host "NOT FOUND" -ForegroundColor Yellow
    Write-Host "*** " -NoNewline -ForegroundColor Yellow
    Write-Host "We need to install Poetry create virtual env first ..."
    & "$openpype_root\tools\create_env.ps1"
} else {
    Write-Host "OK" -ForegroundColor Green
}

& "$($env:POETRY_HOME)\bin\poetry" run python "$($openpype_root)\start.py" pack-project --project $ARGS
Set-Location -Path $current_dir