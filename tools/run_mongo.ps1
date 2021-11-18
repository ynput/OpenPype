<#
.SYNOPSIS
  Helper script to run mongodb.

.DESCRIPTION
  This script will detect mongodb, add it to the PATH and launch it on specified port and db location.

.EXAMPLE

PS> .\run_mongo.ps1

#>

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

function Exit-WithCode($exitcode) {
   # Only exit this host process if it's a child of another PowerShell parent process...
   $parentPID = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$PID" | Select-Object -Property ParentProcessId).ParentProcessId
   $parentProcName = (Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$parentPID" | Select-Object -Property Name).Name
   if ('powershell.exe' -eq $parentProcName) { $host.SetShouldExit($exitcode) }

   exit $exitcode
}


function Find-Mongo ($preferred_version) {
    $defaultPath = "C:\Program Files\MongoDB\Server"
    Write-Host ">>> " -NoNewLine -ForegroundColor Green
    Write-Host "Detecting MongoDB ... " -NoNewline
    if (-not (Get-Command "mongod" -ErrorAction SilentlyContinue)) {
        if(Test-Path "$($defaultPath)\*\bin\mongod.exe" -PathType Leaf) {
        # we have mongo server installed on standard Windows location
        # so we can inject it to the PATH. We'll use latest version available, or the one defined by
        # $preferred_version.
        $mongoVersions = Get-ChildItem -Directory 'C:\Program Files\MongoDB\Server' | Sort-Object -Property {$_.Name -as [int]}
        if(Test-Path "$($mongoVersions[-1])\bin\mongod.exe" -PathType Leaf) {
            Write-Host "OK" -ForegroundColor Green
            $use_version = $mongoVersions[-1]
            foreach ($v in $mongoVersions) {
                Write-Host "  - found [ " -NoNewline
                Write-Host $v -NoNewLine -ForegroundColor Cyan
                Write-Host " ]" -NoNewLine

                $version = Split-Path $v -Leaf

                if ($preferred_version -eq $version) {
                    Write-Host " *" -ForegroundColor Green
                    $use_version = $v
                } else {
                    Write-Host ""
                }
            }

            $env:PATH = "$($env:PATH);$($use_version)\bin\"

            Write-Host "  - auto-added from [ " -NoNewline
            Write-Host "$($use_version)\bin\mongod.exe" -NoNewLine -ForegroundColor Cyan
            Write-Host " ]"
            return "$($use_version)\bin\mongod.exe"
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

$preferred_version = "5.0"

$mongoPath = Find-Mongo $preferred_version
Write-Host ">>> " -NoNewLine -ForegroundColor Green
Write-Host "Using DB path: " -NoNewLine
Write-Host " [ " -NoNewline -ForegroundColor Cyan
Write-Host "$($dbpath)" -NoNewline -ForegroundColor White
Write-Host " ] "-ForegroundColor Cyan
Write-Host ">>> " -NoNewLine -ForegroundColor Green
Write-Host "Port: " -NoNewLine
Write-Host " [ " -NoNewline -ForegroundColor Cyan
Write-Host "$($port)" -NoNewline -ForegroundColor White
Write-Host " ] " -ForegroundColor Cyan
Start-Process -FilePath $mongopath "--dbpath $($dbpath) --port $($port)" -PassThru | Out-Null

