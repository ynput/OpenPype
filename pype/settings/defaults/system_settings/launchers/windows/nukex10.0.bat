@echo off

set __app__="NukeX10.0v4"
set __exe__="C:\Program Files\Nuke10.0v4\Nuke10.0.exe" -nukex
if not exist %__exe__% goto :missing_app

start %__app__% %__exe__% %*

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
