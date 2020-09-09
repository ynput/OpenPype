@echo off

set __app__="Harmony 17"
set __exe__="C:/Program Files (x86)/Toon Boom Animation/Toon Boom Harmony 17 Premium/win64/bin/HarmonyPremium.exe"
if not exist %__exe__% goto :missing_app

start %__app__% cmd.exe /k "python -c ^"import avalon.harmony;avalon.harmony.launch("%__exe__%")^""

goto :eof

:missing_app
    echo ERROR: %__app__% not found in %__exe__%
    exit /B 1
