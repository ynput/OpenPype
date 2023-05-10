# Building the plugin

In order to successfully build the plugin, make sure that the path to the UnrealBuildTool.exe is specified correctly.
After the UBT path specify for which platform it will be compiled. in the -Project parameter, specify the path to the 
CommandletProject.uproject file. Next the build type has to be specified (DebugGame, Development, Package, etc.) and then the -TargetType (Editor, Runtime, etc.)

`BuildPlugin_[Ver].bat` runs the building process in the background. If you want to show the progress inside the
command prompt, use the `BuildPlugin_[Ver]_Window.bat` file.


