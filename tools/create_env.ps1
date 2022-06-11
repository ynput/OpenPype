<#
.SYNOPSIS
  Helper script create virtual environment using Poetry.

.DESCRIPTION
  This script will detect Python installation, create venv with Poetry
  and install all necessary packages from `poetry.lock` or `pyproject.toml`
  needed by OpenPype to be included during application freeze on Windows.

.EXAMPLE

PS> .\create_env.ps1

.EXAMPLE

Print verbose information from Poetry:
PS> .\create_env.ps1 --verbose

#>

$arguments=$ARGS
$poetry_verbosity=""
if($arguments -eq "--verbose") {
    $poetry_verbosity="-vvv"
}

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


function Install-Poetry() {
    Write-Host ">>> " -NoNewline -ForegroundColor Green
    Write-Host "Installing Poetry ... "
    $python = "python"
    if (Get-Command "pyenv" -ErrorAction SilentlyContinue) {
        if (-not (Test-Path -PathType Leaf -Path "$($openpype_root)\.python-version")) {
            $result = & pyenv global
            if ($result -eq "no global version configured") {
                Write-Host "!!! " -NoNewline -ForegroundColor Red
                Write-Host "Using pyenv but having no local or global version of Python set."
                Exit-WithCode 1
            }
        }
        $python = & pyenv which python
        
    }

    $env:POETRY_HOME="$openpype_root\.poetry"
    (Invoke-WebRequest -Uri https://install.python-poetry.org/ -UseBasicParsing).Content | & $($python) -
}


function Test-Python() {
    Write-Host ">>> " -NoNewline -ForegroundColor green
    Write-Host "Detecting host Python ... " -NoNewline
    $python = "python"
    if (Get-Command "pyenv" -ErrorAction SilentlyContinue) {
        $pyenv_python = & pyenv which python
        if (Test-Path -PathType Leaf -Path "$($pyenv_python)") {
            $python = $pyenv_python
        }
    }
    if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
        Write-Host "!!! Python not detected" -ForegroundColor red
        Set-Location -Path $current_dir
        Exit-WithCode 1
    }
    $version_command = @'
import sys
print('{0}.{1}'.format(sys.version_info[0], sys.version_info[1]))
'@

    $p = & $python -c $version_command
    $env:PYTHON_VERSION = $p
    $m = $p -match '(\d+)\.(\d+)'
    if(-not $m) {
      Write-Host "!!! Cannot determine version" -ForegroundColor red
      Set-Location -Path $current_dir
      Exit-WithCode 1
    }
    # We are supporting python 3.7 only
    if (($matches[1] -lt 3) -or ($matches[2] -lt 7)) {
      Write-Host "FAILED Version [ $p ] is old and unsupported" -ForegroundColor red
      Set-Location -Path $current_dir
      Exit-WithCode 1
    } elseif (($matches[1] -eq 3) -and ($matches[2] -gt 7)) {
        Write-Host "WARNING Version [ $p ] is unsupported, use at your own risk." -ForegroundColor yellow
        Write-Host "*** " -NoNewline -ForegroundColor yellow
        Write-Host "OpenPype supports only Python 3.7" -ForegroundColor white
    } else {
        Write-Host "OK [ $p ]" -ForegroundColor green
    }
}

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

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
if (-not (Test-Path 'env:_INSIDE_OPENPYPE_TOOL')) {
    Write-Host $art -ForegroundColor DarkGreen
}

# Enable if PS 7.x is needed.
# Show-PSWarning

$version_file = Get-Content -Path "$($openpype_root)\openpype\version.py"
$result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+.*)"')
$openpype_version = $result[0].Groups['version'].Value
if (-not $openpype_version) {
  Write-Host "!!! " -ForegroundColor yellow -NoNewline
  Write-Host "Cannot determine OpenPype version."
  Set-Location -Path $current_dir
  Exit-WithCode 1
}
Write-Host ">>> " -NoNewline -ForegroundColor Green
Write-Host "Found OpenPype version " -NoNewline
Write-Host "[ $($openpype_version) ]" -ForegroundColor Green

Test-Python

Write-Host ">>> " -NoNewline -ForegroundColor Green
Write-Host "Reading Poetry ... " -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Host "NOT FOUND" -ForegroundColor Yellow
    Install-Poetry
    Write-Host "INSTALLED" -ForegroundColor Cyan
} else {
    Write-Host "OK" -ForegroundColor Green
}

if (-not (Test-Path -PathType Leaf -Path "$($openpype_root)\poetry.lock")) {
    Write-Host ">>> " -NoNewline -ForegroundColor green
    Write-Host "Installing virtual environment and creating lock."
} else {
    Write-Host ">>> " -NoNewline -ForegroundColor green
    Write-Host "Installing virtual environment from lock."
}
& "$env:POETRY_HOME\bin\poetry" install --no-root $poetry_verbosity --ansi
if ($LASTEXITCODE -ne 0) {
    Write-Host "!!! " -ForegroundColor yellow -NoNewline
    Write-Host "Poetry command failed."
    Set-Location -Path $current_dir
    Exit-WithCode 1
}
Set-Location -Path $current_dir
Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Virtual environment created."
