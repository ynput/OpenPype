<#
.SYNOPSIS
  Helper script to run Docusaurus for easy editing of OpenPype documentation.

.DESCRIPTION
  This script is using `yarn` package manager to run Docusaurus. If you don't
  have `yarn`, install Node.js (https://nodejs.org/) and then run:

  npm install -g yarn

  It take some time to run this script. If all is successful you should see
  new browser window with OpenPype documentation. All changes is markdown files
  under .\website should be immediately seen in browser.

.EXAMPLE

PS> .\run_documentation.ps1

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

$script_dir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$openpype_root = (Get-Item $script_dir).parent.FullName

Set-Location $openpype_root/website

& yarn install
& yarn start
