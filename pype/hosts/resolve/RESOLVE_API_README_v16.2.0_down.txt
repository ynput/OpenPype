Updated as of 08 March 2019

--------------------------
In this package, you will find a brief introduction to the Scripting API for DaVinci Resolve Studio. Apart from this README.txt file, this package contains folders containing the basic import modules for scripting access (DaVinciResolve.py) and some representative examples.

Overview
--------

As with Blackmagic Design Fusion scripts, user scripts written in Lua and Python programming languages are supported. By default, scripts can be invoked from the Console window in the Fusion page, or via command line. This permission can be changed in Resolve Preferences, to be only from Console, or to be invoked from the local network. Please be aware of the security implications when allowing scripting access from outside of the Resolve application.


Using a script
--------------
DaVinci Resolve needs to be running for a script to be invoked.

For a Resolve script to be executed from an external folder, the script needs to know of the API location. 
You may need to set the these environment variables to allow for your Python installation to pick up the appropriate dependencies as shown below:

    Mac OS X:
    RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/"
    RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
    PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"

    Windows:
    RESOLVE_SCRIPT_API="%PROGRAMDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\"
    RESOLVE_SCRIPT_LIB="C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\fusionscript.dll"
    PYTHONPATH="%PYTHONPATH%;%RESOLVE_SCRIPT_API%\\Modules\\"

    Linux:
    RESOLVE_SCRIPT_API="/opt/resolve/Developer/Scripting/"
    RESOLVE_SCRIPT_LIB="/opt/resolve/libs/Fusion/fusionscript.so"
    PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"
    (Note: For standard ISO Linux installations, the path above may need to be modified to refer to /home/resolve instead of /opt/resolve)

As with Fusion scripts, Resolve scripts can also be invoked via the menu and the Console.

On startup, DaVinci Resolve scans the Utility Scripts directory and enumerates the scripts found in the Script application menu. Placing your script in this folder and invoking it from this menu is the easiest way to use scripts. The Utility Scripts folder is located in:
    Mac OS X:   /Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/
    Windows:    %APPDATA%\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Comp\
    Linux:      /opt/resolve/Fusion/Scripts/Comp/   (or /home/resolve/Fusion/Scripts/Comp/ depending on installation)

The interactive Console window allows for an easy way to execute simple scripting commands, to query or modify properties, and to test scripts. The console accepts commands in Python 2.7, Python 3.6 and Lua and evaluates and executes them immediately. For more information on how to use the Console, please refer to the DaVinci Resolve User Manual.

This example Python script creates a simple project:
    #!/usr/bin/env python
    import DaVinciResolveScript as dvr_script
    resolve = dvr_script.scriptapp("Resolve")
    fusion = resolve.Fusion()
    projectManager = resolve.GetProjectManager()
    projectManager.CreateProject("Hello World")

The resolve object is the fundamental starting point for scripting via Resolve. As a native object, it can be inspected for further scriptable properties - using table iteration and `getmetatable` in Lua and dir, help etc in Python (among other methods). A notable scriptable object above is fusion - it allows access to all existing Fusion scripting functionality.

Running DaVinci Resolve in headless mode
----------------------------------------

DaVinci Resolve can be launched in a headless mode without the user interface using the -nogui command line option. When DaVinci Resolve is launched using this option, the user interface is disabled. However, the various scripting APIs will continue to work as expected.

Basic Resolve API
-----------------

Some commonly used API functions are described below (*). As with the resolve object, each object is inspectable for properties and functions.


Resolve
  Fusion()                                        --> Fusion             # Returns the Fusion object. Starting point for Fusion scripts.
  GetMediaStorage()                               --> MediaStorage       # Returns media storage object to query and act on media locations.
  GetProjectManager()                             --> ProjectManager     # Returns project manager object for currently open database.
  OpenPage(pageName)                              --> None               # Switches to indicated page in DaVinci Resolve. Input can be one of ("media", "edit", "fusion", "color", "fairlight", "deliver").
ProjectManager
  CreateProject(projectName)                      --> Project            # Creates and returns a project if projectName (text) is unique, and None if it is not.
  LoadProject(projectName)                        --> Project            # Loads and returns the project with name = projectName (text) if there is a match found, and None if there is no matching Project.
  GetCurrentProject()                             --> Project            # Returns the currently loaded Resolve project.
  SaveProject()                                   --> Bool               # Saves the currently loaded project with its own name. Returns True if successful.
  CreateFolder(folderName)                        --> Bool               # Creates a folder if folderName (text) is unique.
  GetProjectsInCurrentFolder()                    --> [project names...] # Returns an array of project names in current folder.
  GetFoldersInCurrentFolder()                     --> [folder names...]  # Returns an array of folder names in current folder.
  GotoRootFolder()                                --> Bool               # Opens root folder in database.
  GotoParentFolder()                              --> Bool               # Opens parent folder of current folder in database if current folder has parent.
  OpenFolder(folderName)                          --> Bool               # Opens folder under given name.
  ImportProject(filePath)                         --> Bool               # Imports a project under given file path. Returns true in case of success.
  ExportProject(projectName, filePath)            --> Bool               # Exports a project based on given name into provided file path. Returns true in case of success.
  RestoreProject(filePath)                        --> Bool               # Restores a project under given backup file path. Returns true in case of success.
Project
  GetMediaPool()                                  --> MediaPool          # Returns the Media Pool object.
  GetTimelineCount()                              --> int                # Returns the number of timelines currently present in the project.
  GetTimelineByIndex(idx)                         --> Timeline           # Returns timeline at the given index, 1 <= idx <= project.GetTimelineCount()
  GetCurrentTimeline()                            --> Timeline           # Returns the currently loaded timeline.
  SetCurrentTimeline(timeline)                    --> Bool               # Sets given timeline as current timeline for the project. Returns True if successful.
  GetName()                                       --> string             # Returns project name.
  SetName(projectName)                            --> Bool               # Sets project name if given projectname (text) is unique.
  GetPresets()                                    --> [presets...]       # Returns a table of presets and their information.
  SetPreset(presetName)                           --> Bool               # Sets preset by given presetName (string) into project.
  GetRenderJobs()                                 --> [render jobs...]   # Returns a table of render jobs and their information.
  GetRenderPresets()                              --> [presets...]       # Returns a table of render presets and their information.
  StartRendering(index1, index2, ...)             --> Bool               # Starts rendering for given render jobs based on their indices. If no parameter is given rendering would start for all render jobs.
  StartRendering([idxs...])                       --> Bool               # Starts rendering for given render jobs based on their indices. If no parameter is given rendering would start for all render jobs.
  StopRendering()                                 --> None               # Stops rendering for all render jobs.
  IsRenderingInProgress()                         --> Bool               # Returns true is rendering is in progress.
  AddRenderJob()                                  --> Bool               # Adds render job to render queue.
  DeleteRenderJobByIndex(idx)                     --> Bool               # Deletes render job based on given job index (int).
  DeleteAllRenderJobs()                           --> Bool               # Deletes all render jobs.
  LoadRenderPreset(presetName)                    --> Bool               # Sets a preset as current preset for rendering if presetName (text) exists.
  SaveAsNewRenderPreset(presetName)               --> Bool               # Creates a new render preset by given name if presetName(text) is unique.
  SetRenderSettings([settings map])               --> Bool               # Sets given settings for rendering. Settings map is a map, keys of map are: "SelectAllFrames", "MarkIn", "MarkOut", "TargetDir", "CustomName".
  GetRenderJobStatus(idx)                         --> [status info]      # Returns job status and completion rendering percentage of the job by given job index (int).
  GetSetting(settingName)                         --> string             # Returns setting value by given settingName (string) if the setting exist. With empty settingName the function returns a full list of settings.
  SetSetting(settingName, settingValue)           --> Bool               # Sets project setting base on given name (string) and value (string).
  GetRenderFormats()                              --> [render formats...]# Returns a list of available render formats.
  GetRenderCodecs(renderFormat)                   --> [render codecs...] # Returns a list of available codecs for given render format (string).
  GetCurrentRenderFormatAndCodec()                --> [format, codec]    # Returns currently selected render format and render codec.
  SetCurrentRenderFormatAndCodec(format, codec)   --> Bool               # Sets given render format (string) and render codec (string) as options for rendering.
MediaStorage
  GetMountedVolumes()                             --> [paths...]         # Returns an array of folder paths corresponding to mounted volumes displayed in Resolve’s Media Storage.
  GetSubFolders(folderPath)                       --> [paths...]         # Returns an array of folder paths in the given absolute folder path. 
  GetFiles(folderPath)                            --> [paths...]         # Returns an array of media and file listings in the given absolute folder path. Note that media listings may be logically consolidated entries.
  RevealInStorage(path)                           --> None               # Expands and displays a given file/folder path in Resolve’s Media Storage.
  AddItemsToMediaPool(item1, item2, ...)          --> [clips...]         # Adds specified file/folder paths from Media Store into current Media Pool folder. Input is one or more file/folder paths.
  AddItemsToMediaPool([items...])                 --> [clips...]         # Adds specified file/folder paths from Media Store into current Media Pool folder. Input is an array of file/folder paths.
MediaPool
  GetRootFolder()                                 --> Folder             # Returns the root Folder of Media Pool
  AddSubFolder(folder, name)                      --> Folder             # Adds a new subfolder under specified Folder object with the given name.
  CreateEmptyTimeline(name)                       --> Timeline           # Adds a new timeline with given name.
  AppendToTimeline(clip1, clip2...)               --> Bool               # Appends specified MediaPoolItem objects in the current timeline. Returns True if successful.
  AppendToTimeline([clips])                       --> Bool               # Appends specified MediaPoolItem objects in the current timeline. Returns True if successful.
  CreateTimelineFromClips(name, clip1, clip2, ...)--> Timeline           # Creates a new timeline with specified name, and appends the specified MediaPoolItem objects.
  CreateTimelineFromClips(name, [clips])          --> Timeline           # Creates a new timeline with specified name, and appends the specified MediaPoolItem objects.
  ImportTimelineFromFile(filePath)                --> Timeline           # Creates timeline based on parameters within given file.
  GetCurrentFolder()                              --> Folder             # Returns currently selected Folder.
  SetCurrentFolder(Folder)                        --> Bool               # Sets current folder by given Folder.
Folder
  GetClips()                                      --> [clips...]         # Returns a list of clips (items) within the folder.
  GetName()                                       --> string             # Returns user-defined name of the folder.
  GetSubFolders()                                 --> [folders...]       # Returns a list of subfolders in the folder.
MediaPoolItem
  GetMetadata(metadataType)                       --> [[types],[values]] # Returns a value of metadataType. If parameter is not specified returns all set metadata parameters.
  SetMetadata(metadataType, metadataValue)        --> Bool               # Sets metadata by given type and value. Returns True if successful.
  GetMediaId()                                    --> string             # Returns a unique ID name related to MediaPoolItem.
  AddMarker(frameId, color, name, note, duration) --> Bool               # Creates a new marker at given frameId position and with given marker information.
  GetMarkers()                                    --> [markers...]       # Returns a list of all markers and their information.
  AddFlag(color)                                  --> Bool               # Adds a flag with given color (text).
  GetFlags()                                      --> [colors...]        # Returns a list of flag colors assigned to the item.
  GetClipColor()                                  --> string             # Returns an item color as a string.
  GetClipProperty(propertyName)                   --> [[types],[values]] # Returns property value related to the item based on given propertyName (string). if propertyName is empty then it returns a full list of properties.
  SetClipProperty(propertyName, propertyValue)    --> Bool               # Sets into given propertyName (string) propertyValue (string).
Timeline
  GetName()                                       --> string             # Returns user-defined name of the timeline.
  SetName(timelineName)                           --> Bool               # Sets timeline name is timelineName (text) is unique.
  GetStartFrame()                                 --> int                # Returns frame number at the start of timeline.
  GetEndFrame()                                   --> int                # Returns frame number at the end of timeline.
  GetTrackCount(trackType)                        --> int                # Returns a number of track based on specified track type ("audio", "video" or "subtitle").
  GetItemsInTrack(trackType, index)               --> [items...]         # Returns an array of Timeline items on the video or audio track (based on trackType) at specified index. 1 <= index <= GetTrackCount(trackType).
  AddMarker(frameId, color, name, note, duration) --> Bool               # Creates a new marker at given frameId position and with given marker information.
  GetMarkers()                                    --> [markers...]       # Returns a list of all markers and their information.
  ApplyGradeFromDRX(path, gradeMode, item1, item2, ...)--> Bool          # Loads a still from given file path (string) and applies grade to Timeline Items with gradeMode (int): 0 - "No keyframes", 1 - "Source Timecode aligned", 2 - "Start Frames aligned".
  ApplyGradeFromDRX(path, gradeMode, [items])     --> Bool               # Loads a still from given file path (string) and applies grade to Timeline Items with gradeMode (int): 0 - "No keyframes", 1 - "Source Timecode aligned", 2 - "Start Frames aligned".
  GetCurrentTimecode()                            --> string             # Returns a string representing a timecode for current position of the timeline, while on Cut, Edit, Color and Deliver page.
  GetCurrentVideoItem()                           --> item               # Returns current video timeline item.
  GetCurrentClipThumbnailImage()                  --> [width, height, format, data]    # Returns raw thumbnail image data (This image data is encoded in base 64 format and the image format is RGB 8 bit) for the current media in the Color Page in the format of dictionary (in Python) and table (in Lua). Information return are "width", "height", "format" and "data". Example is provided in 6_get_current_media_thumbnail.py in Example folder.
TimelineItem
  GetName()                                       --> string             # Returns a name of the item.
  GetDuration()                                   --> int                # Returns a duration of item.
  GetEnd()                                        --> int                # Returns a position of end frame.
  GetFusionCompCount()                            --> int                # Returns the number of Fusion compositions associated with the timeline item.
  GetFusionCompByIndex(compIndex)                 --> fusionComp         # Returns Fusion composition object based on given index. 1 <= compIndex <= timelineItem.GetFusionCompCount()
  GetFusionCompNames()                            --> [names...]         # Returns a list of Fusion composition names associated with the timeline item.
  GetFusionCompByName(compName)                   --> fusionComp         # Returns Fusion composition object based on given name.
  GetLeftOffset()                                 --> int                # Returns a maximum extension by frame for clip from left side.
  GetRightOffset()                                --> int                # Returns a maximum extension by frame for clip from right side.
  GetStart()                                      --> int                # Returns a position of first frame.
  AddMarker(frameId, color, name, note, duration) --> Bool               # Creates a new marker at given frameId position and with given marker information.
  GetMarkers()                                    --> [markers...]       # Returns a list of all markers and their information.
  GetFlags()                                      --> [colors...]        # Returns a list of flag colors assigned to the item.
  GetClipColor()                                  --> string             # Returns an item color as a string.
  AddFusionComp()                                 --> fusionComp         # Adds a new Fusion composition associated with the timeline item.
  ImportFusionComp(path)                          --> fusionComp         # Imports Fusion composition from given file path by creating and adding a new composition for the item.
  ExportFusionComp(path, compIndex)               --> Bool               # Exports Fusion composition based on given index into provided file name path.
  DeleteFusionCompByName(compName)                --> Bool               # Deletes Fusion composition by provided name.
  LoadFusionCompByName(compName)                  --> fusionComp         # Loads Fusion composition by provided name and sets it as active composition.
  RenameFusionCompByName(oldName, newName)        --> Bool               # Renames Fusion composition by provided name with new given name.
  AddVersion(versionName, versionType)            --> Bool               # Adds a new Version associated with the timeline item. versionType: 0 - local, 1 - remote.
  DeleteVersionByName(versionName, versionType)   --> Bool               # Deletes Version by provided name. versionType: 0 - local, 1 - remote.
  LoadVersionByName(versionName, versionType)     --> Bool               # Loads Version by provided name and sets it as active Version. versionType: 0 - local, 1 - remote.
  RenameVersionByName(oldName, newName, versionType)--> Bool             # Renames Version by provided name with new given name. versionType: 0 - local, 1 - remote.
  GetMediaPoolItem()                              --> MediaPoolItem      # Returns a corresponding to the timeline item media pool item if it exists.
  GetVersionNames(versionType)                    --> [strings...]       # Returns a list of version names by provided versionType: 0 - local, 1 - remote.
  GetStereoConvergenceValues()                    --> [offset, value]    # Returns a table of keyframe offsets and respective convergence values
  GetStereoLeftFloatingWindowParams()             --> [offset, value]    # For the LEFT eye -> returns a table of keyframe offsets and respective floating window params. Value at particular offset includes the left, right, top and bottom floating window values
  GetStereoRightFloatingWindowParams()            --> [offset, value]    # For the RIGHT eye -> returns a table of keyframe offsets and respective floating window params. Value at particular offset includes the left, right, top and bottom floating window values
