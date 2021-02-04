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


        ____________
       /\      ___  \
       \ \     \/_\  \
        \ \     _____/ ______   ___ ___ ___
         \ \    \___/ /\     \  \  \\  \\  \
          \ \____\    \ \_____\  \__\\__\\__\
           \/____/     \/_____/  . PYPE Club .

"@

Write-Host $art -ForegroundColor DarkGreen

# Enable if PS 7.x is needed.
# Show-PSWarning

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pype_root = (Get-Item $script_dir).parent.FullName

Set-Location -Path $pype_root

$version_file = Get-Content -Path "$($pype_root)\pype\version.py"
$result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+)"')
$pype_version = $result[0].Groups['version'].Value
if (-not $pype_version) {
  Write-Host "!!! " -ForegroundColor yellow -NoNewline
  Write-Host "Cannot determine Pype version."
  Exit-WithCode 1
}

# Create build directory if not exist
if (-not (Test-Path -PathType Container -Path "$($pype_root)\build")) {
    New-Item -ItemType Directory -Force -Path "$($pype_root)\build"
}

Write-Host "--- " -NoNewline -ForegroundColor yellow
Write-Host "Cleaning build directory ..."
try {
    Remove-Item -Recurse -Force "$($pype_root)\build\*"
}
catch {
    Write-Host "!!! " -NoNewline -ForegroundColor Red
    Write-Host "Cannot clean build directory, possibly because process is using it."
    Write-Host $_.Exception.Message
    Exit-WithCode 1
}

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Building Pype [ " -NoNewline -ForegroundColor white
Write-host $pype_version  -NoNewline -ForegroundColor green
Write-Host " ] ..." -ForegroundColor white

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Detecting host Python ... " -NoNewline
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "!!! Python not detected" -ForegroundColor red
    Exit-WithCode 1
}
$version_command = @"
import sys
print('{0}.{1}'.format(sys.version_info[0], sys.version_info[1]))
"@

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


Write-Host ">>> " -NoNewline -ForegroundColor Green
Write-Host "Reading Poetry ... " -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:USERPROFILE)\.poetry\bin")) {
    Write-Host "NOT FOUND" -ForegroundColor Yellow
    Install-Poetry
    Write-Host "INSTALLED" -ForegroundColor Cyan
} else {
    Write-Host "OK" -ForegroundColor Green
}


Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Cleaning cache files ... " -NoNewline
Get-ChildItem $pype_root -Filter "*.pyc" -Force -Recurse | Remove-Item -Force
Get-ChildItem $pype_root -Filter "*.pyo" -Force -Recurse | Remove-Item -Force
Get-ChildItem $pype_root -Filter "__pycache__" -Force -Recurse | Remove-Item -Force -Recurse
Write-Host "OK" -ForegroundColor green

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Building Pype ..."
$out = & poetry run python setup.py build 2>&1
if ($LASTEXITCODE -ne 0)
{
    Set-Content -Path "$($pype_root)\build\build.log" -Value $out
    Write-Host "!!! " -NoNewLine -ForegroundColor Red
    Write-Host "Build failed. Check the log: " -NoNewline
    Write-Host ".\build\build.log" -ForegroundColor Yellow
    Exit-WithCode $LASTEXITCODE
}

Set-Content -Path "$($pype_root)\build\build.log" -Value $out
& poetry run python "$($pype_root)\tools\build_dependencies.py"

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "restoring current directory"
Set-Location -Path $current_dir

Write-Host "*** " -NoNewline -ForegroundColor Cyan
Write-Host "All done. You will find Pype and build log in " -NoNewLine
Write-Host "'.\build'" -NoNewline -ForegroundColor Green
Write-Host " directory."
