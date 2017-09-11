@echo OFF

echo Entering Maya2016 environment...

:: Environment: Maya
set CB_MAYA_VERSION=2016
set CB_MAYA_SHARED=%CB_APP_SHARED%\maya_shared\%CB_MAYA_VERSION%

if "%CB_MAYA_SHARED%" == "" (
    echo Error: "CB_MAYA_SHARED" not set
    goto :eof
)


:: For scripts menu tool
set PYTHONPATH=%C:\Users\User\Documents\development\scriptsmenu\python;%PYTHONPATH%
set CB_SCRIPTS=%CB_PIPELINE%\git\cbMayaScripts\cbMayaScripts
set COLORBLEED_SCRIPTS=%CB_SCRIPTS%

:: Colorbleed Maya
set PYTHONPATH=%CB_PIPELINE%\git\cbMayaScripts;%PYTHONPATH%
set PYTHONPATH=%CB_PIPELINE%\git\inventory\python;%PYTHONPATH%

:: Maya shared
set MAYA_PLUG_IN_PATH=%CB_MAYA_SHARED%\plugins;%MAYA_PLUGIN_PATH%
set MAYA_SHELF_PATH=%CB_MAYA_SHARED%\prefs\shelves;%MAYA_SHELF_PATH%
set MAYA_SCRIPT_PATH=%CB_MAYA_SHARED%\scripts;%MAYA_SCRIPT_PATH%
set XBMLANGPATH=%CB_MAYA_SHARED%\prefs\icons;%XBMLANGPATH%
set MAYA_PRESET_PATH=%CB_MAYA_SHARED%\prefs\attrPresets;%MAYA_PRESET_PATH%
set PYTHONPATH=%CB_MAYA_SHARED%\scripts;%PYTHONPATH%
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules;%MAYA_MODULE_PATH%

:: Additional modules
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\mGear_2016;%MAYA_MODULE_PATH%
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\SOuP;%MAYA_MODULE_PATH%
set MAYA_SHELF_PATH=%CB_MAYA_SHARED%\modules\SOuP\shelves;%MAYA_SHELF_PATH%
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\pdipro35c_Maya2016x64;%MAYA_MODULE_PATH%
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\ovdb\maya\maya2016;%MAYA_MODULE_PATH%
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\cvshapeinverter;%MAYA_MODULE_PATH%
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\Toolchefs;%MAYA_MODULE_PATH%
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\Exocortex;%MAYA_MODULE_PATH%

:: Miarmy
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\Basefount\Miarmy;%MAYA_MODULE_PATH%
set PATH=%CB_MAYA_SHARED%\modules\Basefount\Miarmy\bin;%PATH%
set VRAY_PLUGINS_x64=%CB_MAYA_SHARED%\modules\Basefount\Miarmy\bin\vray\vray_3.1_3.3_3.4\Maya2015and2016;%VRAY_PLUGINS_x64%;

:: Yeti
set MAYA_MODULE_PATH=%CB_MAYA_SHARED%\modules\Yeti-v2.1.5_Maya2016-windows64;%MAYA_MODULE_PATH%
set PATH=%CB_MAYA_SHARED%\modules\Yeti-v2.1.5_Maya2016-windows64\bin;%PATH%;
set VRAY_PLUGINS_x64=%CB_MAYA_SHARED%\modules\Yeti-v2.1.5_Maya2016-windows64\bin;%VRAY_PLUGINS_x64%;
set VRAY_FOR_MAYA2016_PLUGINS_x64=%CB_MAYA_SHARED%\modules\Yeti-v2.1.5_Maya2016-windows64\bin;%VRAY_FOR_MAYA2016_PLUGINS_x64%;
set REDSHIFT_MAYAEXTENSIONSPATH=%CB_MAYA_SHARED%\modules\Yeti-v2.1.5_Maya2016-windows64\plug-ins;%REDSHIFT_MAYAEXTENSIONSPATH%
set peregrinel_LICENSE=5053@CBserver

:: maya-capture
set PYTHONPATH=%CB_PIPELINE%\git\maya-capture;%PYTHONPATH%
set PYTHONPATH=%CB_PIPELINE%\git\maya-capture-gui;%PYTHONPATH%
set PYTHONPATH=%CB_PIPELINE%\git\maya-capture-gui-cb;%PYTHONPATH%

:: maya-matrix-deform
set PYTHONPATH=%CB_PIPELINE%\git\maya-matrix-deformers;%PYTHONPATH%
set MAYA_PLUG_IN_PATH=%CB_PIPELINE%\git\maya-matrix-deformers\plugin;%MAYA_PLUG_IN_PATH%

:: rapid-rig
set XBMLANGPATH=%CB_MAYA_SHARED%\scripts\RapidRig_Modular_V02;%XBMLANGPATH%
set MAYA_SCRIPT_PATH=%CB_MAYA_SHARED%\scripts\RapidRig_Modular_V02;%MAYA_SCRIPT_PATH%


:: Fix Maya Playblast Color Management depth
set MAYA_FLOATING_POINT_RT_PLAYBLAST=1


:: Fix V-ray forcing affinity to 100%
set VRAY_USE_THREAD_AFFINITY=0