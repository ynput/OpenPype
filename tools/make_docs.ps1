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
Set-Location -Path $openpype_root


$art = @"


▒█▀▀▀█ █▀▀█ █▀▀ █▀▀▄ ▒█▀▀█ █░░█ █▀▀█ █▀▀ ▀█▀ ▀█▀ ▀█▀
▒█░░▒█ █░░█ █▀▀ █░░█ ▒█▄▄█ █▄▄█ █░░█ █▀▀ ▒█░ ▒█░ ▒█░
▒█▄▄▄█ █▀▀▀ ▀▀▀ ▀░░▀ ▒█░░░ ▄▄▄█ █▀▀▀ ▀▀▀ ▄█▄ ▄█▄ ▄█▄
            .---= [ by Pype Club ] =---.
                 https://openpype.io

"@

Write-Host $art -ForegroundColor DarkGreen

Write-Host "This will not overwrite existing source rst files, only scan and add new."
Set-Location -Path $openpype_root
Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Running apidoc ..."
& poetry run sphinx-apidoc -M -e -d 10  --ext-intersphinx --ext-todo --ext-coverage --ext-viewcode -o "$($openpype_root)\docs\source" igniter
& poetry run sphinx-apidoc.exe -M -e -d 10 --ext-intersphinx --ext-todo --ext-coverage --ext-viewcode -o "$($openpype_root)\docs\source" openpype vendor, openpype\vendor

Write-Host ">>> " -NoNewline -ForegroundColor green
Write-Host "Building html ..."
& poetry run python "$($openpype_root)\setup.py" build_sphinx
Set-Location -Path $current_dir
