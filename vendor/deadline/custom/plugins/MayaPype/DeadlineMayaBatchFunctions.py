from __future__ import print_function

import json
import os
import re
import subprocess

import maya.cmds
import maya.mel

# The version that Redshift fixed the render layer render setup override locking issue
# Prior versions will need to use the workaround in the unlockRenderSetupOverrides function
REDSHIFT_RENDER_SETUP_FIX_VERSION = (2, 5, 64)

def getCurrentRenderLayer():
    return maya.cmds.editRenderLayerGlobals( query=True, currentRenderLayer=True )

# A method mimicing the built-in mel function: 'renderLayerDisplayName', but first tries to see if it exists
def getRenderLayerDisplayName( layer_name ):
    if maya.mel.eval( 'exists renderLayerDisplayName' ):
        layer_name = maya.mel.eval( 'renderLayerDisplayName ' + layer_name )
    else:
        # renderLayerDisplayName doesn't exist, so we try to do it ourselves
        if layer_name == 'masterLayer':
            return layer_name

        if maya.cmds.objExists(layer_name) and maya.cmds.nodeType( layer_name ) == 'renderLayer':
            # Display name for default render layer
            if maya.cmds.getAttr( layer_name + '.identification' ) == 0:
                return 'masterLayer'

            # If Render Setup is used the corresponding Render Setup layer name should be used instead of the legacy render layer name.
            result = maya.cmds.listConnections( layer_name + '.msg', type='renderSetupLayer' )
            if result:
                return result[0]

    return layer_name

# remove_override_json_string is a json string consisting of a node as a key, with a list of attributes we want to unlock as the value
# ie. remove_override_json_string = '{ "defaultRenderGlobals": [ "animation", "startFrame", "endFrame" ] }'
def unlockRenderSetupOverrides( remove_overrides_json_string ):
    try:
        # Ensure we're in a version that HAS render setups
        import maya.app.renderSetup.model.renderSetup as renderSetup
    except ImportError:
        return

    # Ensure that the scene is actively using render setups and not the legacy layers
    if not maya.mel.eval( 'exists mayaHasRenderSetup' ) or not maya.mel.eval( 'mayaHasRenderSetup();' ):
        return

    # If the version of Redshift has the bug fix, bypass the overrides
    if not redshiftRequiresWorkaround():
        return

    remove_overrides = json.loads( remove_overrides_json_string )

    render_setup = renderSetup.instance()
    layers = render_setup.getRenderLayers()
    layers_to_unlock = [ layer for layer in layers if layer.name() != 'defaultRenderLayer' ]

    for render_layer in layers_to_unlock:
        print('Disabling Render Setup Overrides in "%s"' % render_layer.name())
        for collection in render_layer.getCollections():
            if type(collection) == maya.app.renderSetup.model.collection.RenderSettingsCollection:
                for override in collection.getOverrides():
                    if override.targetNodeName() in remove_overrides and override.attributeName() in remove_overrides[ override.targetNodeName() ]:
                        print( '    Disabling Override: %s.%s' % ( override.targetNodeName(), override.attributeName() ) )
                        override.setSelfEnabled( False )

def redshiftRequiresWorkaround():
    # Get the version of Redshift
    redshiftVersion = maya.cmds.pluginInfo( 'redshift4maya', query=True, version=True )
    redshiftVersion = tuple( int(version) for version in redshiftVersion.split('.') )
    # Check if the Redshift version is prior to the bug fix
    return redshiftVersion < REDSHIFT_RENDER_SETUP_FIX_VERSION


def performArnoldPathmapping( startFrame, endFrame, tempLocation=None ):
    """
    Performs pathmapping on all arnold standin files that are need for the current task
    :param startFrame: Start frame of the task
    :param endFrame:  End frame of the task
    :param tempLocation: The temporary location where all pathmapped files will be copied to. Only needs to be provided the first time this function is called.
    :return: Nothing
    """
    if tempLocation:
        performArnoldPathmapping.tempLocation = tempLocation
    else:
        if not performArnoldPathmapping.tempLocation:
            raise ValueError( "The first call made to performArnoldPathmapping must provided a tempLocation" )
    
    #a simple regex for finding frame numbers
    frameRE = re.compile( r'#+' )
    
    # Define a function that will be used when looping to replace padding with a 0 padded string.
    def __replaceHashesWithZeroPaddedFrame( frameNum, origFileName ):
        return frameRE.sub( lambda matchObj: str( frameNum ).zfill( len(matchObj.group(0)) ), origFileName )

    standInObjects = maya.cmds.ls( type="aiStandIn" )
    for standIn in standInObjects:
        try:
            # If we have already seen this node before then grab the settings that we need
            origDir, origFileName = performArnoldPathmapping.originalProperties[ standIn ]
        except KeyError:
            # If we have not seen this node before then store it's original path and update the path in the node to where we will be pathmapping the file.
            standinFile = maya.cmds.getAttr( standIn + ".dso" )

            if not standinFile or os.path.splitext( standinFile )[ 1 ].lower() != ".ass":
                # If the standinFile isn't set or isn't .ass file then we cannot pathmap it.
                continue

            origDir, origFileName = os.path.split( standinFile )
            standinTempLocation = os.path.join( performArnoldPathmapping.tempLocation, standIn )

            maya.cmds.setAttr( "%s.dso" % standIn, os.path.join( standinTempLocation, origFileName ), type="string" )
            #Create the Temp directory the first time we see a new standin
            if not os.path.isdir( standinTempLocation ):
                os.makedirs( standinTempLocation )

                performArnoldPathmapping.originalProperties[ standIn ] = (origDir, origFileName)

        for frame in range( startFrame, endFrame + 1 ):
            # evaluate the frame that the node is using (Normally it will be the same as the scene but it can be different)
            evalFrame = maya.cmds.getAttr( "%s.frameNumber" % standIn, time=frame )
            fileNameWithFrame = __replaceHashesWithZeroPaddedFrame( evalFrame, origFileName )

            # If we have already mapped this file then continue.
            if not ( standIn, fileNameWithFrame ) in performArnoldPathmapping.mappedFiles:
                #Perform pathmapping
                runPathmappingOnFile(
                    os.path.join( origDir, fileNameWithFrame ),
                    os.path.join( performArnoldPathmapping.tempLocation, standIn, fileNameWithFrame )
                )
                performArnoldPathmapping.mappedFiles.add( ( standIn, fileNameWithFrame ) )

performArnoldPathmapping.tempLocation = ""
#State property which contains mappings of standin objects to their original fileproperties
performArnoldPathmapping.originalProperties = {}
#State property which contains unique identifier for each file that we have already mapped in the form of ( standin, filename )
performArnoldPathmapping.mappedFiles=set()

    
def runPathmappingOnFile( originalLocation, pathmappedLocation ):
    print( 'Running PathMapping on "%s" and copying to "%s"' % (originalLocation, pathmappedLocation) )
    arguments = [ "-CheckPathMappingInFile", originalLocation, pathmappedLocation ]
    print( CallDeadlineCommand( arguments ) )
                
def GetDeadlineCommand():
    deadlineBin = ""
    try:
        deadlineBin = os.environ['DEADLINE_PATH']
    except KeyError:
        #if the error is a key error it means that DEADLINE_PATH is not set. however Deadline command may be in the PATH or on OSX it could be in the file /Users/Shared/Thinkbox/DEADLINE_PATH
        pass
        
    # On OSX, we look for the DEADLINE_PATH file if the environment variable does not exist.
    if deadlineBin == "" and os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
        with open( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f:
            deadlineBin = f.read().strip()

    deadlineCommand = os.path.join(deadlineBin, "deadlinecommand")
    
    return deadlineCommand

def CallDeadlineCommand(arguments, hideWindow=True):
    deadlineCommand = GetDeadlineCommand()
    startupinfo = None
    creationflags = 0
    if os.name == 'nt':
        if hideWindow:
            # Python 2.6 has subprocess.STARTF_USESHOWWINDOW, and Python 2.7 has subprocess._subprocess.STARTF_USESHOWWINDOW, so check for both.
            if hasattr( subprocess, '_subprocess' ) and hasattr( subprocess._subprocess, 'STARTF_USESHOWWINDOW' ):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            elif hasattr( subprocess, 'STARTF_USESHOWWINDOW' ):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            # still show top-level windows, but don't show a console window
            CREATE_NO_WINDOW = 0x08000000 #MSDN process creation flag
            creationflags = CREATE_NO_WINDOW
        
    arguments.insert( 0, deadlineCommand )

    # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags)
    output, errors = proc.communicate()
    
    return output

def OutputPluginVersions():
    print("================== PLUGINS ===================\n")
    plugins = sorted(maya.cmds.pluginInfo(query=True, listPlugins=True), key=lambda p: p.lower())
    for plugin in plugins:
        version = maya.cmds.pluginInfo(plugin, query=True, version=True)
        print("%s (v%s)" % (plugin, version))
    print("==============================================\n")

def ForceLoadPlugins():
    """
    Force load an explicit set of plug-ins with known issues. There are bugs in Maya where these plug-ins are not
    automatically loaded when required in a scene.

    When a scene contains an Alembic reference node (backed by an external .abc file), Maya does not embed "requires"
    statements into the scene to indicate that the "AbcImport" and "fbxmaya" plug-ins are dependencies of the scene.
    This can be changed for the current Maya session with the following MEL commands:

        pluginInfo -edit -writeRequires AbcImport
        pluginInfo -edit -writeRequires fbxmaya

    However, there is a secondary bug where the "requires" statements are inserted in the scene after already trying to
    load the references.

    Our work-around is to force loading of these plug-ins always before loading the job scene. Both plugins ship with
    Maya and are fairly lightweight in size.
    """

    PLUGINS_TO_LOAD = (
        'AbcImport',    # For Maya 2017 on Windows this is 5MB and takes 15 ms to load
        'fbxmaya'       # For Maya 2017 on Windows this is 12MB and takes 141ms to load
    )

    for plugin in PLUGINS_TO_LOAD:
        plugin_loaded = maya.cmds.pluginInfo(plugin, query=True, loaded=True)
        if not plugin_loaded:
            try:
                print( "Loading %s..." % plugin, end="" )
                maya.cmds.loadPlugin( plugin )
            except RuntimeError as e:
                # Maya raises this exception when it cannot find the plugin. The message is formatted as:
                #
                # Plug-in, "pluginName", was not found on MAYA_PLUG_IN_PATH
                #
                # This seems reasonable enough to forward on to the user. The try-except only serves the purpose of
                # continuing to attempt additional plug-ins. This is a best-effort work-around.
                print( 'Error: %s' % e)
            else:
                print( "ok" )