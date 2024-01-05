<#
.SYNOPSIS
  Helper script to update traits defined by yaml files.

.DESCRIPTION
  This script will take all yaml files in openpype/pipeline/traits and
    generate python files from them. The generated files will be placed in
    openpype/pipeline/traits/generated.

.EXAMPLE

PS> .\refresh_trait.ps1

#>

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

# Install PSWriteColor to support colorized output to terminal
$env:PSModulePath = $env:PSModulePath + ";$($openpype_root)\tools\modules\powershell"

if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$openpype_root\.poetry"
}

Set-Location -Path $openpype_root

function Exit-WithCode($exitcode) {
   # Only exit this host process if it's a child of another PowerShell parent process...
   $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
   $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
   if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }

   exit $exitcode
}

function New-TemporaryDirectory {
    $parent = [System.IO.Path]::GetTempPath()
    [string] $name = [System.Guid]::NewGuid()
    New-Item -ItemType Directory -Path (Join-Path $parent $name)
}

$art = @"

                    ▄██▄
         ▄███▄ ▀██▄ ▀██▀ ▄██▀ ▄██▀▀▀██▄    ▀███▄      █▄
        ▄▄ ▀██▄  ▀██▄  ▄██▀ ██▀      ▀██▄  ▄  ▀██▄    ███
       ▄██▀  ██▄   ▀ ▄▄ ▀  ██         ▄██  ███  ▀██▄  ███
      ▄██▀    ▀██▄   ██    ▀██▄      ▄██▀  ███    ▀██ ▀█▀
     ▄██▀      ▀██▄  ▀█      ▀██▄▄▄▄██▀    █▀      ▀██▄

     ·  · - =[ by YNPUT ]:[ http://ayon.ynput.io ]= - ·  ·

"@

function Get-AsciiArt() {
    Write-Host $art -ForegroundColor DarkGreen
}

$version_file = Get-Content -Path "$($openpype_root)\openpype\version.py"
$result = [regex]::Matches($version_file, '__version__ = "(?<version>\d+\.\d+.\d+.*)"')
$openpype_version = $result[0].Groups['version'].Value
if (-not $openpype_version) {
  Write-Color -Text "!!! ", "Cannot determine OpenPype version." -Color Yellow, Gray
  Exit-WithCode 1
}

Write-Color -Text ">>> ", "Reading Poetry ... " -Color Green, Gray -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Color -Text "NOT FOUND" -Color Yellow
    Write-Color -Text "*** ", "We need to install Poetry create virtual env first ..." -Color Yellow, Gray
    & "$openpype_root\tools\create_env.ps1"
} else {
    Write-Color -Text "OK" -Color Green
}

$temp_traits = New-TemporaryDirectory
Write-Color ">>> ", "Generating traits ..." -Color Green, Gray
Write-Color ">>> ", "Temporary directory: ", $temp_traits -Color Green, Gray, Cyan

$directoryPath = "$($openpype_root)\openpype\pipeline\traits"

Write-Color ">>> ", "Cleaning generated traits ..." -Color Green, Gray
try {
    Remove-Item -Recurse -Force "$($directoryPath)\generated\*"
}
catch {
    Write-Color -Text "!!! ", "Cannot clean generated Traits director." -Color Red, Gray
    Write-Color -Text $_.Exception.Message -Color Red
    Exit-WithCode 1
}

Get-ChildItem -Path $directoryPath -Filter "*.yml" | ForEach-Object {
    Write-Color "  - ", "Generating from [ ", $_.FullName , " ]" -Color Green, Gray, White, Gray
    & "$env:POETRY_HOME\bin\poetry.exe" run openassetio-traitgen -o $temp_traits -g python -v $_.FullName
    $content = Get-Content $_.FullName
    Write-Output $content
}

Write-Color ">>> ", "Moving traits to repository ..." -Color Green, Gray
Move-Item -Path $temp_traits\* -Destination "$($directoryPath)\generated" -Force
# Get all subdirectories
$subDirs = Get-ChildItem -Path "$($directoryPath)\generated" -Directory
$initContent = ""
$allSubmodules = ""
# Loop through each subdirectory
foreach ($subDir in $subDirs) {
    # Extract the directory name
    $moduleName = $subDir.Name

    # Add the import statement to the content
    $initContent += "from . import $moduleName`n"
    $allSubmodules += "    $($subDir.Name),`n"
}
$initContent += "`n`n__all__ = [`n$allSubmodules]`n"

Write-Color ">>> ", "Writing index ..." -Color Green, Gray
$initContent | Out-File -FilePath "$directoryPath\generated\__init__.py" -Encoding utf8 -Force

Write-Color -Text ">>> ", "Traits generated." -Color Green, White
