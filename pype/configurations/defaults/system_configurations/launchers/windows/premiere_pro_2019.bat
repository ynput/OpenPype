@echo off

set __app__="Adobe Premiere Pro"
set __exe__="C:\Program Files\Adobe\Adobe Premiere Pro CC 2019\Adobe Premiere Pro.exe"
if not exist %__exe__% goto :missing_app

python -u %PREMIERA_PATH%\init.py
start %__app__% %__exe__% %*

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
