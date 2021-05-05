<#
.SYNOPSIS
  Helper script create distributable OpenPype zip.

.DESCRIPTION
  This script will detect Python installation and run OpenPype to create
  zip. It needs mongodb running. I will create zip from current source code
  version and copy it top `%LOCALAPPDATA%/pypeclub/pype` if `--path` or `-p`
  argument is not used.

.EXAMPLE

PS> .\create_zip.ps1

#>

function Exit-WithCode($exitcode) {
   # Only exit this host process if it's a child of another PowerShell parent process...
   $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
   $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
   if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }

   exit $exitcode
}


function Show-PSWarning() {
    if ($PSVersionTable.PSVersion.Major -lt 7) {
        Write-Host "!!! " -NoNewline -ForegroundColor Red
        Write-Host "You are using old version of PowerShell. $($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor)"
        Write-Host "Please update to at least 7.0 - " -NoNewline -ForegroundColor Gray
        Write-Host "https://github.com/PowerShell/PowerShell/releases" -ForegroundColor White
        Exit-WithCode 1
    }
}

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

$art = @"

▒█▀▀▀█ █▀▀█ █▀▀ █▀▀▄ ▒█▀▀█ █░░█ █▀▀█ █▀▀ ▀█▀ ▀█▀ ▀█▀
▒█░░▒█ █░░█ █▀▀ █░░█ ▒█▄▄█ █▄▄█ █░░█ █▀▀ ▒█░ ▒█░ ▒█░
▒█▄▄▄█ █▀▀▀ ▀▀▀ ▀░░▀ ▒█░░░ ▄▄▄█ █▀▀▀ ▀▀▀ ▄█▄ ▄█▄ ▄█▄
            .---= [ by Pype Club ] =---.
                 https://openpype.io

"@

Write-Host $art -ForegroundColor DarkGreen

# Enable if PS 7.x is needed.
# Show-PSWarning

$version_file = Get-Content -Path "$($openpype_root)\openpype\version.py"
$result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+.*)"')
$openpype_version = $result[0].Groups['version'].Value
if (-not $openpype_version) {
  Write-Host "!!! " -ForegroundColor yellow -NoNewline
  Write-Host "Cannot determine OpenPype version."
  Exit-WithCode 1
}

Write-Host ">>> " -NoNewline -ForegroundColor Green
Write-Host "Reading Poetry ... " -NoNewline
if (-not (Test-Path -PathType Container -Path "$openpype_root\.poetry\bin")) {
    Write-Host "NOT FOUND" -ForegroundColor Yellow
    Write-Host "*** " -NoNewline -ForegroundColor Yellow
    Write-Host "We need to install Poetry create virtual env first ..."
    & "$openpype_root\tools\create_env.ps1"
} else {
    Write-Host "OK" -ForegroundColor Green
}

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Cleaning cache files ... " -NoNewline
Get-ChildItem $openpype_root -Filter "*.pyc" -Force -Recurse | Remove-Item -Force
Get-ChildItem $openpype_root -Filter "*.pyo" -Force -Recurse | Remove-Item -Force
Get-ChildItem $openpype_root -Filter "__pycache__" -Force -Recurse | Remove-Item -Force -Recurse
Write-Host "OK" -ForegroundColor green

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Generating zip from current sources ..."
$env:PYTHONPATH="$($openpype_root);$($env:PYTHONPATH)"
$env:OPENPYPE_ROOT="$($openpype_root)"
& poetry run python "$($openpype_root)\tools\create_zip.py" $ARGS
Set-Location -Path $current_dir
