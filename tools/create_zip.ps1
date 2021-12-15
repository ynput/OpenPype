<#
.SYNOPSIS
  Helper script create distributable OpenPype zip.

.DESCRIPTION
  This script will detect Python installation and run OpenPype to create
  zip. It will create zip from current source code
  version and copy it top `%LOCALAPPDATA%/pypeclub/openpype` if `--path` or `-p`
  argument is not used.

.EXAMPLE

PS> .\create_zip.ps1

.EXAMPLE

To put generated zip to C:\OpenPype directory:
PS> .\create_zip.ps1 --path C:\OpenPype

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

if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$openpype_root\.poetry"
}

Set-Location -Path $openpype_root

$art = @"

             . .   ..     .    ..
        _oOOP3OPP3Op_. .
     .PPpo~.   ..   ~2p.  ..  ....  .  .
    .Ppo . .pPO3Op.. . O:. . . .
   .3Pp . oP3'. 'P33. . 4 ..   .  .   . .. .  .  .
  .~OP    3PO.  .Op3    : . ..  _____  _____  _____
  .P3O  . oP3oP3O3P' . . .   . /    /./    /./    /
   O3:.   O3p~ .       .:. . ./____/./____/ /____/
   'P .   3p3.  oP3~. ..P:. .  . ..  .   . .. .  .  .
  . ':  . Po'  .Opo'. .3O. .  o[ by Pype Club ]]]==- - - .  .
    . '_ ..  .    . _OP3..  .  .https://openpype.io.. .
         ~P3.OPPPO3OP~ . ..  .
           .  ' '. .  .. . . . ..  .

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
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Host "NOT FOUND" -ForegroundColor Yellow
    Write-Host "*** " -NoNewline -ForegroundColor Yellow
    Write-Host "We need to install Poetry create virtual env first ..."
    & "$openpype_root\tools\create_env.ps1"
} else {
    Write-Host "OK" -ForegroundColor Green
}

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Cleaning cache files ... " -NoNewline
Get-ChildItem $openpype_root -Filter "__pycache__" -Force -Recurse|  Where-Object {( $_.FullName -inotmatch '\\build\\' ) -and ( $_.FullName -inotmatch '\\.venv' )} | Remove-Item -Force -Recurse
Get-ChildItem $openpype_root -Filter "*.pyc" -Force -Recurse | Where-Object {( $_.FullName -inotmatch '\\build\\' ) -and ( $_.FullName -inotmatch '\.venv' )} | Remove-Item -Force
Get-ChildItem $openpype_root -Filter "*.pyo" -Force -Recurse | Where-Object {( $_.FullName -inotmatch '\\build\\' ) -and ( $_.FullName -inotmatch '\.venv' )} | Remove-Item -Force
Write-Host "OK" -ForegroundColor green

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Generating zip from current sources ..."
$env:PYTHONPATH="$($openpype_root);$($env:PYTHONPATH)"
$env:OPENPYPE_ROOT="$($openpype_root)"
& "$($env:POETRY_HOME)\bin\poetry" run python "$($openpype_root)\tools\create_zip.py" $ARGS
Set-Location -Path $current_dir
