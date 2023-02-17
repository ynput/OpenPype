<#
.SYNOPSIS
  Helper script to update OpenPype Sphinx sources.

.DESCRIPTION
  This script will run apidoc over OpenPype sources and generate new source rst
  files for documentation. Then it will run build_sphinx to create test html
  documentation build.

.EXAMPLE

PS> .\make_docs.ps1

#>

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

$env:_INSIDE_OPENPYPE_TOOL = "1"

if (-not (Test-Path 'env:POETRY_HOME')) {
    $env:POETRY_HOME = "$openpype_root\.poetry"
}

Set-Location -Path $openpype_root


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

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

# Install PSWriteColor to support colorized output to terminal
$env:PSModulePath = $env:PSModulePath + ";$($openpype_root)\tools\modules\powershell"

Write-Host $art -ForegroundColor DarkGreen

Write-Color -Text ">>> ", "Reading Poetry ... " -Color Green, Gray -NoNewline
if (-not (Test-Path -PathType Container -Path "$($env:POETRY_HOME)\bin")) {
    Write-Color -Text "NOT FOUND" -Color Yellow
    Install-Poetry
    Write-Color -Text "INSTALLED" -Color Cyan
} else {
    Write-Color -Text "OK" -Color Green
}

Write-Color -Text "... ", "This will not overwrite existing source rst files, only scan and add new." -Color Yellow, Gray
Set-Location -Path $openpype_root
Write-Color -Text ">>> ", "Running apidoc ..." -Color Green, Gray
& "$env:POETRY_HOME\bin\poetry" run sphinx-apidoc -M -e -d 10  --ext-intersphinx --ext-todo --ext-coverage --ext-viewcode -o "$($openpype_root)\docs\source" igniter
& "$env:POETRY_HOME\bin\poetry" run sphinx-apidoc.exe -M -e -d 10 --ext-intersphinx --ext-todo --ext-coverage --ext-viewcode -o "$($openpype_root)\docs\source" openpype vendor, openpype\vendor

Write-Color -Text ">>> ", "Building html ..." -Color Green, Gray
& "$env:POETRY_HOME\bin\poetry" run python "$($openpype_root)\setup.py" build_sphinx
Set-Location -Path $current_dir
