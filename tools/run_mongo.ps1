<#
.SYNOPSIS
  Helper script to run mongodb.

.DESCRIPTION
  This script will detect mongodb, add it to the PATH and launch it on specified port and db location.

.EXAMPLE

PS> .\run_mongo.ps1

#>

$art = @"

▒█▀▀▀█ █▀▀█ █▀▀ █▀▀▄ ▒█▀▀█ █░░█ █▀▀█ █▀▀ ▀█▀ ▀█▀ ▀█▀
▒█░░▒█ █░░█ █▀▀ █░░█ ▒█▄▄█ █▄▄█ █░░█ █▀▀ ▒█░ ▒█░ ▒█░
▒█▄▄▄█ █▀▀▀ ▀▀▀ ▀░░▀ ▒█░░░ ▄▄▄█ █▀▀▀ ▀▀▀ ▄█▄ ▄█▄ ▄█▄
            .---= [ by Pype Club ] =---.
                 https://openpype.io

"@

Write-Host $art -ForegroundColor DarkGreen

function Exit-WithCode($exitcode) {
   # Only exit this host process if it's a child of another PowerShell parent process...
   $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
   $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
   if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }

   exit $exitcode
}


function Find-Mongo {
    $defaultPath = "C:\Program Files\MongoDB\Server"
    Write-Host ">>> " -NoNewLine -ForegroundColor Green
    Write-Host "Detecting MongoDB ... " -NoNewline
    if (-not (Get-Command "mongod" -ErrorAction SilentlyContinue)) {
        if(Test-Path "$($defaultPath)\*\bin\mongod.exe" -PathType Leaf) {
        # we have mongo server installed on standard Windows location
        # so we can inject it to the PATH. We'll use latest version available.
        $mongoVersions = Get-ChildItem -Directory 'C:\Program Files\MongoDB\Server' | Sort-Object -Property {$_.Name -as [int]}
        if(Test-Path "$($mongoVersions[-1])\bin\mongod.exe" -PathType Leaf) {
            $env:PATH = "$($env:PATH);$($mongoVersions[-1])\bin\"
            Write-Host "OK" -ForegroundColor Green
            Write-Host "  - auto-added from [ " -NoNewline
            Write-Host "$($mongoVersions[-1])\bin\mongod.exe" -NoNewLine -ForegroundColor Cyan
            Write-Host " ]"
            return "$($mongoVersions[-1])\bin\mongod.exe"
        } else {
            Write-Host "FAILED " -NoNewLine -ForegroundColor Red
            Write-Host "MongoDB not detected" -ForegroundColor Yellow
            Write-Host "Tried to find it on standard location " -NoNewline -ForegroundColor Gray
            Write-Host " [ " -NoNewline -ForegroundColor Cyan
            Write-Host "$($mongoVersions[-1])\bin\mongod.exe" -NoNewline -ForegroundColor White
            Write-Host " ] " -NoNewLine -ForegroundColor Cyan
            Write-Host "but failed." -ForegroundColor Gray
            Exit-WithCode 1
        }
    } else {
        Write-Host "FAILED " -NoNewLine -ForegroundColor Red
        Write-Host "MongoDB not detected in PATH" -ForegroundColor Yellow
        Exit-WithCode 1
    }
  } else {
        Write-Host "OK" -ForegroundColor Green
        return Get-Command "mongod" -ErrorAction SilentlyContinue
  }
  <#
  .SYNOPSIS
  Function to detect mongod in path.
  .DESCRIPTION
  This will test presence of mongod in PATH. If it's not there, it will try
  to find it in default install location. It support different mongo versions
  (using latest if found). When mongod is found, path to it is added to PATH
  #>
}

$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

# mongodb port
$port = 2707

# path to database
$dbpath = (Get-Item $openpype_root).parent.FullName + "\mongo_db_data"

$mongoPath = Find-Mongo
Start-Process -FilePath $mongopath "--dbpath $($dbpath) --port $($port)" -PassThru


