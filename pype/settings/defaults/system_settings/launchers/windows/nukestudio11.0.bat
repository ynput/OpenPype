@echo off

set __app__="NukeStudio11.0v4"
set __exe__="C:\Program Files\Nuke11.0v4\Nuke11.0.exe" -studio
if not exist %__exe__% goto :missing_app

start %__app__% %__exe__% %*

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
