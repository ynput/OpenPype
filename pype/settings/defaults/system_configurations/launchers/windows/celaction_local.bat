set __app__="CelAction2D"
set __app_dir__="C:\Program Files (x86)\CelAction\"
set __exe__="C:\Program Files (x86)\CelAction\CelAction2D.exe"

if not exist %__exe__% goto :missing_app

pushd %__app_dir__%

if "%PYPE_CELACTION_PROJECT_FILE%"=="" (
  start %__app__% %__exe__% %*
) else (
  start %__app__% %__exe__% "%PYPE_CELACTION_PROJECT_FILE%" %*
)

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
