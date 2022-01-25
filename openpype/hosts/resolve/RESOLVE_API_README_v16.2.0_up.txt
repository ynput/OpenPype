Updated as of 20 October 2020
-----------------------------
In this package, you will find a brief introduction to the Scripting API for DaVinci Resolve Studio. Apart from this README.txt file, this package contains folders containing the basic import
modules for scripting access (DaVinciResolve.py) and some representative examples.

From v16.2.0 onwards, the nodeIndex parameters accepted by SetLUT() and SetCDL() are 1-based instead of 0-based, i.e. 1 <= nodeIndex <= total number of nodes.


Overview
--------
As with Blackmagic Design Fusion scripts, user scripts written in Lua and Python programming languages are supported. By default, scripts can be invoked from the Console window in the Fusion page,
or via command line. This permission can be changed in Resolve Preferences, to be only from Console, or to be invoked from the local network. Please be aware of the security implications when
allowing scripting access from outside of the Resolve application.


Prerequisites
-------------
DaVinci Resolve scripting requires one of the following to be installed (for all users):

    Lua 5.1
    Python 2.7 64-bit
    Python 3.6 64-bit


Using a script
--------------
DaVinci Resolve needs to be running for a script to be invoked.

For a Resolve script to be executed from an external folder, the script needs to know of the API location.
You may need to set the these environment variables to allow for your Python installation to pick up the appropriate dependencies as shown below:

    Mac OS X:
    RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
    RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
    PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"

    Windows:
    RESOLVE_SCRIPT_API="%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
    RESOLVE_SCRIPT_LIB="C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
    PYTHONPATH="%PYTHONPATH%;%RESOLVE_SCRIPT_API%\Modules\"

    Linux:
    RESOLVE_SCRIPT_API="/opt/resolve/Developer/Scripting"
    RESOLVE_SCRIPT_LIB="/opt/resolve/libs/Fusion/fusionscript.so"
    PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"
    (Note: For standard ISO Linux installations, the path above may need to be modified to refer to /home/resolve instead of /opt/resolve)

As with Fusion scripts, Resolve scripts can also be invoked via the menu and the Console.

On startup, DaVinci Resolve scans the subfolders in the directories shown below and enumerates the scripts found in the Workspace application menu under Scripts.
Place your script under Utility to be listed in all pages, under Comp or Tool to be available in the Fusion page or under folders for individual pages (Edit, Color or Deliver). Scripts under Deliver are additionally listed under render jobs.
Placing your script here and invoking it from the menu is the easiest way to use scripts.
    Mac OS X:
      - All users: /Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts
      - Specific user:  /Users/<UserName>/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts
    Windows:
      - All users: %PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Fusion\Scripts
      - Specific user: %APPDATA%\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts
    Linux:
      - All users: /opt/resolve/Fusion/Scripts  (or /home/resolve/Fusion/Scripts/ depending on installation)
      - Specific user: $HOME/.local/share/DaVinciResolve/Fusion/Scripts

The interactive Console window allows for an easy way to execute simple scripting commands, to query or modify properties, and to test scripts. The console accepts commands in Python 2.7, Python 3.6
and Lua and evaluates and executes them immediately. For more information on how to use the Console, please refer to the DaVinci Resolve User Manual.

This example Python script creates a simple project:
    #!/usr/bin/env python
    import DaVinciResolveScript as dvr_script
    resolve = dvr_script.scriptapp("Resolve")
    fusion = resolve.Fusion()
    projectManager = resolve.GetProjectManager()
    projectManager.CreateProject("Hello World")

The resolve object is the fundamental starting point for scripting via Resolve. As a native object, it can be inspected for further scriptable properties - using table iteration and "getmetatable"
in Lua and dir, help etc in Python (among other methods). A notable scriptable object above is fusion - it allows access to all existing Fusion scripting functionality.


Running DaVinci Resolve in headless mode
----------------------------------------
DaVinci Resolve can be launched in a headless mode without the user interface using the -nogui command line option. When DaVinci Resolve is launched using this option, the user interface is disabled.
However, the various scripting APIs will continue to work as expected.


Basic Resolve API
-----------------
Some commonly used API functions are described below (*). As with the resolve object, each object is inspectable for properties and functions.

Resolve
  Fusion()                                        --> Fusion             # Returns the Fusion object. Starting point for Fusion scripts.
  GetMediaStorage()                               --> MediaStorage       # Returns the media storage object to query and act on media locations.
  GetProjectManager()                             --> ProjectManager     # Returns the project manager object for currently open database.
  OpenPage(pageName)                              --> None               # Switches to indicated page in DaVinci Resolve. Input can be one of ("media", "cut", "edit", "fusion", "color", "fairlight", "deliver").
  GetProductName()                                --> string             # Returns product name.
  GetVersion()                                    --> [version fields]   # Returns list of product version fields in [major, minor, patch, build, suffix] format.
  GetVersionString()                              --> string             # Returns product version in "major.minor.patch[suffix].build" format.

ProjectManager
  CreateProject(projectName)                      --> Project            # Creates and returns a project if projectName (string) is unique, and None if it is not.
  DeleteProject(projectName)                      --> Bool               # Delete project in the current folder if not currently loaded
  LoadProject(projectName)                        --> Project            # Loads and returns the project with name = projectName (string) if there is a match found, and None if there is no matching Project.
  GetCurrentProject()                             --> Project            # Returns the currently loaded Resolve project.
  SaveProject()                                   --> Bool               # Saves the currently loaded project with its own name. Returns True if successful.
  CloseProject(project)                           --> Bool               # Closes the specified project without saving.
  CreateFolder(folderName)                        --> Bool               # Creates a folder if folderName (string) is unique.
  DeleteFolder(folderName)                        --> Bool               # Deletes the specified folder if it exists. Returns True in case of success.
  GetProjectListInCurrentFolder()                 --> [project names...] # Returns a list of project names in current folder.
  GetFolderListInCurrentFolder()                  --> [folder names...]  # Returns a list of folder names in current folder.
  GotoRootFolder()                                --> Bool               # Opens root folder in database.
  GotoParentFolder()                              --> Bool               # Opens parent folder of current folder in database if current folder has parent.
  GetCurrentFolder()                              --> string             # Returns the current folder name.
  OpenFolder(folderName)                          --> Bool               # Opens folder under given name.
  ImportProject(filePath)                         --> Bool               # Imports a project from the file path provided. Returns True if successful.
  ExportProject(projectName, filePath, withStillsAndLUTs=True) --> Bool  # Exports project to provided file path, including stills and LUTs if withStillsAndLUTs is True (enabled by default). Returns True in case of success.
  RestoreProject(filePath)                        --> Bool               # Restores a project from the file path provided. Returns True if successful.
  GetCurrentDatabase()                            --> {dbInfo}           # Returns a dictionary (with keys 'DbType', 'DbName' and optional 'IpAddress') corresponding to the current database connection
  GetDatabaseList()                               --> [{dbInfo}]         # Returns a list of dictionary items (with keys 'DbType', 'DbName' and optional 'IpAddress') corresponding to all the databases added to Resolve
  SetCurrentDatabase({dbInfo})                    --> Bool               # Switches current database connection to the database specified by the keys below, and closes any open project.
                                                                         # 'DbType': 'Disk' or 'PostgreSQL' (string)
                                                                         # 'DbName': database name (string)
                                                                         # 'IpAddress': IP address of the PostgreSQL server (string, optional key - defaults to '127.0.0.1')

Project
  GetMediaPool()                                  --> MediaPool          # Returns the Media Pool object.
  GetTimelineCount()                              --> int                # Returns the number of timelines currently present in the project.
  GetTimelineByIndex(idx)                         --> Timeline           # Returns timeline at the given index, 1 <= idx <= project.GetTimelineCount()
  GetCurrentTimeline()                            --> Timeline           # Returns the currently loaded timeline.
  SetCurrentTimeline(timeline)                    --> Bool               # Sets given timeline as current timeline for the project. Returns True if successful.
  GetName()                                       --> string             # Returns project name.
  SetName(projectName)                            --> Bool               # Sets project name if given projectname (string) is unique.
  GetPresetList()                                 --> [presets...]       # Returns a list of presets and their information.
  SetPreset(presetName)                           --> Bool               # Sets preset by given presetName (string) into project.
  AddRenderJob()                                  --> string             # Adds a render job based on current render settings to the render queue. Returns a unique job id (string) for the new render job.
  DeleteRenderJob(jobId)                          --> Bool               # Deletes render job for input job id (string).
  DeleteAllRenderJobs()                           --> Bool               # Deletes all render jobs in the queue.
  GetRenderJobList()                              --> [render jobs...]   # Returns a list of render jobs and their information.
  GetRenderPresetList()                           --> [presets...]       # Returns a list of render presets and their information.
  StartRendering(jobId1, jobId2, ...)             --> Bool               # Starts rendering jobs indicated by the input job ids.
  StartRendering([jobIds...], isInteractiveMode=False)    --> Bool       # Starts rendering jobs indicated by the input job ids.
                                                                         # The optional "isInteractiveMode", when set, enables error feedback in the UI during rendering.
  StartRendering(isInteractiveMode=False)                 --> Bool       # Starts rendering all queued render jobs.
                                                                         # The optional "isInteractiveMode", when set, enables error feedback in the UI during rendering.
  StopRendering()                                 --> None               # Stops any current render processes.
  IsRenderingInProgress()                         --> Bool               # Returns True if rendering is in progress.
  LoadRenderPreset(presetName)                    --> Bool               # Sets a preset as current preset for rendering if presetName (string) exists.
  SaveAsNewRenderPreset(presetName)               --> Bool               # Creates new render preset by given name if presetName(string) is unique.
  SetRenderSettings({settings})                   --> Bool               # Sets given settings for rendering. Settings is a dict, with support for the keys:
                                                                         # "SelectAllFrames": Bool
                                                                         # "MarkIn": int
                                                                         # "MarkOut": int
                                                                         # "TargetDir": string
                                                                         # "CustomName": string
                                                                         # "UniqueFilenameStyle": 0 - Prefix, 1 - Suffix.
                                                                         # "ExportVideo": Bool
                                                                         # "ExportAudio": Bool
                                                                         # "FormatWidth": int
                                                                         # "FormatHeight": int
                                                                         # "FrameRate": float (examples: 23.976, 24)
                                                                         # "PixelAspectRatio": string (for SD resolution: "16_9" or "4_3") (other resolutions: "square" or "cinemascope")
                                                                         # "VideoQuality" possible values for current codec (if applicable):
                                                                         #    0 (int) - will set quality to automatic
                                                                         #    [1 -> MAX] (int) - will set input bit rate
                                                                         #    ["Least", "Low", "Medium", "High", "Best"] (String) - will set input quality level
                                                                         # "AudioCodec": string (example: "aac")
                                                                         # "AudioBitDepth": int
                                                                         # "AudioSampleRate": int
                                                                         # "ColorSpaceTag" : string (example: "Same as Project", "AstroDesign")
                                                                         # "GammaTag" : string (example: "Same as Project", "ACEScct")
  GetRenderJobStatus(jobId)                       --> {status info}      # Returns a dict with job status and completion percentage of the job by given jobId (string).
  GetSetting(settingName)                         --> string             # Returns value of project setting (indicated by settingName, string). Check the section below for more information.
  SetSetting(settingName, settingValue)           --> Bool               # Sets the project setting (indicated by settingName, string) to the value (settingValue, string). Check the section below for more information.
  GetRenderFormats()                              --> {render formats..} # Returns a dict (format -> file extension) of available render formats.
  GetRenderCodecs(renderFormat)                   --> {render codecs...} # Returns a dict (codec description -> codec name) of available codecs for given render format (string).
  GetCurrentRenderFormatAndCodec()                --> {format, codec}    # Returns a dict with currently selected format 'format' and render codec 'codec'.
  SetCurrentRenderFormatAndCodec(format, codec)   --> Bool               # Sets given render format (string) and render codec (string) as options for rendering.
  GetCurrentRenderMode()                          --> int                # Returns the render mode: 0 - Individual clips, 1 - Single clip.
  SetCurrentRenderMode(renderMode)                --> Bool               # Sets the render mode. Specify renderMode = 0 for Individual clips, 1 for Single clip.
  GetRenderResolutions(format, codec)             --> [{Resolution}]     # Returns list of resolutions applicable for the given render format (string) and render codec (string). Returns full list of resolutions if no argument is provided. Each element in the list is a dictionary with 2 keys "Width" and "Height".
  RefreshLUTList()                                --> Bool               # Refreshes LUT List

MediaStorage
  GetMountedVolumeList()                          --> [paths...]         # Returns list of folder paths corresponding to mounted volumes displayed in Resolve’s Media Storage.
  GetSubFolderList(folderPath)                    --> [paths...]         # Returns list of folder paths in the given absolute folder path.
  GetFileList(folderPath)                         --> [paths...]         # Returns list of media and file listings in the given absolute folder path. Note that media listings may be logically consolidated entries.
  RevealInStorage(path)                           --> None               # Expands and displays given file/folder path in Resolve’s Media Storage.
  AddItemListToMediaPool(item1, item2, ...)       --> [clips...]         # Adds specified file/folder paths from Media Storage into current Media Pool folder. Input is one or more file/folder paths. Returns a list of the MediaPoolItems created.
  AddItemListToMediaPool([items...])              --> [clips...]         # Adds specified file/folder paths from Media Storage into current Media Pool folder. Input is an array of file/folder paths. Returns a list of the MediaPoolItems created.
  AddClipMattesToMediaPool(MediaPoolItem, [paths], stereoEye) --> Bool   # Adds specified media files as mattes for the specified MediaPoolItem. StereoEye is an optional argument for specifying which eye to add the matte to for stereo clips ("left" or "right"). Returns True if successful.
  AddTimelineMattesToMediaPool([paths])           --> [MediaPoolItems]   # Adds specified media files as timeline mattes in current media pool folder. Returns a list of created MediaPoolItems.

MediaPool
  GetRootFolder()                                 --> Folder             # Returns root Folder of Media Pool
  AddSubFolder(folder, name)                      --> Folder             # Adds new subfolder under specified Folder object with the given name.
  CreateEmptyTimeline(name)                       --> Timeline           # Adds new timeline with given name.
  AppendToTimeline(clip1, clip2, ...)             --> Bool               # Appends specified MediaPoolItem objects in the current timeline. Returns True if successful.
  AppendToTimeline([clips])                       --> Bool               # Appends specified MediaPoolItem objects in the current timeline. Returns True if successful.
  AppendToTimeline([{clipInfo}, ...])             --> Bool               # Appends list of clipInfos specified as dict of "mediaPoolItem", "startFrame" (int), "endFrame" (int).
  CreateTimelineFromClips(name, clip1, clip2,...) --> Timeline           # Creates new timeline with specified name, and appends the specified MediaPoolItem objects.
  CreateTimelineFromClips(name, [clips])          --> Timeline           # Creates new timeline with specified name, and appends the specified MediaPoolItem objects.
  CreateTimelineFromClips(name, [{clipInfo}])     --> Timeline           # Creates new timeline with specified name, appending the list of clipInfos specified as a dict of "mediaPoolItem", "startFrame" (int), "endFrame" (int).
  ImportTimelineFromFile(filePath, {importOptions}) --> Timeline         # Creates timeline based on parameters within given file and optional importOptions dict, with support for the keys:
                                                                         # "timelineName": string, specifies the name of the timeline to be created
                                                                         # "importSourceClips": Bool, specifies whether source clips should be imported, True by default
                                                                         # "sourceClipsPath": string, specifies a filesystem path to search for source clips if the media is inaccessible in their original path and if "importSourceClips" is True
                                                                         # "sourceClipsFolders": List of Media Pool folder objects to search for source clips if the media is not present in current folder and if "importSourceClips" is False
  GetCurrentFolder()                              --> Folder             # Returns currently selected Folder.
  SetCurrentFolder(Folder)                        --> Bool               # Sets current folder by given Folder.
  DeleteClips([clips])                            --> Bool               # Deletes specified clips or timeline mattes in the media pool
  DeleteFolders([subfolders])                     --> Bool               # Deletes specified subfolders in the media pool
  MoveClips([clips], targetFolder)                --> Bool               # Moves specified clips to target folder.
  MoveFolders([folders], targetFolder)            --> Bool               # Moves specified folders to target folder.
  GetClipMatteList(MediaPoolItem)                 --> [paths]            # Get mattes for specified MediaPoolItem, as a list of paths to the matte files.
  GetTimelineMatteList(Folder)                    --> [MediaPoolItems]   # Get mattes in specified Folder, as list of MediaPoolItems.
  DeleteClipMattes(MediaPoolItem, [paths])        --> Bool               # Delete mattes based on their file paths, for specified MediaPoolItem. Returns True on success.
  RelinkClips([MediaPoolItem], folderPath)        --> Bool               # Update the folder location of specified media pool clips with the specified folder path.
  UnlinkClips([MediaPoolItem])                    --> Bool               # Unlink specified media pool clips.
  ImportMedia([items...])                         --> [MediaPoolItems]   # Imports specified file/folder paths into current Media Pool folder. Input is an array of file/folder paths. Returns a list of the MediaPoolItems created.
  ExportMetadata(fileName, [clips])               --> Bool               # Exports metadata of specified clips to 'fileName' in CSV format.
                                                                         # If no clips are specified, all clips from media pool will be used.

Folder
  GetClipList()                                   --> [clips...]         # Returns a list of clips (items) within the folder.
  GetName()                                       --> string             # Returns the media folder name.
  GetSubFolderList()                              --> [folders...]       # Returns a list of subfolders in the folder.

MediaPoolItem
  GetName()                                       --> string             # Returns the clip name.
  GetMetadata(metadataType=None)                  --> string|dict        # Returns the metadata value for the key 'metadataType'.
                                                                         # If no argument is specified, a dict of all set metadata properties is returned.
  SetMetadata(metadataType, metadataValue)        --> Bool               # Sets the given metadata to metadataValue (string). Returns True if successful.
  GetMediaId()                                    --> string             # Returns the unique ID for the MediaPoolItem.
  AddMarker(frameId, color, name, note, duration, --> Bool               # Creates a new marker at given frameId position and with given marker information. 'customData' is optional and helps to attach user specific data to the marker.
            customData)
  GetMarkers()                                    --> {markers...}       # Returns a dict (frameId -> {information}) of all markers and dicts with their information.
                                                                         # Example of output format: {96.0: {'color': 'Green', 'duration': 1.0, 'note': '', 'name': 'Marker 1', 'customData': ''}, ...}
                                                                         # In the above example - there is one 'Green' marker at offset 96 (position of the marker)
  GetMarkerByCustomData(customData)               --> {markers...}       # Returns marker {information} for the first matching marker with specified customData.
  UpdateMarkerCustomData(frameId, customData)     --> Bool               # Updates customData (string) for the marker at given frameId position. CustomData is not exposed via UI and is useful for scripting developer to attach any user specific data to markers.
  GetMarkerCustomData(frameId)                    --> string             # Returns customData string for the marker at given frameId position.
  DeleteMarkersByColor(color)                     --> Bool               # Delete all markers of the specified color from the media pool item. "All" as argument deletes all color markers.
  DeleteMarkerAtFrame(frameNum)                   --> Bool               # Delete marker at frame number from the media pool item.
  DeleteMarkerByCustomData(customData)            --> Bool               # Delete first matching marker with specified customData.
  AddFlag(color)                                  --> Bool               # Adds a flag with given color (string).
  GetFlagList()                                   --> [colors...]        # Returns a list of flag colors assigned to the item.
  ClearFlags(color)                               --> Bool               # Clears the flag of the given color if one exists. An "All" argument is supported and clears all flags.
  GetClipColor()                                  --> string             # Returns the item color as a string.
  SetClipColor(colorName)                         --> Bool               # Sets the item color based on the colorName (string).
  ClearClipColor()                                --> Bool               # Clears the item color.
  GetClipProperty(propertyName=None)              --> string|dict        # Returns the property value for the key 'propertyName'.
                                                                         # If no argument is specified, a dict of all clip properties is returned. Check the section below for more information.
  SetClipProperty(propertyName, propertyValue)    --> Bool               # Sets the given property to propertyValue (string). Check the section below for more information.
  LinkProxyMedia(propertyName)                    --> Bool               # Links proxy media (absolute path) with the current clip.
  UnlinkProxyMedia()                              --> Bool               # Unlinks any proxy media associated with clip.
  ReplaceClip(filePath)                           --> Bool               # Replaces the underlying asset and metadata of MediaPoolItem with the specified absolute clip path.

Timeline
  GetName()                                       --> string             # Returns the timeline name.
  SetName(timelineName)                           --> Bool               # Sets the timeline name if timelineName (string) is unique. Returns True if successful.
  GetStartFrame()                                 --> int                # Returns the frame number at the start of timeline.
  GetEndFrame()                                   --> int                # Returns the frame number at the end of timeline.
  GetTrackCount(trackType)                        --> int                # Returns the number of tracks for the given track type ("audio", "video" or "subtitle").
  GetItemListInTrack(trackType, index)            --> [items...]         # Returns a list of timeline items on that track (based on trackType and index). 1 <= index <= GetTrackCount(trackType).
  AddMarker(frameId, color, name, note, duration, --> Bool               # Creates a new marker at given frameId position and with given marker information. 'customData' is optional and helps to attach user specific data to the marker.
            customData)
  GetMarkers()                                    --> {markers...}       # Returns a dict (frameId -> {information}) of all markers and dicts with their information.
                                                                         # Example: a value of {96.0: {'color': 'Green', 'duration': 1.0, 'note': '', 'name': 'Marker 1', 'customData': ''}, ...} indicates a single green marker at timeline offset 96
  GetMarkerByCustomData(customData)               --> {markers...}       # Returns marker {information} for the first matching marker with specified customData.
  UpdateMarkerCustomData(frameId, customData)     --> Bool               # Updates customData (string) for the marker at given frameId position. CustomData is not exposed via UI and is useful for scripting developer to attach any user specific data to markers.
  GetMarkerCustomData(frameId)                    --> string             # Returns customData string for the marker at given frameId position.
  DeleteMarkersByColor(color)                     --> Bool               # Deletes all timeline markers of the specified color. An "All" argument is supported and deletes all timeline markers.
  DeleteMarkerAtFrame(frameNum)                   --> Bool               # Deletes the timeline marker at the given frame number.
  DeleteMarkerByCustomData(customData)            --> Bool               # Delete first matching marker with specified customData.
  ApplyGradeFromDRX(path, gradeMode, item1, item2, ...)--> Bool          # Loads a still from given file path (string) and applies grade to Timeline Items with gradeMode (int): 0 - "No keyframes", 1 - "Source Timecode aligned", 2 - "Start Frames aligned".
  ApplyGradeFromDRX(path, gradeMode, [items])     --> Bool               # Loads a still from given file path (string) and applies grade to Timeline Items with gradeMode (int): 0 - "No keyframes", 1 - "Source Timecode aligned", 2 - "Start Frames aligned".
  GetCurrentTimecode()                            --> string             # Returns a string timecode representation for the current playhead position, while on Cut, Edit, Color and Deliver pages.
  GetCurrentVideoItem()                           --> item               # Returns the current video timeline item.
  GetCurrentClipThumbnailImage()                  --> {thumbnailData}    # Returns a dict (keys "width", "height", "format" and "data") with data containing raw thumbnail image data (RGB 8-bit image data encoded in base64 format) for current media in the Color Page.
                                                                         # An example of how to retrieve and interpret thumbnails is provided in 6_get_current_media_thumbnail.py in the Examples folder.
  GetTrackName(trackType, trackIndex)             --> string             # Returns the track name for track indicated by trackType ("audio", "video" or "subtitle") and index. 1 <= trackIndex <= GetTrackCount(trackType).
  SetTrackName(trackType, trackIndex, name)       --> Bool               # Sets the track name (string) for track indicated by trackType ("audio", "video" or "subtitle") and index. 1 <= trackIndex <= GetTrackCount(trackType).
  DuplicateTimeline(timelineName)                 --> timeline           # Duplicates the timeline and returns the created timeline, with the (optional) timelineName, on success.
  CreateCompoundClip([timelineItems], {clipInfo}) --> timelineItem       # Creates a compound clip of input timeline items with an optional clipInfo map: {"startTimecode" : "00:00:00:00", "name" : "Compound Clip 1"}. It returns the created timeline item.
  CreateFusionClip([timelineItems])               --> timelineItem       # Creates a Fusion clip of input timeline items. It returns the created timeline item.
  Export(fileName, exportType, exportSubtype)     --> Bool               # Exports timeline to 'fileName' as per input exportType & exportSubtype format.
                                                                         # exportType can be one of the following constants:
                                                                         #   resolve.EXPORT_AAF
                                                                         #   resolve.EXPORT_DRT
                                                                         #   resolve.EXPORT_EDL
                                                                         #   resolve.EXPORT_FCP_7_XML
                                                                         #   resolve.EXPORT_FCPXML_1_3
                                                                         #   resolve.EXPORT_FCPXML_1_4
                                                                         #   resolve.EXPORT_FCPXML_1_5
                                                                         #   resolve.EXPORT_FCPXML_1_6
                                                                         #   resolve.EXPORT_FCPXML_1_7
                                                                         #   resolve.EXPORT_FCPXML_1_8
                                                                         #   resolve.EXPORT_HDR_10_PROFILE_A
                                                                         #   resolve.EXPORT_HDR_10_PROFILE_B
                                                                         #   resolve.EXPORT_TEXT_CSV
                                                                         #   resolve.EXPORT_TEXT_TAB
                                                                         #   resolve.EXPORT_DOLBY_VISION_VER_2_9
                                                                         #   resolve.EXPORT_DOLBY_VISION_VER_4_0
                                                                         # exportSubtype can be one of the following enums:
                                                                         #   resolve.EXPORT_NONE
                                                                         #   resolve.EXPORT_AAF_NEW
                                                                         #   resolve.EXPORT_AAF_EXISTING
                                                                         #   resolve.EXPORT_CDL
                                                                         #   resolve.EXPORT_SDL
                                                                         #   resolve.EXPORT_MISSING_CLIPS
                                                                         # Please note that exportSubType is a required parameter for resolve.EXPORT_AAF and resolve.EXPORT_EDL. For rest of the exportType, exportSubtype is ignored.
                                                                         # When exportType is resolve.EXPORT_AAF, valid exportSubtype values are resolve.EXPORT_AAF_NEW and resolve.EXPORT_AAF_EXISTING.
                                                                         # When exportType is resolve.EXPORT_EDL, valid exportSubtype values are resolve.EXPORT_CDL, resolve.EXPORT_SDL, resolve.EXPORT_MISSING_CLIPS and resolve.EXPORT_NONE.
                                                                         # Note: Replace 'resolve.' when using the constants above, if a different Resolve class instance name is used.
  GetSetting(settingName)                         --> string             # Returns value of timeline setting (indicated by settingName : string). Check the section below for more information.
  SetSetting(settingName, settingValue)           --> Bool               # Sets timeline setting (indicated by settingName : string) to the value (settingValue : string). Check the section below for more information.

TimelineItem
  GetName()                                       --> string             # Returns the item name.
  GetDuration()                                   --> int                # Returns the item duration.
  GetEnd()                                        --> int                # Returns the end frame position on the timeline.
  GetFusionCompCount()                            --> int                # Returns number of Fusion compositions associated with the timeline item.
  GetFusionCompByIndex(compIndex)                 --> fusionComp         # Returns the Fusion composition object based on given index. 1 <= compIndex <= timelineItem.GetFusionCompCount()
  GetFusionCompNameList()                         --> [names...]         # Returns a list of Fusion composition names associated with the timeline item.
  GetFusionCompByName(compName)                   --> fusionComp         # Returns the Fusion composition object based on given name.
  GetLeftOffset()                                 --> int                # Returns the maximum extension by frame for clip from left side.
  GetRightOffset()                                --> int                # Returns the maximum extension by frame for clip from right side.
  GetStart()                                      --> int                # Returns the start frame position on the timeline.
  AddMarker(frameId, color, name, note, duration, --> Bool               # Creates a new marker at given frameId position and with given marker information. 'customData' is optional and helps to attach user specific data to the marker.
            customData)
  GetMarkers()                                    --> {markers...}       # Returns a dict (frameId -> {information}) of all markers and dicts with their information.
                                                                         # Example: a value of {96.0: {'color': 'Green', 'duration': 1.0, 'note': '', 'name': 'Marker 1', 'customData': ''}, ...} indicates a single green marker at clip offset 96
  GetMarkerByCustomData(customData)               --> {markers...}       # Returns marker {information} for the first matching marker with specified customData.
  UpdateMarkerCustomData(frameId, customData)     --> Bool               # Updates customData (string) for the marker at given frameId position. CustomData is not exposed via UI and is useful for scripting developer to attach any user specific data to markers.
  GetMarkerCustomData(frameId)                    --> string             # Returns customData string for the marker at given frameId position.
  DeleteMarkersByColor(color)                     --> Bool               # Delete all markers of the specified color from the timeline item. "All" as argument deletes all color markers.
  DeleteMarkerAtFrame(frameNum)                   --> Bool               # Delete marker at frame number from the timeline item.
  DeleteMarkerByCustomData(customData)            --> Bool               # Delete first matching marker with specified customData.
  AddFlag(color)                                  --> Bool               # Adds a flag with given color (string).
  GetFlagList()                                   --> [colors...]        # Returns a list of flag colors assigned to the item.
  ClearFlags(color)                               --> Bool               # Clear flags of the specified color. An "All" argument is supported to clear all flags.
  GetClipColor()                                  --> string             # Returns the item color as a string.
  SetClipColor(colorName)                         --> Bool               # Sets the item color based on the colorName (string).
  ClearClipColor()                                --> Bool               # Clears the item color.
  AddFusionComp()                                 --> fusionComp         # Adds a new Fusion composition associated with the timeline item.
  ImportFusionComp(path)                          --> fusionComp         # Imports a Fusion composition from given file path by creating and adding a new composition for the item.
  ExportFusionComp(path, compIndex)               --> Bool               # Exports the Fusion composition based on given index to the path provided.
  DeleteFusionCompByName(compName)                --> Bool               # Deletes the named Fusion composition.
  LoadFusionCompByName(compName)                  --> fusionComp         # Loads the named Fusion composition as the active composition.
  RenameFusionCompByName(oldName, newName)        --> Bool               # Renames the Fusion composition identified by oldName.
  AddVersion(versionName, versionType)            --> Bool               # Adds a new color version for a video clipbased on versionType (0 - local, 1 - remote).
  DeleteVersionByName(versionName, versionType)   --> Bool               # Deletes a color version by name and versionType (0 - local, 1 - remote).
  LoadVersionByName(versionName, versionType)     --> Bool               # Loads a named color version as the active version. versionType: 0 - local, 1 - remote.
  RenameVersionByName(oldName, newName, versionType)--> Bool             # Renames the color version identified by oldName and versionType (0 - local, 1 - remote).
  GetVersionNameList(versionType)                 --> [names...]         # Returns a list of all color versions for the given versionType (0 - local, 1 - remote).
  GetMediaPoolItem()                              --> MediaPoolItem      # Returns the media pool item corresponding to the timeline item if one exists.
  GetStereoConvergenceValues()                    --> {keyframes...}     # Returns a dict (offset -> value) of keyframe offsets and respective convergence values.
  GetStereoLeftFloatingWindowParams()             --> {keyframes...}     # For the LEFT eye -> returns a dict (offset -> dict) of keyframe offsets and respective floating window params. Value at particular offset includes the left, right, top and bottom floating window values.
  GetStereoRightFloatingWindowParams()            --> {keyframes...}     # For the RIGHT eye -> returns a dict (offset -> dict) of keyframe offsets and respective floating window params. Value at particular offset includes the left, right, top and bottom floating window values.
  SetLUT(nodeIndex, lutPath)                      --> Bool               # Sets LUT on the node mapping the node index provided, 1 <= nodeIndex <= total number of nodes.
                                                                         # The lutPath can be an absolute path, or a relative path (based off custom LUT paths or the master LUT path).
                                                                         # The operation is successful for valid lut paths that Resolve has already discovered (see Project.RefreshLUTList).
  SetCDL([CDL map])                               --> Bool               # Keys of map are: "NodeIndex", "Slope", "Offset", "Power", "Saturation", where 1 <= NodeIndex <= total number of nodes.
                                                                         # Example python code - SetCDL({"NodeIndex" : "1", "Slope" : "0.5 0.4 0.2", "Offset" : "0.4 0.3 0.2", "Power" : "0.6 0.7 0.8", "Saturation" : "0.65"})
  AddTake(mediaPoolItem, startFrame=0, endFrame)=0    --> Bool           # Adds mediaPoolItem as a new take. Initializes a take selector for the timeline item if needed. By default, the whole clip is added. startFrame and endFrame can be specified as extents.
  GetSelectedTakeIndex()                          --> int                # Returns the index of the currently selected take, or 0 if the clip is not a take selector.
  GetTakesCount()                                 --> int                # Returns the number of takes in take selector, or 0 if the clip is not a take selector.
  GetTakeByIndex(idx)                             --> {takeInfo...}      # Returns a dict (keys "startFrame", "endFrame" and "mediaPoolItem") with take info for specified index.
  DeleteTakeByIndex(idx)                          --> Bool               # Deletes a take by index, 1 <= idx <= number of takes.
  SelectTakeByIndex(idx)                          --> Bool               # Selects a take by index, 1 <= idx <= number of takes.
  FinalizeTake()                                  --> Bool               # Finalizes take selection.
  CopyGrades([tgtTimelineItems])                  --> Bool               # Copies the current grade to all the items in tgtTimelineItems list. Returns True on success and False if any error occurred.


List and Dict Data Structures
-----------------------------
Beside primitive data types, Resolve's Python API mainly uses list and dict data structures. Lists are denoted by [ ... ] and dicts are denoted by { ... } above.
As Lua does not support list and dict data structures, the Lua API implements "list" as a table with indices, e.g. { [1] = listValue1, [2] = listValue2, ... }.
Similarly the Lua API implements "dict" as a table with the dictionary key as first element, e.g. { [dictKey1] = dictValue1, [dictKey2] = dictValue2, ... }.


Looking up Project and Clip properties
--------------------------------------
This section covers additional notes for the functions "Project:GetSetting", "Project:SetSetting", "Timeline:GetSetting", "Timeline:SetSetting", "MediaPoolItem:GetClipProperty" and
"MediaPoolItem:SetClipProperty". These functions are used to get and set properties otherwise available to the user through the Project Settings and the Clip Attributes dialogs.

The functions follow a key-value pair format, where each property is identified by a key (the settingName or propertyName parameter) and possesses a value (typically a text value). Keys and values are
designed to be easily correlated with parameter names and values in the Resolve UI. Explicitly enumerated values for some parameters are listed below.

Some properties may be read only - these include intrinsic clip properties like date created or sample rate, and properties that can be disabled in specific application contexts (e.g. custom colorspaces
in an ACES workflow, or output sizing parameters when behavior is set to match timeline)

Getting values:
Invoke "Project:GetSetting", "Timeline:GetSetting" or "MediaPoolItem:GetClipProperty" with the appropriate property key. To get a snapshot of all queryable properties (keys and values), you can call
"Project:GetSetting", "Timeline:GetSetting" or "MediaPoolItem:GetClipProperty" without parameters (or with a NoneType or a blank property key). Using specific keys to query individual properties will
be faster. Note that getting a property using an invalid key will return a trivial result.

Setting values:
Invoke "Project:SetSetting", "Timeline:SetSetting" or "MediaPoolItem:SetClipProperty" with the appropriate property key and a valid value. When setting a parameter, please check the return value to
ensure the success of the operation. You can troubleshoot the validity of keys and values by setting the desired result from the UI and checking property snapshots before and after the change.

The following Project properties have specifically enumerated values:
"superScale" - the property value is an enumerated integer between 0 and 3 with these meanings: 0=Auto, 1=no scaling, and 2, 3 and 4 represent the Super Scale multipliers 2x, 3x and 4x.
Affects:
• x = Project:GetSetting('superScale') and Project:SetSetting('superScale', x)

"timelineFrameRate" - the property value is one of the frame rates available to the user in project settings under "Timeline frame rate" option. Drop Frame can be configured for supported frame rates
                      by appending the frame rate with "DF", e.g. "29.97 DF" will enable drop frame and "29.97" will disable drop frame
Affects:
• x = Project:GetSetting('timelineFrameRate') and Project:SetSetting('timelineFrameRate', x)

The following Clip properties have specifically enumerated values:
"superScale" - the property value is an enumerated integer between 1 and 3 with these meanings: 1=no scaling, and 2, 3 and 4 represent the Super Scale multipliers 2x, 3x and 4x.
Affects:
• x = MediaPoolItem:GetClipProperty('Super Scale') and MediaPoolItem:SetClipProperty('Super Scale', x)


Deprecated Resolve API Functions
--------------------------------
The following API functions are deprecated.

ProjectManager
  GetProjectsInCurrentFolder()                    --> {project names...} # Returns a dict of project names in current folder.
  GetFoldersInCurrentFolder()                     --> {folder names...}  # Returns a dict of folder names in current folder.

Project
  GetPresets()                                    --> {presets...}       # Returns a dict of presets and their information.
  GetRenderJobs()                                 --> {render jobs...}   # Returns a dict of render jobs and their information.
  GetRenderPresets()                              --> {presets...}       # Returns a dict of render presets and their information.

MediaStorage
  GetMountedVolumes()                             --> {paths...}         # Returns a dict of folder paths corresponding to mounted volumes displayed in Resolve’s Media Storage.
  GetSubFolders(folderPath)                       --> {paths...}         # Returns a dict of folder paths in the given absolute folder path.
  GetFiles(folderPath)                            --> {paths...}         # Returns a dict of media and file listings in the given absolute folder path. Note that media listings may be logically consolidated entries.
  AddItemsToMediaPool(item1, item2, ...)          --> {clips...}         # Adds specified file/folder paths from Media Storage into current Media Pool folder. Input is one or more file/folder paths. Returns a dict of the MediaPoolItems created.
  AddItemsToMediaPool([items...])                 --> {clips...}         # Adds specified file/folder paths from Media Storage into current Media Pool folder. Input is an array of file/folder paths. Returns a dict of the MediaPoolItems created.

Folder
  GetClips()                                      --> {clips...}         # Returns a dict of clips (items) within the folder.
  GetSubFolders()                                 --> {folders...}       # Returns a dict of subfolders in the folder.

MediaPoolItem
  GetFlags()                                      --> {colors...}        # Returns a dict of flag colors assigned to the item.

Timeline
  GetItemsInTrack(trackType, index)               --> {items...}         # Returns a dict of Timeline items on the video or audio track (based on trackType) at specified

TimelineItem
  GetFusionCompNames()                            --> {names...}         # Returns a dict of Fusion composition names associated with the timeline item.
  GetFlags()                                      --> {colors...}        # Returns a dict of flag colors assigned to the item.
  GetVersionNames(versionType)                    --> {names...}         # Returns a dict of version names by provided versionType: 0 - local, 1 - remote.


Unsupported Resolve API Functions
---------------------------------
The following API (functions and paraameters) are no longer supported.

Project
  StartRendering(index1, index2, ...)             --> Bool               # Please use unique job ids (string) instead of indices.
  StartRendering([idxs...])                       --> Bool               # Please use unique job ids (string) instead of indices.
  DeleteRenderJobByIndex(idx)                     --> Bool               # Please use unique job ids (string) instead of indices.
  GetRenderJobStatus(idx)                         --> {status info}      # Please use unique job ids (string) instead of indices.
  GetSetting and SetSetting                       --> {}                 # settingName "videoMonitorUseRec601For422SDI" is no longer supported.
                                                                         # Please use "videoMonitorUseMatrixOverrideFor422SDI" and "videoMonitorMatrixOverrideFor422SDI" instead.
