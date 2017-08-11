@echo off
echo Entering pipeline (raw development) environment...

:: Initialize environment
set CB_PIPELINE=P:\pipeline\dev

set CB_APP_SHARED=%CB_PIPELINE%\apps

if "%CB_APP_SHARED%" == "" (
    echo Error: "CB_APP_SHARED" not set
    goto :eof
)

echo setting STORAGE..
set STORAGE=P:

:: Core
echo Add cb core..
set PYTHONPATH=%CB_PIPELINE%\git\cb;%PYTHONPATH%
set PYTHONPATH=%CB_PIPELINE%\git\cbra;%PYTHONPATH%

:: Extra
set PYTHONPATH=%CB_PIPELINE%\git\pyseq;%PYTHONPATH%
set PYTHONPATH=%CB_PIPELINE%\git\Qt.py;%PYTHONPATH%

:: Ftrack-connect
::set PYTHONPATH=%CB_PIPELINE%\git\ftrack-connect\source;%PYTHONPATH%

:: FFMPEG
set FFMPEG_PATH=%CB_APP_SHARED%\ffmpeg\bin\ffmpeg.exe