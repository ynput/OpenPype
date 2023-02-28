# OpenPype Unreal Integration plugin - UE 4.x

This is plugin for Unreal Editor, creating menu for [OpenPype](https://github.com/getavalon) tools to run.

## How does this work

Plugin is creating basic menu items in **Window/OpenPype** section of Unreal Editor main menu and a button
on the main toolbar with associated menu. Clicking on those menu items is calling callbacks that are
declared in c++ but needs to be implemented during Unreal Editor
startup in `Plugins/OpenPype/Content/Python/init_unreal.py` - this should be executed by Unreal Editor
automatically.
