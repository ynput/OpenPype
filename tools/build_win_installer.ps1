<#
.SYNOPSIS
  Helper script to build OpenPype Installer.

.DESCRIPTION
  This script will use already built OpenPype (in `build` directory) and
  create Windows installer from it using Inno Setup (https://jrsoftware.org/)

.EXAMPLE

PS> .\build_win_installer.ps1

#>

function Start-Progress {
    param([ScriptBlock]$code)
    $scroll = "/-\|/-\|"
    $idx = 0
    $job = Invoke-Command -ComputerName $env:ComputerName -ScriptBlock { $code } -AsJob

    $origpos = $host.UI.RawUI.CursorPosition

    # $origpos.Y -= 1

    while (($job.State -eq "Running") -and ($job.State -ne "NotStarted"))
    {
        $host.UI.RawUI.CursorPosition = $origpos
        Write-Host $scroll[$idx] -NoNewline
        $idx++
        if ($idx -ge $scroll.Length)
        {
            $idx = 0
        }
        Start-Sleep -Milliseconds 100
    }
    # It's over - clear the activity indicator.
    $host.UI.RawUI.CursorPosition = $origpos
    Write-Host ' '
  <#
  .SYNOPSIS
  Display spinner for running job
  .PARAMETER code
  Job to display spinner for
  #>
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

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

Set-Location -Path $openpype_root

$version_file = Get-Content -Path "$($openpype_root)\openpype\version.py"
$result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+.*)"')
$openpype_version = $result[0].Groups['version'].Value
if (-not $openpype_version) {
  Write-Host "!!! " -ForegroundColor yellow -NoNewline
  Write-Host "Cannot determine OpenPype version."
  Exit-WithCode 1
}
$env:BUILD_VERSION = $openpype_version

iscc 

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

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Creating OpenPype installer ... " -ForegroundColor white

$build_dir_command = @"
import sys
from distutils.util import get_platform
print('exe.{}-{}'.format(get_platform(), sys.version[0:3]))
"@

$build_dir = & $python -c $build_dir_command
Write-Host "Build directory ... ${build_dir}" -ForegroundColor white
$env:BUILD_DIR = $build_dir

if (Get-Command iscc -errorAction SilentlyContinue -ErrorVariable ProcessError)
{
  iscc "$openpype_root\inno_setup.iss"
}else {
  Write-Host "!!! Cannot find Inno Setup command" -ForegroundColor red
  Write-Host "!!! You can download it at https://jrsoftware.org/" -ForegroundColor red
  Exit-WithCode 1
}


Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "restoring current directory"
Set-Location -Path $current_dir

Write-Host "*** " -NoNewline -ForegroundColor Cyan
Write-Host "All done. You will find OpenPype installer in " -NoNewLine
Write-Host "'.\build'" -NoNewline -ForegroundColor Green
Write-Host " directory."
