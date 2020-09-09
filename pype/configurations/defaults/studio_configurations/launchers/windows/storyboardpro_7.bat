@echo off

set __app__="Storyboard Pro 7"
set __exe__="C:/Program Files (x86)/Toon Boom Animation/Toon Boom Storyboard Pro 7/win64/bin/StoryboardPro.exe"
if not exist %__exe__% goto :missing_app

start %__app__% cmd.exe /k "python -c ^"import avalon.storyboardpro;avalon.storyboardpro.launch("%__exe__%")^""

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
