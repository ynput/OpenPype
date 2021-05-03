<#
.SYNOPSIS
  Helper script to build OpenPype.

.DESCRIPTION
  This script will detect Python installation, and build OpenPype to `build`
  directory using existing virtual environment created by Poetry (or
  by running `/tools/create_venv.ps1`). It will then shuffle dependencies in
  build folder to optimize for different Python versions (2/3) in Python host.

.EXAMPLE

PS> .\build.ps1

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

function Install-Poetry() {
    Write-Host ">>> " -NoNewline -ForegroundColor Green
    Write-Host "Installing Poetry ... "
    (Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -UseBasicParsing).Content | python -
    # add it to PATH
    $env:PATH = "$($env:PATH);$($env:USERPROFILE)\.poetry\bin"
}

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
Write-Host "Creating OpenPype installer ... " -ForegroundColor white

$build_dir_command = @"
import sys
from distutils.util import get_platform
print('exe.{}-{}'.format(get_platform(), sys.version[0:3]))
"@

$build_dir = & python -c $build_dir_command
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
