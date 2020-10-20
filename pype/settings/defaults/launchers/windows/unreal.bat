set __app__="Unreal Editor"
set __exe__="%AVALON_CURRENT_UNREAL_ENGINE%\Engine\Binaries\Win64\UE4Editor.exe"
if not exist %__exe__% goto :missing_app

start %__app__% %__exe__% %PYPE_UNREAL_PROJECT_FILE% %*

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
