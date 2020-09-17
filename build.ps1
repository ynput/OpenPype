<#
.SYNOPSIS
  Helper script to build Pype.

.DESCRIPTION
  This script will detect Python installation, create venv and install
  all necessary packages from `requirements.txt` needed by Pype to be
  included during application freeze on Windows.

.EXAMPLE

PS> .\build.ps1

#>


function Exit-WithCode($exitcode) {
   # Only exit this host process if it's a child of another PowerShell parent process...
   $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
   $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
   if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }

   exit $exitcode
}

$art = @'


     ____________
   / \      __   \
   \  \     \/_\  \
    \  \     _____/ ______
     \  \    \___// \     \
      \  \____\   \  \_____\
       \/_____/    \/______/  PYPE Club .

'@

Write-Host $art -ForegroundColor DarkGreen

$version_file = Get-Content -Path ".\pype\version.py"
$result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+)"')
$pype_version = $result[0].Groups['version'].Value
if (-not $pype_version) {
  Write-Host "!!! " -ForegroundColor yellow -NoNewline
  Write-Host "Cannot determine Pype version."
  Exit-WithCode 1
}

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Building Pype [ " -NoNewline -ForegroundColor white
Write-host $pype_version  -NoNewline -ForegroundColor green
Write-Host " ]..." -ForegroundColor white

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Detecting host Python ... " -NoNewline
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "!!! Python not detected" -ForegroundColor red
    Exit-WithCode 1
}
$version_command = @'
import sys
print('{0}.{1}'.format(sys.version_info[0], sys.version_info[1]))
'@

$p = & python -c $version_command
$env:PYTHON_VERSION = $p
$m = $p -match '(\d+)\.(\d+)'
if(-not $m) {
  Write-Host "!!! Cannot determine version" -ForegroundColor red
  Exit-WithCode 1
}
# We are supporting python 3.6 and up
if(($matches[1] -lt 3) -or ($matches[2] -lt 7)) {
  Write-Host "FAILED Version [ $p ] is old and unsupported" -ForegroundColor red
  Exit-WithCode 1
}
Write-Host "OK [ $p ]" -ForegroundColor green
Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Creating virtual env ..."
& python -m venv venv
Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Entering venv ..."
try {
  . (".\venv\Scripts\Activate.ps1")
}
catch {
  Write-Host "!!! Failed to activate" -ForegroundColor red
  Write-Host $_.Exception.Message
  Exit-WithCode 1
}
Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Installing packages to new venv ..."
& pip install -r .\requirements.txt

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Cleaning cache files ... " -NoNewline
Get-ChildItem . -Filter "*.pyc" -Force -Recurse | Remove-Item -Force
Get-ChildItem . -Filter "__pycache__" -Force -Recurse | Remove-Item -Force -Recurse
Write-Host "OK" -ForegroundColor green

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Building Pype ..."
& python setup.py build
deactivate
