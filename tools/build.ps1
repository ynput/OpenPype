<#
.SYNOPSIS
  Helper script to build AYON desktop.

.DESCRIPTION
  This script will detect Python installation, and build AYON to `build`
  directory using existing virtual environment created by Poetry (or
  by running `/tools/create_venv.ps1`). It will then shuffle dependencies in
  build folder to optimize for different Python versions (2/3) in Python host.

.EXAMPLE

PS> .\build.ps1

.EXAMPLE

To build without automatical submodule update:
PS> .\build.ps1 --no-submodule-update

.LINK
https://openpype.io/docs

#>

$arguments=$ARGS
$disable_submodule_update=""
if($arguments -eq "--no-submodule-update") {
    $disable_submodule_update=$true
}

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$repo_root = (Get-Item $script_dir).parent.FullName

# Install PSWriteColor to support colorized output to terminal
$env:PSModulePath = $env:PSModulePath + ";$($repo_root)\tools\modules\powershell"

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

function Install-Poetry() {
    Write-Color -Text ">>> ", "Installing Poetry ... " -Color Green, Gray
    $env:POETRY_HOME="$repo_root\.poetry"
    (Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py -UseBasicParsing).Content | python -
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

$env:_INSIDE_AYON_TOOL = "1"

if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$repo_root\.poetry"
}

Set-Location -Path $repo_root

$version_file = Get-Content -Path "$($repo_root)\version.py"
$result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+.*)"')
$ayon_version = $result[0].Groups['version'].Value
if (-not $ayon_version) {
  Write-Color -Text "!!! ", "Cannot determine AYON version." -Color Yellow, Gray
  Exit-WithCode 1
}

# Create build directory if not exist
if (-not (Test-Path -PathType Container -Path "$($repo_root)\build")) {
    New-Item -ItemType Directory -Force -Path "$($repo_root)\build"
}

Write-Color -Text "--- ", "Cleaning build directory ..." -Color Yellow, Gray
try {
    Remove-Item -Recurse -Force "$($repo_root)\build\*"
}
catch {
    Write-Color -Text "!!! ", "Cannot clean build directory, possibly because process is using it." -Color Red, Gray
    Write-Color -Text $_.Exception.Message -Color Red
    Exit-WithCode 1
}
if (-not $disable_submodule_update) {
    Write-Color -Text ">>> ", "Making sure submodules are up-to-date ..." -Color Green, Gray
    & git submodule update --init --recursive
} else {
    Write-Color -Text "*** ", "Not updating submodules ..." -Color Green, Gray
}

Write-Color -Text ">>> ", "AYON [ ", $ayon_version, " ]" -Color Green, White, Cyan, White

Write-Color -Text ">>> ", "Reading Poetry ... " -Color Green, Gray -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Color -Text "NOT FOUND" -Color Yellow
    Write-Color -Text "*** ", "We need to install Poetry create virtual env first ..." -Color Yellow, Gray
    & "$repo_root\tools\create_env.ps1"
} else {
    Write-Color -Text "OK" -Color Green
}

Write-Color -Text ">>> ", "Cleaning cache files ... " -Color Green, Gray -NoNewline
Get-ChildItem $repo_root -Filter "*.pyc" -Force -Recurse | Where-Object { $_.FullName -inotmatch 'build' } | Remove-Item -Force
Get-ChildItem $repo_root -Filter "*.pyo" -Force -Recurse | Where-Object { $_.FullName -inotmatch 'build' } | Remove-Item -Force
Get-ChildItem $repo_root -Filter "__pycache__" -Force -Recurse | Where-Object { $_.FullName -inotmatch 'build' } | Remove-Item -Force -Recurse
Write-Color -Text "OK" -Color green

Write-Color -Text ">>> ", "Building AYON ..." -Color Green, White
$startTime = [int][double]::Parse((Get-Date -UFormat %s))

$out = &  "$($env:POETRY_HOME)\bin\poetry" run python setup.py build 2>&1
Set-Content -Path "$($repo_root)\build\build.log" -Value $out
if ($LASTEXITCODE -ne 0)
{
    Write-Color -Text "------------------------------------------" -Color Red
    Get-Content "$($repo_root)\build\build.log"
    Write-Color -Text "------------------------------------------" -Color Yellow
    Write-Color -Text "!!! ", "Build failed. Check the log: ", ".\build\build.log" -Color Red, Yellow, White
    Exit-WithCode $LASTEXITCODE
}

Set-Content -Path "$($repo_root)\build\build.log" -Value $out
& "$($env:POETRY_HOME)\bin\poetry" run python "$($repo_root)\tools\build_dependencies.py"

Write-Color -Text ">>> ", "Restoring current directory" -Color Green, Gray
Set-Location -Path $current_dir

$endTime = [int][double]::Parse((Get-Date -UFormat %s))
try
{
    New-BurntToastNotification -AppLogo "$repo_root/common/ayon_common/resources/AYON.png" -Text "AYON build complete!", "All done in $( $endTime - $startTime ) secs. You will find AYON and build log in build directory."
} catch {}
Write-Color -Text "*** ", "All done in ", $($endTime - $startTime), " secs. You will find AYON and build log in ", "'.\build'", " directory." -Color Green, Gray, White, Gray, White, Gray
