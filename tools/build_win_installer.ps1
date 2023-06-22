<#
.SYNOPSIS
  Helper script to build AYON Installer.

.DESCRIPTION
  This script will use already built AYON (in `build` directory) and
  create Windows installer from it using Inno Setup (https://jrsoftware.org/)

.EXAMPLE

PS> .\build_win_installer.ps1

#>
$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$ayon_root = (Get-Item $script_dir).parent.FullName

# Install PSWriteColor to support colorized output to terminal
$env:PSModulePath = $env:PSModulePath + ";$($ayon_root)\tools\modules\powershell"

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
        Write-Color -Text "!!! ", "You are using old version of PowerShell - ",  "$($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor)" -Color Red, Yellow, White
        Write-Color -Text "    Please update to at least 7.0 - ", "https://github.com/PowerShell/PowerShell/releases" -Color Yellow, White
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


Set-Location -Path $ayon_root

$version_file = Get-Content -Path "$($ayon_root)\version.py"
$result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+.*)"')
$ayon_version = $result[0].Groups['version'].Value
if (-not $ayon_version) {
  Write-Color -Text "!!! ", "Cannot determine AYON version." -Color Yellow, Gray
  Exit-WithCode 1
}

$env:BUILD_VERSION = $ayon_version

iscc

Write-Color ">>> ", "Detecting host Python ... " -Color Green, White -NoNewline
$python = "python"
if (Get-Command "pyenv" -ErrorAction SilentlyContinue) {
    $pyenv_python = & pyenv which python
    if (Test-Path -PathType Leaf -Path "$($pyenv_python)") {
        $python = $pyenv_python
    }
}
if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
    Write-Color "!!! ", "Python not detected" -Color Red, Yellow
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
    Write-Color "!!! ", "Cannot determine version" -Color Red, Yellow
    Set-Location -Path $current_dir
    Exit-WithCode 1
}
# We are supporting python 3.9
if (($matches[1] -lt 3) -or ($matches[2] -lt 9)) {
    Write-Host "FAILED Version [ $p ] is old and unsupported" -ForegroundColor red
    Set-Location -Path $current_dir
    Exit-WithCode 1
} elseif (($matches[1] -eq 3) -and ($matches[2] -gt 9)) {
    Write-Host "WARNING Version [ $p ] is unsupported, use at your own risk." -ForegroundColor yellow
    Write-Host "*** " -NoNewline -ForegroundColor yellow
    Write-Host "AYON supports only Python 3.9" -ForegroundColor white
} else {
    Write-Host "OK [ $p ]" -ForegroundColor green
}

Write-Color -Text ">>> ", "Creating AYON installer ... " -Color Green, White

$build_dir = & $python -c "build/output"
Write-Color -Text "--- ", "Build directory ", "${build_dir}" -Color Green, Gray, White
$env:BUILD_DIR = $build_dir

if (-not (Get-Command iscc -errorAction SilentlyContinue -ErrorVariable ProcessError)) {
  Write-Color -Text "!!! ", "Cannot find Inno Setup command" -Color Red, Yellow
  Write-Color "!!! You can download it at https://jrsoftware.org/" -ForegroundColor red
  Exit-WithCode 1
}

& iscc "$ayon_root\inno_setup.iss"

if ($LASTEXITCODE -ne 0) {
    Write-Color -Text "!!! ", "Creating installer failed." -Color Red, Yellow
    Exit-WithCode 1
}

Write-Color -Text ">>> ", "Restoring current directory" -Color Green, Gray
Set-Location -Path $current_dir
try {
    New-BurntToastNotification -AppLogo "$ayon_root/common/ayon_common/resources/AYON.png" -Text "AYON build complete!", "All done. You will find You will find AYON installer in '.\build' directory."
} catch {}
Write-Color -Text "*** ", "All done. You will find AYON installer in ", "'.\build'", " directory." -Color Green, Gray, White, Gray
