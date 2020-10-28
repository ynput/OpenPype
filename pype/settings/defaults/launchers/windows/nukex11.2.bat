@echo off

set __app__="NukeX11.2v3"
set __exe__="C:\Program Files\Nuke11.2v3\Nuke11.2.exe" --nukex
if not exist %__exe__% goto :missing_app

start %__app__% %__exe__% %*

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
