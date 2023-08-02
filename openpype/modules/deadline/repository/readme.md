# OpenPype Deadline repository overlay

This directory is an overlay for Deadline repository.
It means that you can copy the whole hierarchy to Deadline repository and it
should work.

## Custom Plugins

### OpenPype

### OpenPypeTileAssembler

### HarmonyOpenPype

### CelAction

### Houdini

OpenPype will submit Houdini version as `major.minor.patch` <br>
This requires updating `custom\plugins\Houdini\Houdini.param` with the deisred `Hython_Executable` and `SimTracker` because there's no way to change houdini version from deadline Configure PLugins UI

To achieve that:
1. Copy these blocks to `Houdini.param`
2. Replace `<major>`, `<minor>` and `<patch>` with the desired numbers
3. Update paths from deadline UI

#### Hython Executable block
```
[Houdini<major>_<minor>_<patch>_Hython_Executable]
Label=Houdini <major>.<minor>.<patch> Hython Executable
Category=Render Executables
CategoryOrder=0
Type=multilinemultifilename
Index=14
Default=C:\Program Files\Side Effects Software\Houdini 19.0.000\bin\hython.exe;/Applications/Houdini/Houdini19.0.000/Frameworks/Houdini.framework/Versions/19.0.000/Resources/bin/hython;/opt/hfs19.0/bin/hython
Description=The path to the hython executable. It can be found in the Houdini bin folder.
```

#### Sim Tracker block
```
[Houdini<major>_<minor>_<patch>_SimTracker]
Label=Houdini <major>.<minor>.<patch> Sim Tracker File
Category=HQueue Simulation Job Options
CategoryOrder=1
Type=multilinemultifilename
Index=10
Default=C:\Program Files\Side Effects Software\Houdini 19.0.000\houdini\python3.7libs\simtracker.py;/Applications/Houdini/Houdini19.0.000/Frameworks/Houdini.framework/Versions/19.0.000/Resources/houdini/python3.7libs/simtracker.py;/opt/hfs19.0/houdini/python3.7libs/simtracker.py
Description=The path to the simtracker.py file that is used when distributing HQueue sim jobs. This file can be found in the Houdini install.
```


## Notes

### GlobalJobPreLoad

The `GlobalJobPreLoad` will retrieve the OpenPype executable path from the
`OpenPype` Deadline Plug-in's settings. Then it will call the executable to
retrieve the environment variables needed for the Deadline Job.
These environment variables are injected into rendering process.

Deadline triggers the `GlobalJobPreLoad.py` for each Worker as it starts the
Job.

*Note*: It also contains backward compatible logic to preserve functionality
for old Pype2 and non-OpenPype triggered jobs.

### Plugin
For each render and publishing job the `OpenPype` Deadline Plug-in is checked
for the configured location of the OpenPype executable (needs to be configured
in `Deadline's Configure Plugins > OpenPype`) through `GlobalJobPreLoad`.


### Houdini custom plugin
1. custom plugin will always override default plugins, default plugin remains as it is.
2. it is safe to add or delete them.
3. keeping `Hython Executable` and `Sim Tracker` blocks with `major.minor` adds backward compatibility to the default deadline submissions and older OP deadline integration.
