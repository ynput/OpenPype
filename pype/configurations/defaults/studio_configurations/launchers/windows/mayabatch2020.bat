@echo off

set __app__="Maya Batch 2020"
set __exe__="C:\Program Files\Autodesk\Maya2020\bin\mayabatch.exe"
if not exist %__exe__% goto :missing_app

echo "running maya : %*"
%__exe__% %*
echo "done."
goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
