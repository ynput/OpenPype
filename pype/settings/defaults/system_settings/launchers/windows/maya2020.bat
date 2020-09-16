@echo off

set __app__="Maya 2020"
set __exe__="C:\Program Files\Autodesk\maya2020\bin\maya.exe"
if not exist %__exe__% goto :missing_app

if "%AVALON_LAST_WORKFILE%"=="" (
  start %__app__% %__exe__% %*
) else (
  start %__app__% %__exe__% -file "%AVALON_LAST_WORKFILE%" %*
)

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
