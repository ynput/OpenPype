<#
.SYNOPSIS
  Helper script to update Pype Sphinx sources.

.DESCRIPTION
  This script will run apidoc over Pype sources and generate new source rst
  files for documentation. Then it will run build_sphinx to create test html
  documentation build.

.EXAMPLE

PS> .\make_docs.ps1

#>

$current_dir = Get-Location
$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$pype_root = (Get-Item $script_dir).parent.FullName
Set-Location -Path $pype_root


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

Write-Host "This will not overwrite existing source rst files, only scan and add new."
Set-Location -Path $pype_root
Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Running apidoc ..."
& poetry run sphinx-apidoc -M -e -d 10  --ext-intersphinx --ext-todo --ext-coverage --ext-viewcode -o "$($pype_root)\docs\source" igniter
& poetry run sphinx-apidoc.exe -M -e -d 10 --ext-intersphinx --ext-todo --ext-coverage --ext-viewcode -o "$($pype_root)\docs\source" pype vendor, pype\vendor

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Building html ..."
& poetry run python "$($pype_root)\setup.py" build_sphinx
Set-Location -Path $current_dir
