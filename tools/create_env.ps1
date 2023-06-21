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
$poetry_verbosity=$null
if($arguments -eq "--verbose") {
    $poetry_verbosity="-vvv"
}

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$repo_root = (Get-Item $script_dir).parent.FullName

& git submodule update --init --recursive
# Install PSWriteColor to support colorized output to terminal
$env:PSModulePath = $env:PSModulePath + ";$($repo_root)\tools\modules\powershell"


function Exit-WithCode($exitcode) {
   # Only exit this host process if it's a child of another PowerShell parent process...
   $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
   $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
   if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }

   exit $exitcode
}


function Show-PSWarning() {
    if ($PSVersionTable.PSVersion.Major -lt 7) {
        Write-Color -Text "!!! ", "You are using old version of PowerShell - ",  "$($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor)" -Color Red, Yellow, White
        Write-Color -Text "    Please update to at least 7.0 - ", "https://github.com/PowerShell/PowerShell/releases" -Color Yellow, White
        Exit-WithCode 1
    }
}


function Install-Poetry() {
    Write-Color -Text ">>> ", "Installing Poetry ... " -Color Green, Gray
    $python = "python"
    if (Get-Command "pyenv" -ErrorAction SilentlyContinue) {
        if (-not (Test-Path -PathType Leaf -Path "$($repo_root)\.python-version")) {
            $result = & pyenv global
            if ($result -eq "no global version configured") {
                Write-Color -Text "!!! ", "Using pyenv but having no local or global version of Python set." -Color Red, Yellow
                Exit-WithCode 1
            }
        }
        $python = & pyenv which python

    }

    $env:POETRY_HOME="$repo_root\.poetry"
    $env:POETRY_VERSION="1.3.2"
    (Invoke-WebRequest -Uri https://install.python-poetry.org/ -UseBasicParsing).Content | & $($python) -
}


function Test-Python() {
    Write-Color -Text ">>> ", "Detecting host Python ... " -Color Green, Gray -NoNewline
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
    # We are supporting python 3.9 only
    if (([int]$matches[1] -lt 3) -or ([int]$matches[2] -lt 9)) {
      Write-Color -Text "FAILED ", "Version ", "[", $p ,"]",  "is old and unsupported" -Color Red, Yellow, Cyan, White, Cyan, Yellow
      Set-Location -Path $current_dir
      Exit-WithCode 1
    } elseif (([int]$matches[1] -eq 3) -and ([int]$matches[2] -gt 9)) {
        Write-Color -Text "WARNING Version ", "[",  $p, "]",  " is unsupported, use at your own risk." -Color Yellow, Cyan, White, Cyan, Yellow
        Write-Color -Text "*** ", "OpenPype supports only Python 3.9" -Color Yellow, White
    } else {
        Write-Color "OK ", "[",  $p, "]" -Color Green, Cyan, White, Cyan
    }
}

if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$repo_root\.poetry"
}


Set-Location -Path $repo_root

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
if (-not (Test-Path 'env:_INSIDE_AYON_TOOL')) {
    Write-Host $art -ForegroundColor DarkGreen
}

# Enable if PS 7.x is needed.
# Show-PSWarning

Test-Python

Write-Color -Text ">>> ", "Reading Poetry ... " -Color Green, Gray -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Color -Text "NOT FOUND" -Color Yellow
    Install-Poetry
    Write-Color -Text "INSTALLED" -Color Cyan
} else {
    Write-Color -Text "OK" -Color Green
}

if (-not (Test-Path -PathType Leaf -Path "$($repo_root)\poetry.lock")) {
    Write-Color -Text ">>> ", "Installing virtual environment and creating lock." -Color Green, Gray
} else {
    Write-Color -Text ">>> ", "Installing virtual environment from lock." -Color Green, Gray
}
$startTime = [int][double]::Parse((Get-Date -UFormat %s))
& "$env:POETRY_HOME\bin\poetry" install --no-root $poetry_verbosity --ansi
if ($LASTEXITCODE -ne 0) {
    Write-Color -Text "!!! ", "Poetry command failed." -Color Red, Yellow
    Set-Location -Path $current_dir
    Exit-WithCode 1
}
Write-Color -Text ">>> ", "Installing pre-commit hooks ..." -Color Green, White
& "$env:POETRY_HOME\bin\poetry" run pre-commit install
if ($LASTEXITCODE -ne 0) {
    Write-Color -Text "!!! ", "Installation of pre-commit hooks failed." -Color Red, Yellow
    Set-Location -Path $current_dir
    Exit-WithCode 1
}

$endTime = [int][double]::Parse((Get-Date -UFormat %s))
Set-Location -Path $current_dir
try
{
    New-BurntToastNotification -AppLogo "$repo_root/common/ayon_common/resources/AYON.png" -Text "OpenPype", "Virtual environment created.", "All done in $( $endTime - $startTime ) secs."
} catch {}
Write-Color -Text ">>> ", "Virtual environment created." -Color Green, White
