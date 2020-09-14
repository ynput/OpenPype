@echo off

set __app__="Photoshop 2020"
set __exe__="C:\Program Files\Adobe\Adobe Photoshop 2020\Photoshop.exe"
if not exist %__exe__% goto :missing_app

start %__app__% cmd.exe /k "%PYPE_PYTHON_EXE% -c ^"import avalon.photoshop;avalon.photoshop.launch("%__exe__%")^""

goto :eof

pause

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
