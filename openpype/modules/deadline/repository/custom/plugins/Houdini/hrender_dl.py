from __future__ import print_function
import sys
import traceback
from collections import namedtuple
from itertools import chain

import os
import re
import subprocess

import hou

def setupTileOutput( file, tileNumber ):
    frameRegex = re.compile( "\$F", re.IGNORECASE )
    matches = frameRegex.findall( file )
    if matches is not None and len( matches ) > 0:
        paddingString = matches[ len( matches ) - 1 ]
        padding = "_tile"+str(tileNumber)+"_$F"
        file = RightReplace( file, paddingString, padding, 1 )
    else:
        paddedNumberRegex = re.compile( "([0-9]+)", re.IGNORECASE )
        matches = paddedNumberRegex.findall( file )
        if matches is not None and len( matches ) > 0:
            paddingString = matches[ len( matches ) - 1 ]
            padding = "_tile"+str(tileNumber)+"_"+paddingString
            file = RightReplace( file, paddingString, padding, 1 )
        else:
            splitFilename = os.path.splitext(file)
            file = splitFilename[0]+"_tile"+str(tileNumber)+"_"+splitFilename[1]

    return file

def includeNodeInTakeAndAllowEditing( node ):
    currentTake = hou.takes.currentTake()
    currentTake.addParmTuplesFromNode( node )
    node.allowEditingOfContents()

def RightReplace( fullString, oldString, newString, occurences ):
    return newString.join( fullString.rsplit( oldString, occurences ) )

def ApplySettingsToRop(rop, settingsDict):
    """
    Iterates over a dictionary of settings for the specified ROP and applies their values.
    :param rop: The ROP to apply settings to
    :param settingsDict: A dictionary of settings with the setting name being the 'Key' and the desired value as the 'Value'
    """
    for settingName in settingsDict:
        setting = rop.parm(settingName)
        if setting is not None:
            setting.set(settingsDict.get(settingName))


def GetDeadlineCommand():
    deadlineBin = ""
    try:
        deadlineBin = os.environ['DEADLINE_PATH']
    except KeyError:
        # if the error is a key error it means that DEADLINE_PATH is not set. however Deadline command may be in the PATH or on OSX it could be in the file /Users/Shared/Thinkbox/DEADLINE_PATH
        pass

    # On OSX, we look for the DEADLINE_PATH file if the environment variable does not exist.
    if deadlineBin == "" and os.path.exists("/Users/Shared/Thinkbox/DEADLINE_PATH"):
        with open("/Users/Shared/Thinkbox/DEADLINE_PATH") as f:
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
            if hasattr(subprocess, '_subprocess') and hasattr(subprocess._subprocess, 'STARTF_USESHOWWINDOW'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            elif hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            # still show top-level windows, but don't show a console window
            CREATE_NO_WINDOW = 0x08000000  # MSDN process creation flag
            creationflags = CREATE_NO_WINDOW

    arguments.insert(0, deadlineCommand)

    # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            startupinfo=startupinfo, creationflags=creationflags)
    output, errors = proc.communicate()

    return output


def pathmap_file(in_file_name, out_file_name=None, print_stdout=True):
    """
    Runs Deadlines CheckPathMappingInFile Deadline command in order to perform pathmapping on a file.
    :param in_file_name: The name of the File to be pathmapped
    :param out_file_name: The name of the output file (defaults to the input filename)
    :param print_stdout: If the Stdout should be printed to the log
    :return: None
    """

    if not out_file_name:
        out_file_name = in_file_name

    std_output = CallDeadlineCommand(["--CheckPathMappingInFile", in_file_name, out_file_name])
    if print_stdout:
        print(std_output)


def is_parm_valid_for_pathmapping(parm):
    """
    Helper function used to determine if a parm is valid for the purposes of pathmapping.
    This will return False for all nodes that meet at least 1 of the following conditions:
        * Parm is None
        * Parm is locked (non editable)
        * Parm is inside of a Locked HDA (Node is not editable) unless it is specified as editable
        * Parm is Disabled
        * Parm contains an empty string value
        * Parm is a soho_program parm (file run when render is called on the specified node
    :param parm: The Parm that we wish to check validity on
    :return: If the parm is Valid
    """
    # If the parm is none then the value is intrinisic to the scene and we cannot modify it
    if not parm:
        return False

    # Locked Parms cannot be modified
    if parm.isLocked():
        return False

    node = parm.node()
    # if the node is inside a locked HDA and is not specifically marked as Editable then the value is derived
    # from somewhere else
    if node.isInsideLockedHDA() and not node.isEditableInsideLockedHDA():
        return False

    # soho_program parms point to the script that a rop will run when told to render and as such should never need to be mapped.
    if parm.name() == "soho_program":
        return False

    # Disabled nodes have no effect so we should be fine ignoring them.
    if parm.isDisabled():
        return False

    # Make sure that we actually have a non empty string without keyframes
    # Keyframes will need special casing
    try:
        if not parm.unexpandedString():
            return False
    except hou.OperationFailed:
        return False
    return True


def gather_parms_to_map():
    """
    Builds up a list of all parms in the houdini scene file that need to be pathmapped
     and puts them into a list
    :return: list of hou.parm that may need pathmapping
    """

    # Get all non empty file references in the scene not marked as Write Only
    input_refs = (parm for parm, _ in hou.fileReferences())

    # Get all Output only file parms from all Arnold ROPs in the scene

    arnold_node_type = hou.nodeType('Driver/arnold')
    arnold_output_parms = ()
    if arnold_node_type:
        arnold_output_parms = (
            parm
            for node in arnold_node_type.instances()
            for parm in node.globParms("ar_aov_separate_file* ar_picture ar_ass_file")
        )

    # Check validity of all parms to narrow down the ones we need to map.
    return [
        parm
        for parm in chain(input_refs, arnold_output_parms)
        if is_parm_valid_for_pathmapping(parm)
    ]


def pathmap_arnold_procedurals(tempdir, start_frame, end_frame):
    """
    Pathmaps all .ass files that are referenced by arnold procedural nodes
    :param tempdir: The base directory that the procedural nodes should be copied to.
    :param start_frame: The first frame we are rendering with this task
    :param end_frame: The last frame we are rendering with this task
    :return: None
    """
    hou_procedural_type = 'Object/arnold_procedural'

    print("Begin path mapping Arnold procedurals")
    for node in hou.nodeType(hou_procedural_type).instances():
        parm = node.parm('ar_filename')

        if not is_parm_valid_for_pathmapping(parm):
            print("Skipping parm: %s" % parm.path())
            continue

        # Arnold procedurals can point to multiple file types, we only want to copy .ass files currently.
        try:
            if os.path.splitext(parm.evalAsString())[1].lower() != ".ass":
                continue
        except hou.OperationFailed:
            # We were not able to evaluate the parm.
            continue

        print("Updating parm: %s" % parm.path())

        # Determine the location to copy the files to and create the directory.
        # The Path will be (<Path to job directory>/tempdir_<ThreadID>/path/to/node
        node_tempdir = os.path.join(tempdir, node.path().strip('/'))
        if not os.path.isdir(node_tempdir):
            os.makedirs(node_tempdir)

        # Get the unexpanded File path so we can update the Parm after copying files.
        unexpanded = parm.unexpandedString()
        unexpanded_name = os.path.split(unexpanded)[1]

        copied_files = set()

        for frame in range(start_frame, end_frame + 1):
            # Eval all tokens and expressions at each frame
            expanded_file = parm.evalAsStringAtFrame(frame)

            if not expanded_file in copied_files:
                # Perform Pathmapping
                print("Performing path mapping on '%s'" % expanded_file)
                expanded_file_name = os.path.split(expanded_file)[1]
                pathmap_file(expanded_file, os.path.join(node_tempdir, expanded_file_name))
                copied_files.add(expanded_file)

        # Update the Parm
        try:
            parm.set(os.path.join(node_tempdir, unexpanded_name))
        except hou.OperationFailed as e:
            print('Failed to update Parm "%s" received the following exception: %s' % (parm.path(), e))

        print("End path mapping Arnold procedurals")


def pathmap_parms(tempdir, parms):
    """
    Performs path mapping on a list of parms
    :param tempdir: The temporary directory that we will use as part of pathmapping
    :param parms: A list of parms that we will be performing pathmapping
    :return: None
    """
    ver = hou.applicationVersion()[0]
    # Write out a temporary file with each path on a separate line
    pathmapFileName = os.path.join(tempdir, "parm_pathmap.txt")
    with open(pathmapFileName, 'w') as pathmap_handle:
        if ver < 18:
            pathmap_handle.write(
                "\n".join(parm.unexpandedString() for parm in parms)
            )
        else:
            pathmap_handle.write(
                "\n".join(parm.rawValue() for parm in parms)
            )
    # Perform pathmapping on the file, so each line is swapped to the new mapped location.
    pathmap_file(pathmapFileName, pathmapFileName)

    # Read back in the mapped file and update all parms to the new values
    with open(pathmapFileName, 'r') as pathmap_handle:
        for parm, path in zip(parms, pathmap_handle.readlines()):
            if ver < 18:
                raw_value = parm.unexpandedString()
            else:
                raw_value = parm.rawValue()

            if not raw_value == path.strip():
                try:
                    print('Updating Parm "%s" from "%s" to "%s"' % (parm.path(), raw_value, path.strip()))
                    parm.set(path.strip())
                except hou.OperationFailed as e:
                    print('Failed to update Parm "%s" received the following exception: %s' % (parm.path(), e))


def pathmap_envs(tempdir, envs):
    """
    Performs path mapping on a list of DLPathmapEnvs
    :param tempdir: The temporary directory that we will use as part of pathmapping
    :param envs: A list of envs that we will be performing pathmapping
    :return: None
    """
    # Write out a temporary file with each path on a separate line
    pathmap_file_name = os.path.join(tempdir, "env_pathmap.txt")
    with open(pathmap_file_name, 'w') as pathmap_handle:
        pathmap_handle.write(
            "\n".join(env.val for env in envs)
        )

    # Perform pathmapping on the file, so each line is swapped to the new mapped location.
    pathmap_file(pathmap_file_name, pathmap_file_name)

    # Read back in the mapped file and update all parms to the new values
    with open(pathmap_file_name, 'r') as pathmap_handle:
        for orig, line in zip(envs, pathmap_handle.readlines()):
            val = line.strip()
            if val != orig.val:
                print('Setting variable "{name}" to {val}'.format(name=orig.name, val=val) )
                hou.putenv(orig.name, val)

    # Varchange updates all nodes in the scene to use the latest versions of vals
    hou.hscript('varchange')


def gather_envs_to_map():
    """
    Builds up a list of all variable in the houdini env that need to be pathmapped
     and puts them into a list
    :return: list of EnvToMap that may need pathmapping
    """
    env_to_map = namedtuple('EnvToMap', ['name', 'val'])

    found_envs = []

    # gather all globally set houdini variables
    # this will return everything in 2 strings the first string of the format:
    # ENV\t= VAL\n
    # While the second is the Errors from the command
    set_envs = hou.hscript('setenv')

    for line in set_envs[0].split('\n'):
        if line.strip():
            env, val = line.split('\t= ', 1)
            found_envs.append(env_to_map(env.strip(), val.strip()))

    return found_envs


def perform_pathmapping(tempdir):
    """
    Perform pathmapping on all input parameters and other select parameters
    :param tempdir: the temporary location that a text file will be written to to aid pathmapping.
    :return: None
    """
    if not tempdir:
        print("Temporary Directory has not been set. Skipping Pathmapping.")
        return

    print("Begin Path Mapping")

    update_mode = hou.updateModeSetting()
    hou.setUpdateMode(hou.updateMode.Manual)

    # gather a list of all parameters that need to be pathmapped
    parms = gather_parms_to_map()
    if parms:
        pathmap_parms(tempdir, parms)

    envs = gather_envs_to_map()
    if envs:
        pathmap_envs(tempdir, envs)
    hou.setUpdateMode(update_mode)
    print("End Path Mapping")


try:
    print( "Detected Houdini version: " + str( hou.applicationVersion() ) )

    args = sys.argv
    print( args )

    startFrame = 0
    endFrame = 0
    increment = 1
    frameTuple = ()
    # Parse the arguments
    if "-f" in args:
        frameIndex = args.index( "-f" )
        startFrame = int(args[ frameIndex + 1 ])
        endFrame = int(args[ frameIndex + 2 ])
        increment = int(args[ frameIndex + 3 ])
        print( "Start: " + str(startFrame) )
        print( "End: " + str(endFrame) )
        print( "Increment: " + str(increment) )
        frameTuple = ( startFrame, endFrame, increment )

    resolution = ()
    if "-r" in args:
        resolutionIndex = args.index( "-r" )
        width = int( args[ resolutionIndex + 1 ] )
        height = int( args[ resolutionIndex + 2 ] )
        resolution = (width,height)
        print( "Width: " + str(width) )
        print( "Height: " + str(height) )

    ignoreInputs = False
    if "-g" in args:
        ignoreInputs = True
        print( "Ignore Inputs: True" )
    else:
        print( "Ignore Inputs: False" )

    if "-o" not in args:
        output = None
        ext = None
        print( "No output specified. Output will be handled by the driver" )
    else:
        outputIndex = args.index( "-o" )
        output = args[ outputIndex + 1 ]
        print( "Output: " + output )

    if "-i" not in args:
        ifd = None
    else:
        ifdIndex = args.index( "-i" )
        ifd = args[ ifdIndex + 1 ]
        print( "IFD: " + ifd )

    gpus = None
    if "-gpu" in args:
        gpusIndex = args.index( "-gpu" )
        gpus = args[ gpusIndex + 1 ]
        print( "GPUs: " + gpus )

    tileRender = False
    xStart = 0
    xEnd = 0
    yStart = 0
    yEnd = 0
    currTile = 0
    if "-t" in args:
        tileRender = True
        tileIndex = args.index( "-t" )
        currTile = int( args[ tileIndex + 1 ] )
        xStart = float( args[ tileIndex + 2 ] )
        xEnd = float( args[ tileIndex + 3 ] )
        yStart = float( args[ tileIndex + 4 ] )
        yEnd = float( args[ tileIndex + 5 ] )

    if "-wedgenum" not in args:
        wedgeNum = -1
    else:
        wedgeNumIndex = args.index("-wedgenum")
        wedgeNum = int(args[wedgeNumIndex + 1])
        print( "Wedge Number: " + str(wedgeNum) )

    driverIndex = args.index( "-d" )
    driver = args[ driverIndex + 1 ]
    #if not driver.startswith( "/" ):
    #    driver = "/out/" + driver
    print( "Driver: " + driver )

    inputFile = args[ len(args) - 1 ]
    print( "Input File: " + inputFile )

    isSim = False
    sliceNum = 0
    trackerMachine = ""
    trackerPort = -1
    if "-s" in args:
        isSim = True
        sliceIndex = args.index("-s")
        sliceNum = int( args[ sliceIndex + 1 ] )
        trackerMachine = args[ sliceIndex + 2 ]
        trackerPort = int( args[ sliceIndex + 3 ] )

    tempdir = ""
    if "-tempdir" in args:
        tempdirIndex = args.index("-tempdir")
        tempdir = args[tempdirIndex + 1]

    arnoldAbortOnLicenseFail = 1
    if "-arnoldAbortOnLicenseFail" in args:
        arnoldAbortOnLicenseFailIndex = args.index("-arnoldAbortOnLicenseFail")
        arnoldAbortOnLicenseFail = int( args[ arnoldAbortOnLicenseFailIndex + 1 ] )

    # Print out load warnings, but continue on a successful load.
    try:
        hou.hipFile.load( inputFile )
    except hou.LoadWarning as e:
        print(e)

    # Get the output driver.
    rop = hou.node( driver )
    if rop == None:
        print( "Error: Driver \"" + driver + "\" does not exist" )
    else:
        includeNodeInTakeAndAllowEditing( rop )
        if isSim:
            sliceType = rop.parm("slice_type").evalAsString()
            if sliceType == "volume" or sliceType == "particle":
                # Sim job, so update the sim control node and get the actual ROP for rendering.
                simControlName = rop.parm("hq_sim_controls").evalAsString()
                print( "Sim control node: " + simControlName )

                hou.hscript("setenv SLICE="+str(sliceNum))
                hou.hscript("varchange")
                print( "Sim slice: " + str(sliceNum) )

                simControlNode = hou.node( simControlName )
                includeNodeInTakeAndAllowEditing( simControlNode )
                if simControlNode.parm("visaddress") is not None:
                    simControlNode.parm("visaddress").set( trackerMachine )
                else:
                    simControlNode.parm("address").set( trackerMachine )

                simControlNode.parm("port").set( trackerPort )

                print( "Sim Tracker: " + trackerMachine )
                print( "Sim Port: " + str(trackerPort) )
            elif sliceType == "cluster":
                # Sim job, so update the sim control node and get the actual ROP for rendering.
                simControlName = rop.parm("hq_sim_controls").evalAsString()
                print( "Sim control node: " + simControlName )

                hou.hscript("setenv CLUSTER="+str(sliceNum))
                hou.hscript("varchange")
                print( "Sim cluster: " + str(sliceNum) )

            rop = hou.node( rop.parm("hq_driver").eval() )
            includeNodeInTakeAndAllowEditing( rop )
            startFrame = int(rop.evalParm("f1"))
            endFrame = int(rop.evalParm("f2"))
            increment = int(rop.evalParm("f3"))

        # Set the necessar IFD settings if exporting IFD files.
        if ifd is not None:
            print( "Setting SOHO output mode to 1" )
            ifdExportParm = rop.parm( "soho_outputmode" )
            if ifdExportParm is not None:
                ifdExportParm.set( 1 )

            print( "Setting SOHO disk file to " + ifd )
            ifdFilenameParm = rop.parm( "soho_diskfile" )
            if ifdFilenameParm is not None:
                ifdFilenameParm.set( ifd )

        perform_pathmapping(tempdir)
        # Turn progress reporting on, and set the output path. The reason we set the output path here instead of
        # in the 'render' function below is that the 'render' function always seems to replace the $F padding with
        # frame 1. So the output for each frame always overwrites the previous.
        ropType = rop.type().name()
        safeROPType = rop.type().nameWithCategory()
        print( "ROP type: " + ropType )

        wedgeNode = None

        isWedge = (ropType == "wedge")
        numTasks = 1

        #If this is a wedge rop we need to do some additional set up
        if isWedge:

            #Get the render rop and make sure the frame range is set correctly
            renderNode = rop.node(rop.parm("driver").eval())
            includeNodeInTakeAndAllowEditing( renderNode )
            renderNode.parm("f1").set(startFrame)
            renderNode.parm("f2").set(endFrame)
            renderNode.parm("f3").set(increment)
            frameTuple = ( )
            if (wedgeNum >= 0):
                #We are only using one wedge, set it up as such
                rop.parm("wrange").set(1)
                rop.parm("wedgenum").set(wedgeNum)
            else:
                #Do all the wedges for the frame range. We will use this scripts last call to render as the last wedge's render call,
                # so we just need to render the first n-1 wedges here and then set up the rop for the last render.
                wedgeMethod = rop.parm("wedgemethod").evalAsString()
                if wedgeMethod == "channel":
                    numParams = rop.parm("wedgeparams").eval()
                    random = rop.parm("random").eval()

                    if random:
                        #We're using the random settings
                        numRandom = rop.parm("numrandom").eval()
                        numTasks = numRandom * numParams
                    else:
                        #Using the number wedge params to determine task count
                        for i in range(1, numParams+1):
                            numTasks = numTasks * int(rop.parm("steps"+str(i)).eval())
                elif wedgeMethod == "take":
                    takename = rop.parm("roottake").eval()
                    parentTake = hou.takes.findTake(takename)
                    if parentTake:
                        children = parentTake.children()
                        numTasks = len(children)

                rop.parm("wrange").set(1)

            #Store the wedge rop for rendering later, set the output driver rop as the current rop to ensure
            #all our output and progress is tracked.
            wedgeNode = rop
            rop = renderNode
            ropType = rop.type().name()

        if ropType == 'rop_geometry':
            # Turn on Alfred-style progress reporting on Geo ROP.
            alf_prog_parm = rop.parm("alfprogress")
            if alf_prog_parm is not None:
                alf_prog_parm.set(1)

        elif ropType == 'geometry':
            alfredProgress = rop.parm( "alfprogress" )
            if alfredProgress is not None:
                alfredProgress.set( 1 )
                print( "Enabled Alfred style progress" )

            reportNetwork = rop.parm( "reportnetwork" )
            if reportNetwork is not None:
                reportNetwork.set( 1 )
                print( "Enabled network use reporting" )

            if output is not None:
                outputFile = rop.parm( "sopoutput" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == 'ifd':
            alfredProgress = rop.parm( "vm_alfprogress" )
            if alfredProgress is not None:
                alfredProgress.set( 1 )
                print( "Enabled Alfred style progress" )

            verbosity = rop.parm( "vm_verbose" )
            if verbosity is not None:
                verbosity.set( 3 )
                print( "Set verbosity to 3" )

            if tileRender:
                if output == None:
                    output = rop.parm( "vm_picture" ).unexpandedString()

                output = setupTileOutput(output, currTile )

                ropTilesEnabled = rop.parm( "vm_tile_render" )
                if ropTilesEnabled is not None:
                    ropTilesEnabled.set(0)

            if output is not None:
                outputFile = rop.parm( "vm_picture" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == 'arnold':
            logToConsole = rop.parm( "ar_log_console_enable" )
            if logToConsole is not None:
                logToConsole.set( 1 )
                print( "Enabled log to console" )

            logVerbosity = rop.parm( "ar_log_verbosity" )
            if logVerbosity is not None:
                logVerbosity.set( 'detailed' )
                print( "Set verbosity to " + logVerbosity.eval() )

            abortOnLicenseFail = rop.parm( "ar_abort_on_license_fail" )
            if abortOnLicenseFail is not None:
                abortOnLicenseFail.set( arnoldAbortOnLicenseFail )
                print( "Set Arnold abort on license fail to %s" % abortOnLicenseFail.eval() )

            if tileRender:
                if output == None:
                    output = rop.parm( "ar_picture" ).unexpandedString()

                output = setupTileOutput(output, currTile)

            if output is not None:
                outputFile = rop.parm( "ar_picture" )
                if outputFile is not None:
                    outputFile.set(output)

            # Arnold does not work with Houdini's normal pathmapping so we use our own.
            pathmap_arnold_procedurals(tempdir, startFrame, endFrame)

        elif ropType == 'baketexture':
            if output is not None:
                outputFile = rop.parm( "vm_uvoutputpicture1" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == "comp":
            if output is not None:
                outputFile = rop.parm( "copoutput" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == "channel":
            if output is not None:
                outputFile = rop.parm( "chopoutput" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == "dop":
            if output is not None:
                outputFile = rop.parm( "dopoutput" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == 'filmboxfbx':
            makePath = rop.parm("mkpath")
            if makePath is not None:
                makePath.set(1)

            if output is not None:
                outputFile = rop.parm( "sopoutput" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == 'opengl':
            if output is not None:
                outputFile = rop.parm( "picture" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == "rib":
            if tileRender:
                if output is None:
                    output = rop.parm( "ri_display" ).unexpandedString()

                output = setupTileOutput( output, currTile )

            if output is not None:
                outputFile = rop.parm( "ri_display" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == "ris::22":
            if tileRender:
                if output is None:
                    # No need to check displays here. Tile Rendering is only available with Override Output.
                    # We check if there is a single display later in the Override Output.
                    output = rop.parm("ri_display_0").unexpandedString()

                if output is not None:
                    output = setupTileOutput(output, currTile)

            if output is not None:
                displays = rop.parm("ri_displays")
                if displays is not None:
                    total_displays = displays.eval()

                if total_displays == 1:
                    outputFile = rop.parm("ri_display_0")
                    if outputFile is not None:
                        outputFile.set(output)
                else:
                    raise RuntimeError("Override Output is supported only for a single display but found {0}.".format(total_displays))

            printProgress = rop.parm( "progress" )
            if printProgress is not None:
                printProgress.set( 1 )

        elif ropType == "rop_alembic":
            if output is not None:
                outputFile = rop.parm( "filename" )
                if outputFile is not None:
                    outputFile.set( output )

        elif ropType == "Redshift_ROP":
            redshiftHardSettingsDict = {
                "RS_nonBlockingRendering" : 0,
                "RS_renderAOVsToMPlay" : 0,
                "RS_overwriteMPlayImage" : 0,
                "RS_MPlay_disabledNonGUI" : 0,
                "RS_renderToMPlay" : 0
            }

            if output is not None:
                redshiftHardSettingsDict["RS_outputFileNamePrefix"] = output

                # create the output directory
                output_folder_unexpanded = os.path.dirname(output)
                output_folder = hou.expandString(output_folder_unexpanded)
                if not os.path.isdir(output_folder):
                    try:
                        print( 'Creating the output directory "%s"' % output_folder )
                        os.makedirs(output_folder)
                    except:
                        print( 'Failed to create output directory "%s". The path may be invalid or permissions may not be sufficient.' % output_folder )
                        raise

            ApplySettingsToRop(rop, redshiftHardSettingsDict)

            if gpus is not None:
                print( "This Slave is overriding its GPU affinity, so the following GPUs will be used by RedShift: " + gpus )
                gpus = gpus.split( "," )
                gpuSettingString = ""
                for i in range(8):
                    if str( i ) in gpus:
                        gpuSettingString += "1"
                    else:
                        gpuSettingString += "0"
                hou.hscript( "Redshift_setGPU -s "+gpuSettingString )

        elif ropType == "Octane_ROP":
            octaneHardSettingsDict = {
                "HO_statisticsMPlay" : 0,
                "HO_statisticsFinalMPlay" : 0,
                "HO_overwriteMPlay" : 0,
                "HO_renderToMPlay" : 0,
                "HO_img_enable" : 1,
                "HO_img_createDir" : 1
            }

            if output is not None:
                octaneHardSettingsDict["HO_img_fileName"] = output

            ApplySettingsToRop(rop, octaneHardSettingsDict)

            if gpus is not None:
                print( "This Slave is overriding its GPU affinity, so the following GPUs will be used by Octane: " + gpus )
                gpus = gpus.split( "," )
                for i in range(16):
                    hou.hscript( "Octane_setGPU -g %s -s %s"%( i, int( str( i ) in gpus) ) )

        elif safeROPType == "Driver/vray_renderer":
            if output is not None:
                outputFile = rop.parm( "SettingsOutput_img_file_path" )
                if outputFile is not None:
                    outputFile.set( output )
            if ifd is not None:
                ifdFile = rop.parm( "render_export_filepath" )
                if ifdFile is not None:
                    ifdFile.set( ifd )

        if tileRender:
            camera = rop.parm( "camera" ).eval()
            cameraNode = hou.node(camera)
            includeNodeInTakeAndAllowEditing( cameraNode )

            cropLeft = cameraNode.parm( "cropl" )
            if cropLeft is not None:
                cropLeft.set( xStart )

            cropRight = cameraNode.parm( "cropr" )
            if cropRight is not None:
                cropRight.set( xEnd )

            cropBottom = cameraNode.parm( "cropb" )
            if cropBottom is not None:
                cropBottom.set( yStart )

            cropTop = cameraNode.parm( "cropt" )
            if cropTop is not None:
                cropTop.set( yEnd )

        frameString = ""
        # Render the frames.
        if startFrame == endFrame:
            frameString = "frame " + str(startFrame)
        else:
            frameString = "frame " + str(startFrame) + " to " + str(endFrame)

        if isWedge:
            rop = wedgeNode
            if wedgeNum == -1:
                #Do all the wedges for the frame range. We will use this scripts' last call to render as the last wedge's render call,
                # so we just need to render the first n-1 wedges here and then set up the rop for the last render.
                for i in range(0, (numTasks - 1)):
                    print( "Rendering wedge " + str(i) + " for " + frameString )
                    rop.parm("wedgenum").set(i)
                    rop.render( frameTuple, resolution, ignore_inputs=ignoreInputs )

                #Since we looped to the second last, we need to set the wedge number for the last render call
                print( "Rendering wedge " + str(numTasks-1) + " for " + frameString )
                rop.parm("wedgenum").set(numTasks-1)
            else:
                #This is a single wedge job
                print( "Rendering wedge " + str(wedgeNum) + " for " + frameString )
        else:
            print( "Rendering " + frameString )

        #Renders the given rop. Renders the last wedge of a multi-wedge wedge job.
        rop.render( frameTuple, resolution, ignore_inputs=ignoreInputs )

        print( "Finished Rendering" )
except Exception as e:
    print( "Error: Caught exception: " + str(e) )
    raise
