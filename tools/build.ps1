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

# Create build directory if not exist
if (-not (Test-Path -PathType Container -Path "$($openpype_root)\build")) {
    New-Item -ItemType Directory -Force -Path "$($openpype_root)\build"
}

Write-Host "--- " -NoNewline -ForegroundColor yellow
Write-Host "Cleaning build directory ..."
try {
    Remove-Item -Recurse -Force "$($openpype_root)\build\*"
}
catch {
    Write-Host "!!! " -NoNewline -ForegroundColor Red
    Write-Host "Cannot clean build directory, possibly because process is using it."
    Write-Host $_.Exception.Message
    Exit-WithCode 1
}

Write-Host ">>> " -NoNewLine -ForegroundColor green
Write-Host "Making sure submodules are up-to-date ..."
git submodule update --init --recursive

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Building OpenPype [ " -NoNewline -ForegroundColor white
Write-host $openpype_version  -NoNewline -ForegroundColor green
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
$env:PATH = "$($env:PATH);$($env:USERPROFILE)\.poetry\bin"

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Cleaning cache files ... " -NoNewline
Get-ChildItem $openpype_root -Filter "*.pyc" -Force -Recurse | Remove-Item -Force
Get-ChildItem $openpype_root -Filter "*.pyo" -Force -Recurse | Remove-Item -Force
Get-ChildItem $openpype_root -Filter "__pycache__" -Force -Recurse | Remove-Item -Force -Recurse
Write-Host "OK" -ForegroundColor green

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Building OpenPype ..."

$out = & poetry run python setup.py build 2>&1
if ($LASTEXITCODE -ne 0)
{
    Set-Content -Path "$($openpype_root)\build\build.log" -Value $out
    Write-Host "!!! " -NoNewLine -ForegroundColor Red
    Write-Host "Build failed. Check the log: " -NoNewline
    Write-Host ".\build\build.log" -ForegroundColor Yellow
    Exit-WithCode $LASTEXITCODE
}

Set-Content -Path "$($openpype_root)\build\build.log" -Value $out
& poetry run python "$($openpype_root)\tools\build_dependencies.py"

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "restoring current directory"
Set-Location -Path $current_dir

Write-Host "*** " -NoNewline -ForegroundColor Cyan
Write-Host "All done. You will find OpenPype and build log in " -NoNewLine
Write-Host "'.\build'" -NoNewline -ForegroundColor Green
Write-Host " directory."
