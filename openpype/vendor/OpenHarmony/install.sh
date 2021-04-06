#!/bin/bash

set dlPath=pwd
set harmonyPrefsDir=~/Library/Preferences/Toon Boom Animation/

echo -------------------------------------------------------------------
echo -- Starting install of openHarmony open source scripting library --
echo -------------------------------------------------------------------
echo OpenHarmony will be installed to the folder :
echo $dlpath
echo Do not delete the contents of this folder.

REM Check Harmony Versions and make a list
for /d %%D in ("%harmonyPrefsDir%\*Harmony*") do (
  set harmonyVersionDir=%%~fD
  for /d %%V in ("!harmonyVersionDir!\*-layouts*") do (
    set "folderName=%%~nD"
    set "versionName=%%~nV"
    set "harmonyFolder=!folderName:~-7!"
    set "harmonyVersions=!versionName:~0,2!"
    echo Found Toonboom Harmony !harmonyFolder! !harmonyVersions! - installing openHarmony for this version.
    set "installDir=!harmonyPrefsDir!\Toon Boom Harmony !harmonyFolder!\!harmonyVersions!00-scripts\"
