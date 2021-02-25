import io
import json
import os
import re
from collections import defaultdict, namedtuple

from Deadline.Plugins import *
from Deadline.Scripting import *
from FranticX.Processes import *
from System import *
from System.Diagnostics import *
from System.IO import *
from System.Text import *
from six import string_types


######################################################################
## This is the function that Deadline calls to get an instance of the
## main DeadlinePlugin class.
######################################################################
def GetDeadlinePlugin():
    return MayaBatchPlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()


######################################################################
## This is the main DeadlinePlugin class for the MayaBatch plugin.
######################################################################
class MayaBatchPlugin(DeadlinePlugin):
    ProcessName = "MayaBatch"
    Process = None

    Version = 0
    Build = "none"
    Renderer = "mayasoftware"
    EnablePathMapping = False
    DirmapPathMapping = False
    XGenPathMapping = False
    EnableOpenColorIO = False

    StartFrame = ""
    EndFrame = ""
    ByFrame = ""
    RenumberFrameStart = ""
    FirstTask = True
    Animation = True

    SceneFile = ""
    ProjectPath = ""
    StartupScriptPath = ""
    RenderDirectory = ""
    CurrentRenderDirectory = ""
    LocalRendering = False
    ImagePrefix = ""

    TempThreadDirectory = ""

    Camera = ""
    Width = ""
    Height = ""
    AspectRatio = ""

    AntiAliasing = ""
    MotionBlur = ""
    Threads = ""
    Verbosity = ""

    RenderLayer = ""
    UsingRenderLayers = False

    Left = ""
    Right = ""
    Top = ""
    Bottom = ""

    ScriptJob = False
    ScriptFilename = ""

    BifrostJob = False
    BifrostCompressionFormat = "0"

    AlembicJob = False
    AlembicVerbose = False
    AlembicFormat = "Ogawa"
    AlembicFile = ""
    AlembicKeys = ""
    AlembicArgs = ""
    AlembicSelection = "All"

    GeometryCacheJob = False
    GeoFilePerFrame = False
    GeoCacheFileName = ""
    OneFilePerGeometry = ""
    PointsAsDblorFlt = ""
    PointsInLocalOrWorld = ""
    GeoCacheFormat = ""
    SelectedGeometry = ""

    FluidCacheJob = False
    FluidFilePerFrame = ""
    FluidCacheFileName = ""
    OneFilePerFluid = ""
    FluidCacheFormat = ""
    SelectedFluids = ""

    RegionRendering = False
    SingleRegionJob = False
    SingleRegionFrame = 0
    SingleRegionIndex = ""

    # Krakatoa Variables
    KrakatoaJobFileContainsKrakatoaParameters = True
    KrakatoaFinalPassDensity = ""
    KrakatoaFinalPassDensityExponent = ""
    KrakatoaUseLightingPassDensity = "0"
    KrakatoaLightingPassDensity = ""
    KrakatoaLightingPassDensityExponent = ""
    KrakatoaUseEmissionStrength = "0"
    KrakatoaEmissionStrength = ""
    KrakatoaEmissionStrength = ""
    KrakatoaUseEmission = "0"
    KrakatoaUseAbsorption = "0"
    KrakatoaEnableMotionBlur = "0"
    KrakatoaMotionBlurParticleSegments = ""
    KrakatoaJitteredMotionBlur = "0"
    KrakatoaShutterAngle = ""
    KrakatoaEnableDOF = ""
    KrakatoaSampleRateDOF = ""
    KrakatoaEnableMatteObjects = ""
    KrakatoaRenderingMethod = ""
    KrakatoaVoxelSize = "0.5"
    KrakatoaVoxelFilterRadius = "1"
    KrakatoaForceEXROutput = "1"

    # This list contains all of the known error messages that we want to fail on if strict error checking is enabled.
    # Each entry is either:
    # * a string - we will fail if the line contains the string(case sensitive)
    # * an iterable containing strings - we will fail if the line contains all of the strings in the iterable.
    fatal_strict_errors = [
        "Render failed",
        "could not get a license",
        "Could not obtain a license",
        "This scene does not have any renderable cameras",
        "Warning: The post-processing failed while attempting to rename file",
        "Error: Failed to open IFF file for reading",
        "Error: An exception has occurred, rendering aborted.",
        "Cannot open project",
        "Could not open file.",
        "Error reading file. :",
        "Error: Scene was not loaded properly, please check the scene name",
        "Error: Graphics card capabilities are insufficient for rendering.",
        "Not enough storage is available to process this command.",
        "Error: (Mayatomr) : mental ray has stopped with errors, see the log",
        "Warning: (Mayatomr.Scene) : no render camera found, final scene will be incomplete and can't be rendered",
        "mental ray: out of memory",
        "The specified module could not be found.",
        "Error: (Mayatomr.Export) : mental ray startup failed with errors",
        "Number of arguments on call to preLayerScript does not match number of parameters in procedure definition.",
        "Error: rman Fatal:",
        "rman Error:",
        "Error: There was a fatal error rendering the scene.",
        "Could not read V-Ray environment variable",
        "can't create file (No such file or directory)",
        "Fatal Error:",
        "Error writing render region to raw image file.",
        "Error: OctaneRender is not activated!",
        "Error: R12001",
        "ERROR pgLicenseCheck",
        ("Error: Camera", "does not exist"),
        (
            "Error: The attribute",
            "was locked in a referenced file, and cannot be unlocked.",
        ),
        ("Error: Cannot find file ", " for source statement."),
        ("error 101003:", "can't create file"),
        "Failed to save file",
        ("Error: ", "XGen:  Failed to find"),
    ]

    def __init__(self):
        self.InitializeProcessCallback += self.InitializeProcess
        self.StartJobCallback += self.StartJob
        self.RenderTasksCallback += self.RenderTasks
        self.EndJobCallback += self.EndJob

        self.scriptContents = ""
        self.isScriptLogged = False

    def Cleanup(self):
        del self.InitializeProcessCallback
        del self.StartJobCallback
        del self.RenderTasksCallback
        del self.EndJobCallback

        if self.Process:
            self.Process.Cleanup()
            del self.Process

    ## Called by Deadline to initialize the process.
    def InitializeProcess(self):
        # Set the plugin specific settings.
        self.SingleFramesOnly = False
        self.PluginType = PluginType.Advanced

    def StartJob(self):
        self.Version = StringUtils.ParseLeadingNumber(
            self.GetPluginInfoEntry("Version")
        )
        self.Version = (
            int(self.Version * 10) / 10.0
        )  # we only want one decimal place
        if not str(self.Version).endswith(".5"):
            self.Version = (
                int(self.Version) * 1.0
            )  # If it's not a *.5 Version, then we want to ignore the decimal value

        self.Build = self.GetPluginInfoEntryWithDefault(
            "Build", "None"
        ).lower()

        self.LogInfo("Rendering with Maya Version " + str(self.Version))

        self.EnablePathMapping = self.GetBooleanConfigEntryWithDefault(
            "EnablePathMapping", False
        )
        if self.EnablePathMapping:
            self.DirmapPathMapping = (
                self.GetConfigEntryWithDefault(
                    "PathMappingMode", "Use dirmap Command"
                )
                == "Use dirmap Command"
            )
            self.XGenPathMapping = self.GetBooleanConfigEntryWithDefault(
                "XGenPathMapping", False
            )
            self.EnableOpenColorIO = self.GetBooleanPluginInfoEntryWithDefault(
                "EnableOpenColorIO", False
            )

        sceneFilename = (
            self.GetPluginInfoEntryWithDefault(
                "SceneFile", self.GetDataFilename()
            )
            .strip()
            .replace("\\", "/")
        )
        sceneFilename = RepositoryUtils.CheckPathMapping(
            sceneFilename
        ).replace("\\", "/")
        if (
            SystemUtils.IsRunningOnWindows()
            and sceneFilename.startswith("/")
            and not sceneFilename.startswith("//")
        ):
            sceneFilename = "/" + sceneFilename

        self.TempThreadDirectory = self.CreateTempDirectory(
            "thread" + str(self.GetThreadNumber())
        )

        # We can only do path mapping on .ma files (they're ascii files)
        if (
            self.EnablePathMapping
            and not self.DirmapPathMapping
            and os.path.splitext(sceneFilename)[1].lower() == ".ma"
        ):
            self.LogInfo("Performing path mapping on ma scene file")

            tempSceneFileName = Path.GetFileName(sceneFilename)
            self.SceneFile = os.path.join(
                self.TempThreadDirectory, tempSceneFileName
            )

            RepositoryUtils.CheckPathMappingInFileAndReplace(
                sceneFilename, self.SceneFile, ("\\", '/"'), ("/", '\\"')
            )
            if SystemUtils.IsRunningOnLinux() or SystemUtils.IsRunningOnMac():
                os.chmod(self.SceneFile, os.stat(sceneFilename).st_mode)

        else:
            self.SceneFile = sceneFilename

        self.SceneFile = PathUtils.ToPlatformIndependentPath(self.SceneFile)

        # ~ # These options are passed to maya batch when it starts up.
        # ~ self.SceneFile = self.GetPluginInfoEntryWithDefault( "SceneFile", self.GetDataFilename() ).strip().replace( "\\", "/" )
        # ~ self.SceneFile = RepositoryUtils.CheckPathMapping( self.SceneFile ).replace( "\\", "/" )
        # ~ if SystemUtils.IsRunningOnWindows() and self.SceneFile.startswith( "/" ) and not self.SceneFile.startswith( "//" ):
        # ~ self.SceneFile = "/" + self.SceneFile

        self.ProjectPath = (
            self.GetPluginInfoEntryWithDefault("ProjectPath", "")
            .strip()
            .replace("\\", "/")
        )
        self.ProjectPath = RepositoryUtils.CheckPathMapping(
            self.ProjectPath
        ).replace("\\", "/")
        if (
            SystemUtils.IsRunningOnWindows()
            and self.ProjectPath.startswith("/")
            and not self.ProjectPath.startswith("//")
        ):
            self.ProjectPath = "/" + self.ProjectPath

        self.StartupScriptPath = (
            self.GetPluginInfoEntryWithDefault("StartupScript", "")
            .strip()
            .replace("\\", "/")
        )
        self.StartupScriptPath = RepositoryUtils.CheckPathMapping(
            self.StartupScriptPath
        ).replace("\\", "/")
        if (
            SystemUtils.IsRunningOnWindows()
            and self.StartupScriptPath.startswith("/")
            and not self.StartupScriptPath.startswith("//")
        ):
            self.StartupScriptPath = "/" + self.StartupScriptPath

        if self.StartupScriptPath:
            if not os.path.isfile(self.StartupScriptPath):
                self.FailRender(
                    'Startup script "%s" does not exist.'
                    % self.StartupScriptPath
                )

        # Set up the maya batch process.
        self.Renderer = self.GetPluginInfoEntryWithDefault(
            "Renderer", "mayaSoftware"
        ).lower()
        self.Process = MayaBatchProcess(
            self,
            self.Version,
            self.Build,
            self.SceneFile,
            self.ProjectPath,
            self.StartupScriptPath,
            self.Renderer,
            self.EnablePathMapping and self.DirmapPathMapping,
        )

        self.SetEnvironmentAndLogInfo("MAYA_DEBUG_ENABLE_CRASH_REPORTING", "0")
        self.SetEnvironmentAndLogInfo(
            "MAYA_DISABLE_CIP",
            "1",
            description="ADSK Customer Involvement Program",
        )
        self.SetEnvironmentAndLogInfo(
            "MAYA_DISABLE_CER",
            "1",
            description="ADSK Customer Error Reporting",
        )
        self.SetEnvironmentAndLogInfo(
            "MAYA_DISABLE_CLIC_IPM",
            "1",
            description="ADSK In Product Messaging",
        )
        self.SetEnvironmentAndLogInfo("MAYA_OPENCL_IGNORE_DRIVER_VERSION", "1")
        self.SetEnvironmentAndLogInfo(
            "MAYA_VP2_DEVICE_OVERRIDE", "VirtualDeviceDx11"
        )

        self.SetEnvironmentAndLogInfo(
            "MAYA_RENDER_SETUP_INCLUDE_ALL_LIGHTS",
            str(
                int(
                    self.GetBooleanPluginInfoEntryWithDefault(
                        "RenderSetupIncludeLights", True
                    )
                )
            ),
        )

        if self.Renderer == "redshift":
            # Flag which tells Redshift to kill Maya if Redshift runs into an internal error instead of hanging
            self.SetEnvironmentAndLogInfo(
                "REDSHIFT_FORCEQUITONINTERNALERROR", "1"
            )

        self.SetRedshiftPathmappingEnv()

        if self.Version >= 2016.5:
            useLegacyRenderLayers = int(
                self.GetBooleanPluginInfoEntryWithDefault(
                    "UseLegacyRenderLayers", False
                )
            )
            self.SetEnvironmentAndLogInfo(
                "MAYA_ENABLE_LEGACY_RENDER_LAYERS", str(useLegacyRenderLayers)
            )

        # If on the Mac, set some environment variables (these are normally set by MayaENV.sh when running the Maya Terminal).
        if SystemUtils.IsRunningOnMac():
            mayaExecutable = self.Process.RenderExecutable()
            mayaBinFolder = Path.GetDirectoryName(mayaExecutable)
            usrAwComBin = "/usr/aw/COM/bin"
            usrAwComEtc = "/usr/aw/COM/etc"

            self.LogInfo(
                "Adding "
                + mayaBinFolder
                + " to PATH environment variable for this session"
            )
            self.LogInfo(
                "Adding "
                + usrAwComBin
                + " to PATH environment variable for this session"
            )
            self.LogInfo(
                "Adding "
                + usrAwComEtc
                + " to PATH environment variable for this session"
            )

            path = Environment.GetEnvironmentVariable("PATH")
            if path:
                path = (
                    mayaBinFolder
                    + ":"
                    + usrAwComBin
                    + ":"
                    + usrAwComEtc
                    + ":"
                    + path
                )
                self.SetProcessEnvironmentVariable("PATH", path)
            else:
                self.SetProcessEnvironmentVariable(
                    "PATH",
                    mayaBinFolder + ":" + usrAwComBin + ":" + usrAwComEtc,
                )

            mayaLocation = Path.GetDirectoryName(mayaBinFolder)
            self.SetEnvironmentAndLogInfo("MAYA_LOCATION", mayaLocation)

            mayaMacOSFolder = Path.Combine(mayaLocation, "MacOS")
            self.LogInfo(
                "Adding "
                + mayaMacOSFolder
                + " to DYLD_LIBRARY_PATH environment variable for this session"
            )
            libraryPath = Environment.GetEnvironmentVariable(
                "DYLD_LIBRARY_PATH"
            )
            if libraryPath:
                libraryPath = mayaMacOSFolder + ":" + libraryPath
                self.SetProcessEnvironmentVariable(
                    "DYLD_LIBRARY_PATH", libraryPath
                )
            else:
                self.SetProcessEnvironmentVariable(
                    "DYLD_LIBRARY_PATH", mayaMacOSFolder
                )

            mayaFrameworksFolder = Path.Combine(mayaLocation, "Frameworks")
            self.LogInfo(
                "Adding "
                + mayaFrameworksFolder
                + " to DYLD_FRAMEWORK_PATH environment variable for this session"
            )
            frameworkPath = Environment.GetEnvironmentVariable(
                "DYLD_FRAMEWORK_PATH"
            )
            if frameworkPath:
                frameworkPath = mayaFrameworksFolder + ":" + frameworkPath
                self.SetProcessEnvironmentVariable(
                    "DYLD_FRAMEWORK_PATH", frameworkPath
                )
            else:
                self.SetProcessEnvironmentVariable(
                    "DYLD_FRAMEWORK_PATH", mayaFrameworksFolder
                )

            mayaPythonVersionsFolder = Path.Combine(
                mayaFrameworksFolder, "Python.framework/Versions"
            )

            pythonVersion = "2.7"
            mayaPythonVersionFolder = Path.Combine(
                mayaPythonVersionsFolder, pythonVersion
            )
            if not Directory.Exists(mayaPythonVersionFolder):
                pythonVersion = "2.6"
                mayaPythonVersionFolder = Path.Combine(
                    mayaPythonVersionsFolder, pythonVersion
                )

            if Directory.Exists(mayaPythonVersionFolder):
                self.SetEnvironmentAndLogInfo(
                    "PYTHONHOME", mayaPythonVersionFolder
                )

        elif SystemUtils.IsRunningOnWindows():
            mayaExecutable = self.Process.RenderExecutable()
            mayaBinFolder = Path.GetDirectoryName(mayaExecutable)
            mayaLocation = Path.GetDirectoryName(mayaBinFolder)
            mayaPythonFolder = Path.Combine(mayaLocation, "Python")
            if Directory.Exists(mayaPythonFolder):
                self.SetEnvironmentAndLogInfo("PYTHONHOME", mayaPythonFolder)

        # Start the maya process.
        self.StartMonitoredManagedProcess(self.ProcessName, self.Process)

    def SetEnvironmentAndLogInfo(self, envVar, value, description=None):
        """
        Sets an environment variable and prints a message to the log
        :param envVar: The environment variable that is going to be set
        :param value: The value that is the environment variable is being set to
        :param description: An optional description of the environment variable that will be added to the log.
        :return: Nothing
        """
        self.LogInfo(
            "Setting {0}{1} environment variable to {2} for this session".format(
                envVar,
                " ({0})".format(description) if description else "",
                value,
            )
        )
        self.SetProcessEnvironmentVariable(envVar, value)

    def WriteBatchScriptFile(self, scriptBuilder):
        """
        Writes out a MEL/python script that will be executed inside of Mayas.
        :param scriptBuilder: A string builder object containing the script to create.
        :return: The file path of the newly created script file.
        """
        self.scriptContents = scriptBuilder.ToString()

        if self.GetBooleanConfigEntryWithDefault("WriteScriptToLog", False):
            self.WriteScriptToLog()

        # Create the temp script file.
        outScriptFilename = Path.GetTempFileName()
        if SystemUtils.IsRunningOnWindows():
            with open(outScriptFilename, "wb") as f:
                f.write(
                    self.scriptContents.encode("mbcs")
                )  # On Windows, write it out as binary single-bytes per string using the current character set. This ensures that the resulting mel file doesn't have unicode characters, because maya will not be able to decode those characters correctly.
        else:
            File.WriteAllText(
                outScriptFilename, self.scriptContents
            )  # Non-Windows, we can write it out like this and the unicode characters will be written, but Maya will be able to handle the unicode encoded file.

        if SystemUtils.IsRunningOnLinux() or SystemUtils.IsRunningOnMac():
            os.chmod(
                outScriptFilename, os.stat(Path.GetTempFileName()).st_mode
            )

        return outScriptFilename

    def WriteScriptToLog(self, isError=False):
        """
        Prints the batch script, that performs the rendering inside Maya, to the render log. This will either be triggered by a plugin
        configuration option or by encountering a fatal error.
        :param isError: Determines how we log the script contents. Either as info or as a warning.
        :return: None
        """
        if self.isScriptLogged or not self.scriptContents:
            return

        # determine how we should log the script based on if it's an error or not
        logFunction = self.LogWarning if isError else self.LogInfo

        if isError:
            logFunction(
                "Encountered an error, logging render script contents for debugging:"
            )
        else:
            logFunction("Logging render script contents:")

        logFunction(
            "################################ SCRIPT LOG START ################################"
        )
        logFunction(self.scriptContents.replace("\r", ""))
        logFunction(
            "################################# SCRIPT LOG END #################################"
        )

        self.isScriptLogged = True

    def RenderTasks(self):
        self.LogInfo("Waiting until maya is ready to go")

        # isScriptLogged needs to be reset at the beginning of each task, in case WriteScriptToLog is turned on
        self.isScriptLogged = False

        # Wait until maya batch is ready to go.
        self.WaitForProcess()
        self.Process.ResetFrameCount()

        self.ScriptJob = self.GetBooleanPluginInfoEntryWithDefault(
            "ScriptJob", False
        )
        self.BifrostJob = self.GetBooleanPluginInfoEntryWithDefault(
            "BifrostJob", False
        )
        self.AlembicJob = self.GetBooleanPluginInfoEntryWithDefault(
            "AlembicJob", False
        )
        self.GeometryCacheJob = self.GetBooleanPluginInfoEntryWithDefault(
            "GeometryCacheJob", False
        )
        self.FluidCacheJob = self.GetBooleanPluginInfoEntryWithDefault(
            "FluidCacheJob", False
        )
        self.Animation = self.GetBooleanPluginInfoEntryWithDefault(
            "Animation", True
        )
        self.StartFrame = str(self.GetStartFrame())
        self.EndFrame = str(self.GetEndFrame())

        self.RenderDirectory = (
            self.GetPluginInfoEntryWithDefault("OutputFilePath", "")
            .strip()
            .replace("\\", "/")
        )
        self.RenderDirectory = RepositoryUtils.CheckPathMapping(
            self.RenderDirectory
        ).replace("\\", "/")
        if len(self.RenderDirectory) > 0 and self.RenderDirectory.endswith(
            "/"
        ):
            self.RenderDirectory = self.RenderDirectory.rstrip("/\\")
        if (
            SystemUtils.IsRunningOnWindows()
            and len(self.RenderDirectory) > 0
            and self.RenderDirectory.startswith("/")
            and not self.RenderDirectory.startswith("//")
        ):
            self.RenderDirectory = "/" + self.RenderDirectory

        self.LocalRendering = self.GetBooleanPluginInfoEntryWithDefault(
            "LocalRendering", False
        )

        if self.FirstTask:
            mayaBatchUtilsScriptFilename = os.path.join(
                self.GetPluginDirectory(), "MayaBatchUtils.mel"
            )
            self.LogInfo(
                "Importing Maya Batch Utils melscript: "
                + mayaBatchUtilsScriptFilename
            )
            self.FlushMonitoredManagedProcessStdout(self.ProcessName)
            self.WriteStdinToMonitoredManagedProcess(
                self.ProcessName,
                'eval( "source \\"'
                + mayaBatchUtilsScriptFilename.replace("\\", "/")
                + '\\";" )',
            )

            # Wait until eval is complete
            self.LogInfo(
                "Waiting for Maya Batch Utils melscript to finish loading"
            )
            self.WaitForProcess()

            self.LogInfo(
                "Importing Maya Batch Functions python script: %s"
                % os.path.join(
                    self.GetPluginDirectory(), "DeadlineMayaBatchFunctions.py"
                )
            )
            importFunctions = 'python("import sys; sys.path.append(\'%s\')");catch( python("import DeadlineMayaBatchFunctions") );' % self.GetPluginDirectory().replace(
                "\\", "/"
            )
            self.WriteStdinToMonitoredManagedProcess(
                self.ProcessName, importFunctions
            )

            # Wait until import is complete.
            self.LogInfo(
                "Waiting for Maya Batch Functions python script to finish importing"
            )
            self.WaitForProcess()

        if self.ScriptJob:
            self.LogInfo(">This is a MEL/Python Script Job")
            job = self.GetJob()

            self.LogInfo("+Reading Plugin Info")
            pluginInfo = {}
            pluginInfoTempList = job.GetJobPluginInfoKeys()
            for key in pluginInfoTempList:
                pluginInfo[key] = job.GetJobPluginInfoKeyValue(key)

            self.LogInfo("+Reading Extra Info")
            extraInfo = {}
            extraInfo["ExtraInfo0"] = job.JobExtraInfo0
            extraInfo["ExtraInfo1"] = job.JobExtraInfo1
            extraInfo["ExtraInfo2"] = job.JobExtraInfo2
            extraInfo["ExtraInfo3"] = job.JobExtraInfo3
            extraInfo["ExtraInfo4"] = job.JobExtraInfo4
            extraInfo["ExtraInfo5"] = job.JobExtraInfo5
            extraInfo["ExtraInfo6"] = job.JobExtraInfo6
            extraInfo["ExtraInfo7"] = job.JobExtraInfo7
            extraInfo["ExtraInfo8"] = job.JobExtraInfo8
            extraInfo["ExtraInfo9"] = job.JobExtraInfo9
            for key in job.ExtraInfoDictionary.Keys:
                extraInfo[key] = job.ExtraInfoDictionary[key]

            self.LogInfo(
                "+Building up a melscript of defined global variables"
            )
            # Build up a melscript to define global variables and run it
            scriptBuilder = StringBuilder()

            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                'string $sceneName = "'
                + self.SceneFile.replace("\\", "/")
                + '";'
            )
            scriptBuilder.AppendLine(
                'print ("Loading scene: " + $sceneName + "\\n");'
            )
            scriptBuilder.AppendLine()

            # If using dirmap for path mapping, need to load the scene now (it's not loaded via the command line in this case).
            # Only do this for the first task the Worker has picked up for this job.
            if (
                self.FirstTask
                and self.EnablePathMapping
                and self.DirmapPathMapping
            ):  # this check seems to be equivalent to self.DelayLoadScene
                self.CreateDelayLoadSceneMelscript(scriptBuilder)

            # double check at this point to make sure the scene is loaded. it could have been loaded by the command line, or by MEL script if delayed loading is enabled.
            scriptBuilder.AppendLine("string $checkScene = `file -q -sn`;")
            scriptBuilder.AppendLine('if ($checkScene=="")')
            scriptBuilder.AppendLine(
                '    error ("Cannot load scene \\"" + $sceneName + "\\". Please check the scene path, then try opening the scene on the machine which ran this job to troubleshoot the problem.\\n");'
            )
            scriptBuilder.AppendLine()

            # write deadline convenience functions
            scriptBuilder.AppendLine(
                "global proc string DeadlinePluginInfo (string $value){"
            )
            scriptBuilder.AppendLine("  switch($value) {")
            for key, value in pluginInfo.iteritems():
                scriptBuilder.AppendLine(
                    '      case "%s" : return "%s"; break;'
                    % (
                        key.strip().replace("\\", "\\\\"),
                        value.strip().replace("\\", "\\\\"),
                    )
                )
            scriptBuilder.AppendLine("  }")
            scriptBuilder.AppendLine('  return "";')
            scriptBuilder.AppendLine("}")
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                "global proc string DeadlineExtraInfo (string $value){"
            )
            scriptBuilder.AppendLine("  switch($value) {")
            for key, value in extraInfo.iteritems():
                scriptBuilder.AppendLine(
                    '      case "%s" : return "%s"; break;'
                    % (key.replace("\\", "\\\\"), value.replace("\\", "\\\\"))
                )
            scriptBuilder.AppendLine("  }")
            scriptBuilder.AppendLine('  return "";')
            scriptBuilder.AppendLine("}")
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine()

            self.LogInfo("+Building DeadlineValue")

            scriptBuilder.AppendLine(
                "global proc string DeadlineValue (string $value){"
            )
            scriptBuilder.AppendLine("  switch($value) {")
            # Format:
            # scriptBuilder.AppendLine("      case \<VALUE_NAME>\" : return \"" +        <RETURN_VALUE> +         "\"; break;")
            scriptBuilder.AppendLine(
                '      case "TestValue" : return "This is a test"; break;'
            )
            scriptBuilder.AppendLine(
                '      case "DataFileName" : return "'
                + self.SceneFile.replace("\\", "\\\\")
                + '"; break;'
            )
            scriptBuilder.AppendLine(
                '      case "PluginDirectory" : return "'
                + self.GetPluginDirectory().replace("\\", "\\\\")
                + '"; break;'
            )
            scriptBuilder.AppendLine(
                '      case "JobsDataDirectory" : return "'
                + self.GetJobsDataDirectory().replace("\\", "\\\\")
                + '"; break;'
            )
            scriptBuilder.AppendLine(
                '      case "StartFrame" : return "'
                + str(self.GetStartFrame())
                + '"; break;'
            )
            scriptBuilder.AppendLine(
                '      case "EndFrame" : return "'
                + str(self.GetEndFrame())
                + '"; break;'
            )
            scriptBuilder.AppendLine(
                '      case "ThreadNumber" : return "'
                + str(self.GetThreadNumber())
                + '"; break;'
            )
            scriptBuilder.AppendLine("  }")
            scriptBuilder.AppendLine('  return "";')
            scriptBuilder.AppendLine("}")
            scriptBuilder.AppendLine()

            # Create the temp script file.
            globalScriptFilename = Path.GetTempFileName()
            File.WriteAllText(globalScriptFilename, scriptBuilder.ToString())

            if SystemUtils.IsRunningOnLinux() or SystemUtils.IsRunningOnMac():
                os.chmod(
                    globalScriptFilename,
                    os.stat(Path.GetTempFileName()).st_mode,
                )

            self.LogInfo(
                "Executing defined global variables melscript: "
                + globalScriptFilename
            )

            self.FlushMonitoredManagedProcessStdout(self.ProcessName)
            self.WriteStdinToMonitoredManagedProcess(
                self.ProcessName,
                'eval( "source \\"'
                + globalScriptFilename.replace("\\", "/")
                + '\\";" )',
            )

            # Wait until render is complete.
            self.LogInfo("Waiting for global variables melscript to finish")
            self.WaitForProcess()

            # This is script job, so we'll just execute the given script.
            self.ScriptFilename = self.GetPluginInfoEntry("ScriptFilename")
            if not Path.IsPathRooted(self.ScriptFilename):
                self.ScriptFilename = Path.Combine(
                    self.GetJobsDataDirectory(), self.ScriptFilename
                )

            if not File.Exists(self.ScriptFilename):
                self.FailRender(
                    "MEL/Python Script File is missing: %s"
                    % self.ScriptFilename
                )

        elif self.BifrostJob:
            self.LogInfo(">This is a Bifrost Job")

            if self.LocalRendering:
                self.CurrentRenderDirectory = self.CreateTempDirectory(
                    "mayaSimOutput"
                ).replace("\\", "/")
                self.LogInfo(
                    "Simulating to local drive, will copy files and folders to final location after simulation is complete"
                )
            else:
                self.CurrentRenderDirectory = self.RenderDirectory
                self.LogInfo("Simulating to network drive")

            BifrostStatsScriptFilename = Path.Combine(
                self.GetPluginDirectory(), "BifrostMemUsage.mel"
            )
            self.LogInfo(
                "Executing Bifrost stats melscript: "
                + BifrostStatsScriptFilename
            )
            self.FlushMonitoredManagedProcessStdout(self.ProcessName)
            self.WriteStdinToMonitoredManagedProcess(
                self.ProcessName,
                'eval( "source \\"'
                + BifrostStatsScriptFilename.replace("\\", "/")
                + '\\";" )',
            )

            self.LogInfo("Creating melscript to execute")

            # Create the script to execute.
            # Version dependant work: We add the Format type for Bifrost 2016 and beyond.
            scriptBuilder = StringBuilder()
            scriptBuilder.AppendLine("// Starting Mel program")
            scriptBuilder.AppendLine()

            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                'string $sceneName = "'
                + self.SceneFile.replace("\\", "/")
                + '";'
            )
            scriptBuilder.AppendLine(
                'print ("Loading scene: " + $sceneName + "\\n");'
            )
            scriptBuilder.AppendLine()
            # If using dirmap for path mapping, need to load the scene now (it's not loaded via the command line in this case).
            # Only do this for the first task the Worker has picked up for this job.
            if (
                self.FirstTask
                and self.EnablePathMapping
                and self.DirmapPathMapping
            ):  # this check seems to be equivalent to self.DelayLoadScene
                self.CreateDelayLoadSceneMelscript(scriptBuilder)

            if self.Version == 2015:
                scriptBuilder.AppendLine(
                    "proc simulateIt( int $start, int $end, string $outdir ) {"
                )
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine(
                    "    // Make sure Bifrost plugin is loaded."
                )
                scriptBuilder.AppendLine(
                    '    if( !`pluginInfo -q -l "BifrostMain"` ) {'
                )
                scriptBuilder.AppendLine(
                    '        loadPlugin( "BifrostMain" );'
                )
                scriptBuilder.AppendLine(
                    '        loadPlugin( "Bifrostshellnode" );'
                )
                scriptBuilder.AppendLine(
                    '        loadPlugin( "Bifrostvisplugin" );'
                )
                scriptBuilder.AppendLine("    } // end if")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine(
                    "    // Create simple expression to run BifrostMemUsage() on each timestep."
                )
                scriptBuilder.AppendLine(
                    '    expression -s "BifrostMemUsage()";'
                )
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("    // Select all containers.")
                scriptBuilder.AppendLine(
                    "    string $containers[] = `ls -type bifrostContainer`;"
                )
                scriptBuilder.AppendLine("    if( !size( $containers ) )")
                scriptBuilder.AppendLine("        error( `pwd` );")
                scriptBuilder.AppendLine("    // end if")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("    // Report.")
                scriptBuilder.AppendLine(
                    "    for( $container in $containers )"
                )
                scriptBuilder.AppendLine(
                    '        print( "// Found container: "+$container+".\\n" );'
                )
                scriptBuilder.AppendLine("    // end for")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("    // Select container(s).")
                scriptBuilder.AppendLine("    select -r $containers;")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("    // Run simulation.")
                scriptBuilder.AppendLine("    doCreateBifrostCache 1 { ")
                scriptBulider.AppendLine(
                    '        "0",       // mode. 0 means use strict start and end frames provided.'
                )
                scriptBuilder.AppendLine("        $start,    // start frame")
                scriptBuilder.AppendLine("        $end,      // end frame")
                scriptBuilder.AppendLine(
                    "        $outdir,   // name of cache directory"
                )
                scriptBuilder.AppendLine(
                    '        "",        // Base name of cache files. If blank, use the container name as cache file.'
                )
                scriptBuilder.AppendLine("    };")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("} // end BifrostBatchSim")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine(
                    "simulateIt( "
                    + self.StartFrame
                    + ", "
                    + self.EndFrame
                    + ', "'
                    + self.CurrentRenderDirectory
                    + '" );'
                )

            elif self.Version > 2015:
                self.BifrostCompressionFormat = self.GetPluginInfoEntry(
                    "BifrostCompressionFormat"
                )

                scriptBuilder.AppendLine(
                    "proc simulateIt( int $start, int $end, string $outdir, int $format ) {"
                )
                scriptBuilder.AppendLine()
                if self.Version == 2016:
                    scriptBuilder.AppendLine(
                        "    // Make sure Bifrost plugin is loaded."
                    )
                    scriptBuilder.AppendLine(
                        '    if( !`pluginInfo -q -l "BifrostMain"` ) {'
                    )
                    scriptBuilder.AppendLine(
                        '        loadPlugin( "BifrostMain" );'
                    )
                    scriptBuilder.AppendLine("    } // end if")

                scriptBuilder.AppendLine(
                    '    if( !`pluginInfo -q -l "bifrostshellnode"` ) {'
                )
                scriptBuilder.AppendLine(
                    '        loadPlugin( "bifrostshellnode" );'
                )
                scriptBuilder.AppendLine("    } // end if")
                scriptBuilder.AppendLine(
                    '    if( !`pluginInfo -q -l "bifrostvisplugin"` ) {'
                )
                scriptBuilder.AppendLine(
                    '        loadPlugin( "bifrostvisplugin" );'
                )
                scriptBuilder.AppendLine("    } // end if")

                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine(
                    "    // Create simple expression to run BifrostMemUsage() on each timestep."
                )
                scriptBuilder.AppendLine(
                    '    expression -s "BifrostMemUsage()";'
                )
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("    // Select all containers.")
                scriptBuilder.AppendLine(
                    "    string $containers[] = `ls -type bifrostContainer`;"
                )
                scriptBuilder.AppendLine("    if( !size( $containers ) )")
                scriptBuilder.AppendLine("        error( `pwd` );")
                scriptBuilder.AppendLine("    // end if")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("    // Report.")
                scriptBuilder.AppendLine(
                    "    for( $container in $containers )"
                )
                scriptBuilder.AppendLine(
                    '        print( "// Found container: "+$container+".\\n" );'
                )
                scriptBuilder.AppendLine("    // end for")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("    // Select container(s).")
                scriptBuilder.AppendLine("    select -r $containers;")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("    // Run simulation.")
                scriptBuilder.AppendLine("    doCreateBifrostCache 2 { ")
                scriptBuilder.AppendLine(
                    '        "0",       // mode. 0 means use strict start and end frames provided.'
                )
                scriptBuilder.AppendLine("        $start,    // start frame")
                scriptBuilder.AppendLine("        $end,      // end frame")
                scriptBuilder.AppendLine(
                    "        $outdir,   // name of cache directory"
                )
                scriptBuilder.AppendLine(
                    '        "",        // Base name of cache files. If blank, use the container name as cache file.'
                )
                scriptBuilder.AppendLine(
                    '        "bif",     // name of cache format'
                )
                scriptBuilder.AppendLine(
                    "        $format        // index of cache compression format"
                )
                scriptBuilder.AppendLine("    };")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine("} // end BifrostBatchSim")
                scriptBuilder.AppendLine()
                scriptBuilder.AppendLine(
                    "simulateIt( "
                    + self.StartFrame
                    + ", "
                    + self.EndFrame
                    + ', "'
                    + self.CurrentRenderDirectory
                    + '", '
                    + self.BifrostCompressionFormat
                    + " );"
                )

            # Version independant
            self.ScriptFilename = self.WriteBatchScriptFile(scriptBuilder)

        elif self.AlembicJob:
            self.LogInfo(">This is an Alembic Job")
            self.AlembicFormat = self.GetPluginInfoEntry("AlembicFormatOption")

            self.AlembicFile = (
                self.RenderDirectory
                + "/"
                + self.GetPluginInfoEntry("OutputFile")
            )

            if not self.AlembicFile.endswith(".abc"):
                self.AlembicFile += ".abc"

            # init keys
            if self.GetBooleanPluginInfoEntryWithDefault("Verbose", False):
                self.AlembicArgs += " -v "

            if self.GetBooleanPluginInfoEntryWithDefault("NoNormals", False):
                self.AlembicKeys += " -nn "
            if self.GetBooleanPluginInfoEntryWithDefault(
                "RenderableOnly", False
            ):
                self.AlembicKeys += " -ro "
            if self.GetBooleanPluginInfoEntryWithDefault(
                "StripNamespaces", False
            ):
                self.AlembicKeys += " -sn "
            if self.GetBooleanPluginInfoEntryWithDefault("UVWrite", False):
                self.AlembicKeys += " -uv "
            if self.GetBooleanPluginInfoEntryWithDefault(
                "WriteColorSets", False
            ):
                self.AlembicKeys += " -wcs "
            if self.GetBooleanPluginInfoEntryWithDefault(
                "WriteFaceSets", False
            ):
                self.AlembicKeys += " -wfs "
            if self.GetBooleanPluginInfoEntryWithDefault(
                "WholeFrameGeo", False
            ):
                self.AlembicKeys += " -wfg "
            if self.GetBooleanPluginInfoEntryWithDefault("WorldSpace", False):
                self.AlembicKeys += " -ws "
            if self.GetBooleanPluginInfoEntryWithDefault(
                "FilterEulerRotations", False
            ):
                self.AlembicKeys += " -ef "
            if self.GetBooleanPluginInfoEntryWithDefault(
                "WriteCreases", False
            ):
                self.AlembicKeys += " -wc "
            if self.GetBooleanPluginInfoEntryWithDefault(
                "WriteVisibility", False
            ):
                self.AlembicKeys += " -wv "

            if self.GetBooleanPluginInfoEntryWithDefault(
                "AlembicSubFrames", False
            ):
                self.AlembicKeys += " -frs %s " % str(
                    self.GetFloatPluginInfoEntryWithDefault(
                        "AlembicLowSubFrame", -0.2
                    )
                )
                self.AlembicKeys += " -frs %s " % str(
                    self.GetFloatPluginInfoEntryWithDefault(
                        "AlembicHighSubFrame", 0.2
                    )
                )

            alembicAttributes = self.GetPluginInfoEntryWithDefault(
                "AlembicAttributes", ""
            )
            alembicAttributePrefix = self.GetPluginInfoEntryWithDefault(
                "AlembicAttributePrefix", ""
            )

            if not alembicAttributes == "":
                for attr in alembicAttributes.split(","):
                    self.AlembicKeys += " -attr %s " % attr.strip()

            if not alembicAttributePrefix == "":
                for attr in alembicAttributePrefix.split(","):
                    self.AlembicKeys += " -attrPrefix %s " % attr.strip()

            # Roots for selected items go between -df and -f flags.
            self.AlembicSelection = self.GetPluginInfoEntryWithDefault(
                "AlembicSelection", "All"
            )
            # -root |pPyramid1 -root |camera1
            alembicSelectArgs = " "

            if self.AlembicSelection != "All":
                alembicSelectionList = self.AlembicSelection.split(
                    ","
                )  # Map all the comma-separated selected scene members to a list

                for item in alembicSelectionList:
                    if item == "":
                        item = "|"

                    alembicSelectArgs += " -root " + item + " "

            self.AlembicArgs += (
                ' -j "'
                + self.AlembicKeys
                + " -fr "
                + self.StartFrame
                + " "
                + self.EndFrame
                + " -df "
                + self.AlembicFormat
                + alembicSelectArgs
                + ' -f \\"'
                + self.AlembicFile
                + '\\""'
            )
            # Alembic workload
            # Get all of the needed Alembic attributes, then build the -j args string. Pass that string to scriptBuilder
            # Available right now: start frame, end frame, directory, filename
            scriptBuilder = StringBuilder()

            scriptBuilder.AppendLine("// Starting Mel program")
            scriptBuilder.AppendLine()

            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                'string $sceneName = "'
                + self.SceneFile.replace("\\", "/")
                + '";'
            )
            scriptBuilder.AppendLine(
                'print ("Loading scene: " + $sceneName + "\\n");'
            )
            scriptBuilder.AppendLine()

            # If using dirmap for path mapping, need to load the scene now (it's not loaded via the command line in this case).
            # Only do this for the first task the Worker has picked up for this job.
            if (
                self.FirstTask
                and self.EnablePathMapping
                and self.DirmapPathMapping
            ):  # this check seems to be equivalent to self.DelayLoadScene
                self.CreateDelayLoadSceneMelscript(scriptBuilder)

            scriptBuilder.AppendLine(' loadPlugin("AbcExport"); ')
            scriptBuilder.AppendLine(" AbcExport " + self.AlembicArgs + ";")

            self.ScriptFilename = self.WriteBatchScriptFile(scriptBuilder)

        elif self.GeometryCacheJob:
            self.LogInfo(">This is a Geometry Caching Job")
            # First load geometry cache params
            self.GeoFilePerFrame = self.GetBooleanPluginInfoEntryWithDefault(
                "OneFilePerFrame", False
            )
            self.GeoCacheFileName = self.GetPluginInfoEntry("GeoCacheFileName")
            self.OneFilePerGeometry = self.GetPluginInfoEntry(
                "OneFilePerGeometry"
            )
            self.PointsAsDblorFlt = self.GetPluginInfoEntryWithDefault(
                "SavePointsAs", "Float"
            )  # Corresponds to 0 or 1 (dbl/flt)
            self.PointsInLocalOrWorld = self.GetPluginInfoEntryWithDefault(
                "SavePointsIn", "World"
            )  # Corresponds to 0 or 1 (loc/wld)
            self.GeoCacheFormat = self.GetPluginInfoEntry("CacheFormat")
            if self.GeoCacheFormat != "mcc":
                self.GeoCacheFormat = "mcx"

            self.SelectedGeometry = self.GetPluginInfoEntry(
                "SelectedGeometry"
            ).replace(",", " ")

            if self.SelectedGeometry == "All":
                cacheSelectArgs = " `listTransforms -geometry`"
            elif len(self.SelectedGeometry) > 0:
                cacheSelectArgs = self.SelectedGeometry
            else:
                cacheSelectArgs = '; error("No Geometry Selected") '

            if self.GeoFilePerFrame:
                self.GeoFilePerFrame = "OneFilePerFrame"
            else:
                self.GeoFilePerFrame = "OneFile"
            # To check if all selected: SelectedGeometry = "All"
            # Pass in selected Geometry. On MEL side: put GUI together
            scriptBuilder = StringBuilder()
            scriptBuilder.AppendLine("// Starting Mel program")
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                'string $sceneName = "'
                + self.SceneFile.replace("\\", "/")
                + '";'
            )
            scriptBuilder.AppendLine(
                'print ("Loading scene: " + $sceneName + "\\n");'
            )
            scriptBuilder.AppendLine()

            # If using dirmap for path mapping, need to load the scene now (it's not loaded via the command line in this case).
            # Only do this for the first task the Worker has picked up for this job.
            if (
                self.FirstTask
                and self.EnablePathMapping
                and self.DirmapPathMapping
            ):  # this check seems to be equivalent to self.DelayLoadScene
                self.CreateDelayLoadSceneMelscript(scriptBuilder)

            scriptBuilder.AppendLine(
                '    string $geoArgs[] = { "0",    // Time Range Mode '
            )
            scriptBuilder.AppendLine(
                '    "' + self.StartFrame + '",    // Start Frame '
            )
            scriptBuilder.AppendLine(
                '    "' + self.EndFrame + '",    // End Frame '
            )
            scriptBuilder.AppendLine(
                '    "' + self.GeoFilePerFrame + '",   // File Distribution '
            )
            scriptBuilder.AppendLine('    "0",    // Refresh during cache ')
            scriptBuilder.AppendLine(
                '    "' + self.RenderDirectory + '",    // Output Directory '
            )
            scriptBuilder.AppendLine(
                '    "'
                + self.OneFilePerGeometry
                + '",    // One Cache Per Geometry '
            )
            scriptBuilder.AppendLine(
                '    "' + self.GeoCacheFileName + '",    // Output File Name '
            )
            scriptBuilder.AppendLine('    "1",    // Use name as prefix ')
            scriptBuilder.AppendLine(
                '    "add",    // Action to Perform '
            )  # Is this one going to be customizable?
            scriptBuilder.AppendLine('    "1",    // Force Save ')
            scriptBuilder.AppendLine('    "1",    // Simulation Rate ')
            scriptBuilder.AppendLine('    "1",    // Sample Multiplier ')
            scriptBuilder.AppendLine(
                '    "1",    // Inheret Replace Modifications '
            )
            scriptBuilder.AppendLine(
                '    " '
                + str(int(self.PointsAsDblorFlt == "Float"))
                + '", // Store points as Double (0) or Float (1) '
            )
            scriptBuilder.AppendLine(
                '    "'
                + self.GeoCacheFormat
                + '", // File Format (mcc or mcx) '
            )
            scriptBuilder.AppendLine(
                '    "'
                + str(int(self.PointsInLocalOrWorld == "World"))
                + '" }; // Points in Local (0) or World (1) '
            )
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine("    //--------------------- ")
            scriptBuilder.AppendLine("    // Selection Procedure: ")
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                "    select -r "
                + cacheSelectArgs
                + " ; // Grab the geometry selected earlier by the user, or throw an error if none are selected "
            )
            scriptBuilder.AppendLine("    string $selection[] = `ls -sl`; ")
            scriptBuilder.AppendLine("    for( $item in $selection ) ")
            scriptBuilder.AppendLine(
                '        print("Found Geometry: " + $item ); '
            )
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                "    doCreateGeometryCache(6, $geoArgs); // The actual workload "
            )

            self.ScriptFilename = self.WriteBatchScriptFile(scriptBuilder)

        elif self.FluidCacheJob:
            self.LogInfo(">This is a Fluid Caching Job")

            self.FluidFilePerFrame = self.GetBooleanPluginInfoEntryWithDefault(
                "OneFilePerFrame", False
            )
            self.FluidCacheFileName = self.GetPluginInfoEntry(
                "FluidCacheFileName"
            )
            self.OneFilePerFluid = self.GetPluginInfoEntry("OneFilePerFluid")
            self.FluidCacheFormat = self.GetPluginInfoEntry("CacheFormat")
            if self.FluidCacheFormat != "mcc":
                self.FluidCacheFormat = "mcx"

            self.SelectedFluids = self.GetPluginInfoEntry(
                "SelectedFluids"
            ).replace(",", " ")

            if self.SelectedFluids == "All":
                cacheSelectArgs = ' `listTransforms "-type fluidShape"` '
            elif len(self.SelectedFluids) > 0:
                cacheSelectArgs = self.SelectedFluids
            else:
                cacheSelectArgs = '; error("No Fluids Were Selected") '

            if self.FluidFilePerFrame:
                self.FluidFilePerFrame = "OneFilePerFrame"
            else:
                self.FluidFilePerFrame = "OneFile"
            # To check if all selected: SelectedGeometry = "All"
            # Pass in selected Geometry. On MEL side: put GUI together
            scriptBuilder = StringBuilder()
            scriptBuilder.AppendLine("// Starting Mel program")
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                'string $sceneName = "'
                + self.SceneFile.replace("\\", "/")
                + '";'
            )
            scriptBuilder.AppendLine(
                'print ("Loading scene: " + $sceneName + "\\n");'
            )

            if (
                self.FirstTask
                and self.EnablePathMapping
                and self.DirmapPathMapping
            ):  # this check seems to be equivalent to self.DelayLoadScene
                self.CreateDelayLoadSceneMelscript(scriptBuilder)

            scriptBuilder.AppendLine(
                '    string $fluidArgs[] = { "0",    // Time Range Mode '
            )
            scriptBuilder.AppendLine(
                '    "' + self.StartFrame + '", // Start Frame '
            )
            scriptBuilder.AppendLine(
                '    "' + self.EndFrame + '", // End Frame '
            )
            scriptBuilder.AppendLine(
                '    "'
                + self.FluidFilePerFrame
                + '", // Distribution: 1 file or 1 file per frame'
            )
            scriptBuilder.AppendLine('    "1", // Refresh during caching ')
            scriptBuilder.AppendLine(
                '    "' + self.RenderDirectory + '", // Output Path '
            )
            scriptBuilder.AppendLine(
                '    "'
                + self.OneFilePerFluid
                + '",    // One Cache Per Fluid '
            )
            scriptBuilder.AppendLine(
                '    "'
                + self.FluidCacheFileName
                + '",    // Output File Name '
            )
            scriptBuilder.AppendLine('    "1",    // Use name as prefix ')
            scriptBuilder.AppendLine('    "add",    // Action to Perform ')
            scriptBuilder.AppendLine('    "1",    // Force Save ')
            scriptBuilder.AppendLine('    "1",    // Simulation Rate ')
            scriptBuilder.AppendLine('    "1",    // Sample Multiplier ')
            scriptBuilder.AppendLine(
                '    "1",    // Inheret Replace Modifications '
            )
            scriptBuilder.AppendLine('    "0",    // Double as Float ')
            scriptBuilder.AppendLine(
                '    "' + self.FluidCacheFormat + '", // mcc or mcx '
            )
            scriptBuilder.AppendLine('    "1",    // Density ')
            scriptBuilder.AppendLine('    "1",    // Velocity ')
            scriptBuilder.AppendLine('    "1",    // Temperature ')
            scriptBuilder.AppendLine('    "1",    // Fuel ')
            scriptBuilder.AppendLine('    "1",    // Color ')
            scriptBuilder.AppendLine('    "1",    // Texture ')
            scriptBuilder.AppendLine('    "1" };    // Falloff ')
            scriptBuilder.AppendLine("    //--------------------- ")
            scriptBuilder.AppendLine("    // Selection Procedure: ")
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                "    select -r "
                + cacheSelectArgs
                + " ; // Grab the Fluids selected earlier by the user, or throw an error if none are selected "
            )
            scriptBuilder.AppendLine("    string $selection[] = `ls -sl`; ")
            scriptBuilder.AppendLine("    for( $item in $selection ) ")
            scriptBuilder.AppendLine(
                '        print("Found Fluid: " + $item ); '
            )
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                "    doCreateFluidCache(5, $fluidArgs); // The actual work "
            )

            self.ScriptFilename = self.WriteBatchScriptFile(scriptBuilder)

        else:
            self.LogInfo(">This is a Render Job")

            # Get render options so we can build the script to execute.
            self.RegionRendering = self.GetBooleanPluginInfoEntryWithDefault(
                "RegionRendering", False
            )
            self.SingleRegionJob = self.IsTileJob()
            self.SingleRegionFrame = str(self.GetStartFrame())
            self.SingleRegionIndex = self.GetCurrentTaskId()

            if self.RegionRendering and self.SingleRegionJob:
                self.StartFrame = str(self.SingleRegionFrame)
                self.EndFrame = str(self.SingleRegionFrame)
            else:
                self.StartFrame = str(self.GetStartFrame())
                self.EndFrame = str(self.GetEndFrame())

            frameNumberOffset = self.GetIntegerPluginInfoEntryWithDefault(
                "FrameNumberOffset", 0
            )
            allowsFrameRenumbering = not (self.Renderer == "vray")
            if self.GetBooleanPluginInfoEntryWithDefault(
                "RenderHalfFrames", False
            ):
                self.LogInfo("Rendering half frames")
                if allowsFrameRenumbering:
                    self.ByFrame = "0.5"
                    self.RenumberFrameStart = str(
                        (self.GetStartFrame() * 2) + (frameNumberOffset * 2)
                    )
                    self.EndFrame = (
                        self.EndFrame + ".5"
                    )  # Need to add an extra 1/2 frame to the end of the end frame
                else:
                    self.FailRender(
                        "Rendering Half Frames is not supported by this renderer."
                    )
            else:
                self.ByFrame = "1"
                if frameNumberOffset != 0:
                    if allowsFrameRenumbering:
                        self.RenumberFrameStart = str(
                            self.GetStartFrame() + frameNumberOffset
                        )
                    else:
                        self.LogWarning(
                            "Renumbering Frames is not supported by this renderer."
                        )

            self.LogInfo("Rendering with " + self.Renderer)

            if self.RegionRendering and self.SingleRegionJob:
                self.ImagePrefix = self.GetPluginInfoEntryWithDefault(
                    "RegionPrefix" + self.SingleRegionIndex, ""
                ).replace("\\", "/")
            else:
                self.ImagePrefix = (
                    self.GetPluginInfoEntryWithDefault("OutputFilePrefix", "")
                    .strip()
                    .replace("\\", "/")
                )

            if (
                self.LocalRendering
                and self.Renderer != "mentalrayexport"
                and self.Renderer != "vrayexport"
                and self.Renderer != "rendermanexport"
            ):
                if len(self.RenderDirectory) == 0:
                    self.LocalRendering = False
                    self.CurrentRenderDirectory = self.RenderDirectory
                    self.LogInfo(
                        "OutputFilePath was not specified in the plugin info file, rendering to network drive"
                    )
                else:
                    self.CurrentRenderDirectory = self.CreateTempDirectory(
                        "mayaOutput"
                    ).replace("\\", "/")
                    self.LogInfo(
                        "Rendering to local drive, will copy files and folders to final location after render is complete"
                    )
            else:
                self.LocalRendering = False
                self.CurrentRenderDirectory = self.RenderDirectory
                self.LogInfo("Rendering to network drive")

            self.RenderLayer = self.GetPluginInfoEntryWithDefault(
                "RenderLayer", ""
            ).strip()
            self.UsingRenderLayers = self.GetBooleanPluginInfoEntryWithDefault(
                "UsingRenderLayers", False
            )

            self.Camera = self.GetPluginInfoEntryWithDefault(
                "Camera", ""
            ).strip()
            self.Width = self.GetPluginInfoEntryWithDefault(
                "ImageWidth", ""
            ).strip()
            self.Height = self.GetPluginInfoEntryWithDefault(
                "ImageHeight", ""
            ).strip()
            self.Scale = self.GetPluginInfoEntryWithDefault(
                "ImageScale", ""
            ).strip()
            self.AspectRatio = self.GetPluginInfoEntryWithDefault(
                "AspectRatio", ""
            ).strip()
            self.SkipExistingFrames = self.GetBooleanPluginInfoEntryWithDefault(
                "SkipExistingFrames", False
            )

            self.MotionBlur = (
                self.GetPluginInfoEntryWithDefault("MotionBlur", "")
                .strip()
                .lower()
            )
            if self.MotionBlur == "true":
                self.MotionBlur = "1"
            elif self.MotionBlur == "false":
                self.Motionblur = "0"

            self.AntiAliasing = self.GetPluginInfoEntryWithDefault(
                "AntiAliasing", ""
            ).strip()
            self.Threads = self.GetThreadCount()

            # Get krakatoa information from .job file
            if self.Renderer == "mayakrakatoa":

                # check if parameters exist in the .job file, indicating the job was initiated through the Maya interface.
                try:
                    self.GetPluginInfoEntry("KrakatoaUseEmission")
                except:
                    self.KrakatoaJobFileContainsKrakatoaParameters = False

                if self.KrakatoaJobFileContainsKrakatoaParameters:
                    self.KrakatoaFinalPassDensity = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaFinalPassDensity", "7.0"
                    ).strip()
                    self.KrakatoaFinalPassDensityExponent = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaFinalPassDensityExponent", "-1"
                    ).strip()

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaUseLightingPassDensity", False
                    ):
                        self.KrakatoaUseLightingPassDensity = "1"
                    else:
                        self.KrakatoaUseLightingPassDensity = "0"

                    self.KrakatoaLightingPassDensity = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaLightingPassDensity", "1.0"
                    ).strip()
                    self.KrakatoaLightingPassDensityExponent = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaLightingPassDensityExponent", "-1"
                    ).strip()

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaUseEmissionStrength", False
                    ):
                        self.KrakatoaUseEmissionStrength = "1"
                    else:
                        self.KrakatoaUseEmissionStrength = "0"

                    self.KrakatoaEmissionStrength = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaEmissionStrength", "1.0"
                    ).strip()
                    self.KrakatoaEmissionStrengthExponent = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaEmissionStrengthExponent", "-1"
                    ).strip()

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaUseEmission", False
                    ):
                        self.KrakatoaUseEmission = "1"
                    else:
                        self.KrakatoaUseEmission = "0"

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaUseAbsorption", False
                    ):
                        self.KrakatoaUseAbsorption = "1"
                    else:
                        self.KrakatoaUseAbsorption = "0"

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaEnableMotionBlur", False
                    ):
                        self.KrakatoaEnableMotionBlur = "1"
                    else:
                        self.KrakatoaEnableMotionBlur = "0"

                    self.KrakatoaMotionBlurParticleSegments = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaMotionBlurParticleSegments", "2"
                    ).strip()

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaJitteredMotionBlur", False
                    ):
                        self.KrakatoaJitteredMotionBlur = "1"
                    else:
                        self.KrakatoaJitteredMotionBlur = "0"

                    self.KrakatoaShutterAngle = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaShutterAngle", "180.0"
                    ).strip()

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaEnableDOF", False
                    ):
                        self.KrakatoaEnableDOF = "1"
                    else:
                        self.KrakatoaEnableDOF = "0"

                    self.KrakatoaSampleRateDOF = self.GetPluginInfoEntryWithDefault(
                        "KrakatoaSampleRateDOF", "0.1"
                    ).strip()

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaEnableMatteObjects", False
                    ):
                        self.KrakatoaEnableMatteObjects = "1"
                    else:
                        self.KrakatoaEnableMatteObjects = "0"

                    if self.GetPluginInfoEntryWithDefault(
                        "KrakatoaRenderingMethod", "Particles"
                    ).strip():
                        self.KrakatoaRenderingMethod = "0"
                    else:
                        self.KrakatoaRenderingMethod = "1"
                        self.KrakatoaVoxelSize = self.GetPluginInfoEntryWithDefault(
                            "KrakatoaVoxelSize", "0.5"
                        ).strip()
                        self.KrakatoaVoxelFliterRadius = self.GetPluginInfoEntryWithDefault(
                            "KrakatoaVoxelFilterRadius", "1"
                        ).strip()

                    if self.GetBooleanPluginInfoEntryWithDefault(
                        "KrakatoaForceEXROutput", True
                    ):
                        self.KrakatoaForceEXROutput = "1"
                    else:
                        self.KrakatoaForceEXROutput = "0"

            if self.RegionRendering:
                if self.SingleRegionJob:
                    self.Left = self.GetPluginInfoEntryWithDefault(
                        "RegionLeft" + self.SingleRegionIndex, "0"
                    )
                    self.Right = self.GetPluginInfoEntryWithDefault(
                        "RegionRight" + self.SingleRegionIndex, "0"
                    )
                    self.Top = self.GetPluginInfoEntryWithDefault(
                        "RegionTop" + self.SingleRegionIndex, "0"
                    )
                    self.Bottom = self.GetPluginInfoEntryWithDefault(
                        "RegionBottom" + self.SingleRegionIndex, "0"
                    )
                else:
                    self.Left = self.GetPluginInfoEntryWithDefault(
                        "RegionLeft", "0"
                    ).strip()
                    self.Right = self.GetPluginInfoEntryWithDefault(
                        "RegionRight", "0"
                    ).strip()
                    self.Top = self.GetPluginInfoEntryWithDefault(
                        "RegionTop", "0"
                    ).strip()
                    self.Bottom = self.GetPluginInfoEntryWithDefault(
                        "RegionBottom", "0"
                    ).strip()
            self.LogInfo("Creating melscript to execute render")

            # Create the script to execute.
            scriptBuilder = StringBuilder()
            scriptBuilder.AppendLine("// Starting Mel program")
            scriptBuilder.AppendLine()

            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine("proc renderIt(string $name) {")
            scriptBuilder.AppendLine()

            scriptBuilder.AppendLine(self.GetInitializeCommand())

            # local asset caching
            if self.FirstTask and self.GetBooleanPluginInfoEntryWithDefault(
                "UseLocalAssetCaching", False
            ):
                assetToolsScriptFilename = os.path.join(
                    self.GetPluginDirectory(), "AssetTools.mel"
                )
                self.LogInfo(
                    "Importing scene asset introspection melscript: "
                    + assetToolsScriptFilename
                )
                self.FlushMonitoredManagedProcessStdout(self.ProcessName)
                self.WriteStdinToMonitoredManagedProcess(
                    self.ProcessName,
                    'eval( "source \\"'
                    + assetToolsScriptFilename.replace("\\", "/")
                    + '\\";" )',
                )  # The function to do LAC is in this external .mel script.
                scriptBuilder.AppendLine(self.LocalAssetCachingCommand())

            # If not rendering an animation, don't specify the animation parameters so that the output file isn't padded.
            if self.Animation:
                scriptBuilder.AppendLine(self.GetStartFrameCommand())
                scriptBuilder.AppendLine(self.GetEndFrameCommand())
                scriptBuilder.AppendLine(self.GetByFrameCommand())
                scriptBuilder.AppendLine(self.GetRenumberFrameStartCommand())

            scriptBuilder.AppendLine(self.GetImagePrefixCommand())
            scriptBuilder.AppendLine(self.GetRenderDirectoryCommand())

            scriptBuilder.AppendLine(self.GetCameraCommand())
            scriptBuilder.AppendLine(self.GetWidthCommand())
            scriptBuilder.AppendLine(self.GetHeightCommand())
            scriptBuilder.AppendLine(self.GetScaleCommand())
            scriptBuilder.AppendLine(self.GetResolutionCommand())
            # scriptBuilder.AppendLine( self.GetAspectRatioCommand() )
            scriptBuilder.AppendLine(self.GetSkipExistingFramesCommand())

            scriptBuilder.AppendLine(self.GetAntiAliasingCommand())
            scriptBuilder.AppendLine(self.GetMotionBlurCommand())
            scriptBuilder.AppendLine(self.GetThreadsCommand())
            scriptBuilder.AppendLine(self.GetMemoryCommand())
            scriptBuilder.AppendLine(self.GetVerboseCommand())

            scriptBuilder.AppendLine(self.GetRenderLayerCommand())
            scriptBuilder.AppendLine(self.GetRegionCommand())
            scriptBuilder.AppendLine(self.GetMiscCommands())

            scriptBuilder.AppendLine(self.GetRenderCommand())

            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine("}")

            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine("//")
            scriptBuilder.AppendLine("// Main part")
            scriptBuilder.AppendLine("//")
            scriptBuilder.AppendLine("proc mainDeadlineRender() {")
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine(
                'string $sceneName = "'
                + self.SceneFile.replace("\\", "/")
                + '";'
            )
            scriptBuilder.AppendLine(
                'print ("Loading scene: " + $sceneName + "\\n");'
            )
            scriptBuilder.AppendLine()

            # If using dirmap for path mapping, need to load the scene now (it's not loaded via the command line in this case).
            # Only do this for the first task the Worker has picked up for this job.
            if self.EnablePathMapping:
                if self.FirstTask:
                    if (
                        self.DirmapPathMapping
                    ):  # this check seems to be equivalent to self.DelayLoadScene
                        self.CreateDelayLoadSceneMelscript(scriptBuilder)

                    if self.XGenPathMapping:
                        mappings = [
                            mappingPair
                            for mappingPair in RepositoryUtils.GetPathMappings()
                            if mappingPair[1]
                        ]
                        if len(mappings) > 0:
                            scriptBuilder.AppendLine()
                            scriptBuilder.AppendLine(
                                'string $deadlineMappings[] = { "'
                                + '", "'.join(
                                    mappingComponent.replace("\\", "/")
                                    for mappingPair in mappings
                                    for mappingComponent in mappingPair
                                )
                                + '" };'
                            )
                            scriptBuilder.AppendLine(
                                'print("------[ XGen path mapping STARTED ]------\\n");'
                            )
                            scriptBuilder.AppendLine(
                                "if( catch( mapXGen( $deadlineMappings ) ) ) {"
                            )
                            scriptBuilder.AppendLine(
                                'print("------[ XGen path mapping FAILED ]------\\n");'
                            )
                            scriptBuilder.AppendLine("} else {")
                            scriptBuilder.AppendLine(
                                'print("------[ XGen path mapping SUCCEEDED ]------\\n");'
                            )
                            scriptBuilder.AppendLine("}")
                            scriptBuilder.AppendLine()

                if self.Renderer in ["arnold", "arnoldexport"]:
                    scriptBuilder.AppendLine(
                        "catch(python( \"DeadlineMayaBatchFunctions.performArnoldPathmapping( %s, %s, '%s')\" ) );"
                        % (
                            self.StartFrame,
                            self.EndFrame,
                            self.TempThreadDirectory.replace("\\", "/"),
                        )
                    )

            # double check at this point to make sure the scene is loaded. it could have been loaded by the command line, or by MEL script if delayed loading is enabled.
            scriptBuilder.AppendLine("string $checkScene = `file -q -sn`;")
            scriptBuilder.AppendLine('if ($checkScene=="") {')
            scriptBuilder.AppendLine(
                'error ("Cannot load scene \\"" + $sceneName + "\\". Please check the scene path, then try opening the scene on the machine which ran this job to troubleshoot the problem.\\n");'
            )
            scriptBuilder.AppendLine(
                "} else if (catch(`renderIt($sceneName)`)) {"
            )
            scriptBuilder.AppendLine('error ("Render failed.\\n");')
            scriptBuilder.AppendLine("} else {")
            scriptBuilder.AppendLine('print ("Render completed.\\n");')
            scriptBuilder.AppendLine("}")
            scriptBuilder.AppendLine()
            scriptBuilder.AppendLine("}")

            scriptBuilder.AppendLine("mainDeadlineRender();")
            scriptBuilder.AppendLine("// Ending Mel program")
            scriptBuilder.AppendLine()

            self.ScriptFilename = self.WriteBatchScriptFile(scriptBuilder)

        # Have maya batch execute the script.
        self.LogInfo("Executing script: " + self.ScriptFilename)
        self.FlushMonitoredManagedProcessStdout(self.ProcessName)

        # Execute either MEL or Python script based on file extension provided.
        if os.path.splitext(self.ScriptFilename)[1].lower() == ".py":
            self.WriteStdinToMonitoredManagedProcess(
                self.ProcessName,
                'eval( "python( \\"execfile( \\\\\\"'
                + self.ScriptFilename.replace("\\", "/")
                + '\\\\\\" )\\" );" );',
            )
        else:
            self.WriteStdinToMonitoredManagedProcess(
                self.ProcessName,
                'eval( "source \\"'
                + self.ScriptFilename.replace("\\", "/")
                + '\\";" )',
            )

        # Wait until render is complete.
        self.LogInfo("Waiting for script to finish")
        self.WaitForProcess()

        # If this is a regular job, do some post processing.
        if not self.ScriptJob:
            # Delete the temp script file.
            os.remove(self.ScriptFilename)

            # If local rendering, move output to its final destination.
            if self.LocalRendering and self.Renderer != "3delight":
                self.LogInfo(
                    "Moving output files and folders from "
                    + self.CurrentRenderDirectory
                    + " to "
                    + self.RenderDirectory
                )
                self.VerifyAndMoveDirectory(
                    self.CurrentRenderDirectory,
                    self.RenderDirectory,
                    False,
                    -1,
                )

        # We've now finished the first task on this Worker for this job.
        self.FirstTask = False

    def SetRedshiftPathmappingEnv(self):
        # "C:\MyTextures\" "\\MYSERVER01\Textures\" ...
        redshiftMappingRE = re.compile(r"\"([^\"]*)\"\s+\"([^\"]*)\"")

        if self.Renderer == "redshift" and self.EnablePathMapping:
            mappings = RepositoryUtils.GetPathMappings()
            # Remove Mappings with no to path.
            mappings = [
                mappingPair for mappingPair in mappings if mappingPair[1]
            ]

            if len(mappings) == 0:
                return

            self.LogInfo("Redshift Path Mapping...")

            oldRSMappingFileName = Environment.GetEnvironmentVariable(
                "REDSHIFT_PATHOVERRIDE_FILE"
            )
            if oldRSMappingFileName:
                self.LogInfo(
                    '[REDSHIFT_PATHOVERRIDE_FILE]="%s"' % oldRSMappingFileName
                )
                with io.open(
                    oldRSMappingFileName, mode="r", encoding="utf-8"
                ) as oldRSMappingFile:
                    for line in oldRSMappingFile:
                        mappings.extend(redshiftMappingRE.findall(line))

            oldRSMappingString = Environment.GetEnvironmentVariable(
                "REDSHIFT_PATHOVERRIDE_STRING"
            )
            if oldRSMappingString:
                self.LogInfo(
                    '[REDSHIFT_PATHOVERRIDE_STRING]="%s"' % oldRSMappingString
                )
                mappings.extend(redshiftMappingRE.findall(oldRSMappingString))

            newRSMappingFileName = os.path.join(
                self.TempThreadDirectory, "RSMapping.txt"
            )
            with io.open(
                newRSMappingFileName, mode="w", encoding="utf-8"
            ) as newRSMappingFile:
                for mappingPair in mappings:
                    self.LogInfo(
                        u'source: "%s" dest: "%s"'
                        % (mappingPair[0], mappingPair[1])
                    )
                    newRSMappingFile.write(
                        u'"%s" "%s"\n' % (mappingPair[0], mappingPair[1])
                    )

            self.SetEnvironmentAndLogInfo(
                "REDSHIFT_PATHOVERRIDE_FILE", newRSMappingFileName
            )

    def _get_valid_mappings_for_dirmap(self):
        """
        Pulls all Path mappings from Deadline and ensures all paths are valid for dirmap.
        Validity is ensured by:
            Changing all backslashes(\) in the output to slashes(/)
            removing all paths that do not start with either / or a <drive letter>:
        :return: a list of pairs of paths contain the From and To components for pathmapping
        """
        # Confirms that paths start with either \,/ or <driveLetter>:
        valid_mapping_re = re.compile(r"^([a-z]:|[\\\/])", re.IGNORECASE)

        valid_mappings = []
        for mapping_pair in RepositoryUtils.GetPathMappings():
            # Confirm both the from and to path are valid
            if all(map(valid_mapping_re.match, mapping_pair)):
                valid_mappings.append(
                    map(lambda x: x.replace("\\", "/"), mapping_pair)
                )

        return valid_mappings

    def build_dirmap_commands(self):
        """
        Builds a list of melscript commands needed to enable Dirmap pathmapping in Maya
        :return: a list of melscript commands.
        """

        mappings = self._get_valid_mappings_for_dirmap()

        if not mappings:
            self.LogInfo(
                "No valid path mappings found. Skipping adding dirmap commands."
            )
            return []

        # Enable Dirmap
        commands = ["dirmap -en true;"]

        for original, mapped in mappings:
            self.LogInfo(
                'Adding dirmap command to map "{}" to "{}"'.format(
                    original, mapped
                )
            )
            commands.append('dirmap -m "{}" "{}";'.format(original, mapped))

        return commands

    def CreateDelayLoadSceneMelscript(self, scriptBuilder):

        # If using dirmap for path mapping, need to load the scene now (it's not loaded via the command line in this case).
        # Only do this for the first task the Worker has picked up for this job.
        # The below is only a sanity check, and should never fail.
        if (
            not self.EnablePathMapping or not self.DirmapPathMapping
        ):  # this check seems to be equivalent to self.DelayLoadScene
            raise Exception(
                "Do not call CreateDelayedLoadingMelscript unless delayed loading is enabled."
            )

        scriptBuilder.AppendLine("\n".join(self.build_dirmap_commands()))
        scriptBuilder.AppendLine()

        # Force load plug-ins that Maya does not properly auto-load when the scene depends on them
        scriptBuilder.AppendLine(
            'catch( python( "DeadlineMayaBatchFunctions.ForceLoadPlugins()" ) );'
        )

        # Use "catchQuiet" to silence errors when loading the scene
        useCatchQuiet = self.GetBooleanConfigEntryWithDefault(
            "SilenceSceneLoadErrors", False
        )

        # this call right here actually loads the scene file.
        # this is needed because in DelayLoadScene mode, this filename was not passed on the command line.
        scriptBuilder.AppendLine(
            "int $loadFailed = %s( `file -o $sceneName` );"
            % ("catchQuiet" if useCatchQuiet else "catch")
        )

        scriptBuilder.AppendLine("if (!$loadFailed) {")

        # show loaded plugins
        scriptBuilder.AppendLine(
            'catch( python( "DeadlineMayaBatchFunctions.OutputPluginVersions()" ) );'
        )

        # Need to execute the startup script now, after the scene has been loaded.
        if self.StartupScriptPath != "":
            scriptBuilder.AppendLine(
                'string $startupScriptName = "'
                + self.StartupScriptPath.replace("\\", "/")
                + '";'
            )
            scriptBuilder.AppendLine(
                'print ("Executing startup script: " + $startupScriptName + "\\n");'
            )
            scriptBuilder.AppendLine(
                'if( catch(eval( "source \\"" + $startupScriptName + "\\";" )) ){'
            )
            scriptBuilder.AppendLine(
                'print ( "An error occurred during the Startup Script.\\n" );'
            )
            scriptBuilder.AppendLine("}")

        scriptBuilder.AppendLine("}")

        # this call is currently a work around because Maya's dirmap is failing to pathmap any file paths that include tokens.
        # When this is fixed in maya we can add a version check.
        scriptBuilder.AppendLine(
            'catch( remapNodeFilePathsWithTokens( "file", "fileTextureName", true ) );'
        )
        scriptBuilder.AppendLine(
            'catch( remapNodeFilePathsWithTokens( "aiStandIn", "dso", false ) );'
        )
        # Dirmap does not map OpenColorIO Files so we have to handle this separately.
        scriptBuilder.AppendLine(
            "catch( mapOpenColorIOFile( "
            + ("1" if self.EnableOpenColorIO else "0")
            + " ) );"
        )

    def EndJob(self):
        self.LogInfo("Ending Maya Job")
        self.FlushMonitoredManagedProcessStdoutNoHandling(self.ProcessName)
        self.LogInfo("Waiting for Maya to shut down")
        self.ShutdownMonitoredManagedProcess(self.ProcessName)
        self.LogInfo("Maya has shut down")

        if (
            self.EnablePathMapping
            and not self.DirmapPathMapping
            and os.path.splitext(self.SceneFile)[1].lower() == ".ma"
        ):
            os.remove(self.SceneFile)

    def WaitForProcess(self):
        self.FlushMonitoredManagedProcessStdout(self.ProcessName)
        self.WriteStdinToMonitoredManagedProcess(
            self.ProcessName, self.Process.ReadyForInputCommand()
        )
        while not self.Process.IsReadyForInput():
            self.VerifyMonitoredManagedProcess(self.ProcessName)
            self.FlushMonitoredManagedProcessStdout(self.ProcessName)

            blockingDialogMessage = self.CheckForMonitoredManagedProcessPopups(
                self.ProcessName
            )
            if blockingDialogMessage:
                self.FailRender(blockingDialogMessage)

            if self.IsCanceled():
                self.FailRender("Received cancel task command")
            SystemUtils.Sleep(100)
        self.Process.ResetReadyForInput()

    def unlockRedshiftRenderSetupOverrides(self):
        renderSetupOverrides = defaultdict(list)

        if self.StartFrame or self.EndFrame:
            renderSetupOverrides["defaultRenderGlobals"].append("animation")
            if self.StartFrame:
                renderSetupOverrides["defaultRenderGlobals"].append(
                    "startFrame"
                )
            if self.EndFrame:
                renderSetupOverrides["defaultRenderGlobals"].append("endFrame")

        if self.ByFrame:
            renderSetupOverrides["defaultRenderGlobals"].append("byFrameStep")

        if self.RenumberFrameStart:
            renderSetupOverrides["defaultRenderGlobals"].append(
                "modifyExtension"
            )
            renderSetupOverrides["defaultRenderGlobals"].append(
                "startExtension"
            )

        if self.ImagePrefix:
            renderSetupOverrides["defaultRenderGlobals"].append(
                "imageFilePrefix"
            )
            renderSetupOverrides["redshiftOptions"].append("imageFilePrefix")

        if self.Height:
            renderSetupOverrides["defaultResolution"].append("height")

        if self.Width:
            renderSetupOverrides["defaultResolution"].append("width")

        # Pass in renderSetupOverrides as a string
        unlockOverrideString = 'string $renderSetupOverrides = "%s";\n' % json.dumps(
            renderSetupOverrides
        ).replace(
            '"', '\\"'
        )
        unlockOverrideString += 'catch( python( "DeadlineMayaBatchFunctions.unlockRenderSetupOverrides(\'" + $renderSetupOverrides + "\' )" ) );'
        return unlockOverrideString

    def GetInitializeCommand(self):
        if self.Renderer == "file" or (
            self.UsingRenderLayers and len(self.RenderLayer) == 0
        ):
            return 'string $rl=""; string $rp="";select defaultRenderGlobals; setAttr .renderAll 1; float $resize=-1.;'
        elif self.Renderer == "mayasoftware":
            return 'string $opt = ""; string $rl=""; string $rp=""; float $resize=-1.; select defaultRenderGlobals; setAttr .renderAll 1;'
        elif self.Renderer == "mayahardware":
            return 'float $resize=-1.; global string $hardwareRenderOptions = ""; string $rl=""; string $rp=""; select hardwareRenderGlobals;'
        elif self.Renderer == "mayahardware2":
            return 'float $resize=-1.; global string $ogsRenderOptions = ""; string $rl=""; string $rp=""; select hardwareRenderingGlobals;'
        elif self.Renderer == "mayavector":
            return 'if (!`pluginInfo -q -l VectorRender`) {loadPlugin VectorRender;} vrCreateGlobalsNode(); string $rl=""; string $rp="";  float $resize=-1.; select vectorRenderGlobals; setAttr defaultRenderGlobals.renderAll 1;'
        elif self.Renderer == "mentalray":
            return 'string $opt=""; string $rl=""; string $rp=""; int $renderThreads = 2; float $resize=-1.; miLoadMayatomr; miCreateDefaultNodes(); select defaultRenderGlobals; setAttr .renderAll 1;'
        elif self.Renderer in ["renderman", "rendermanris", "rendermanexport"]:
            return (
                'if (!`pluginInfo -q -l RenderMan_for_Maya`) {loadPlugin RenderMan_for_Maya;} rmanCreateAllGlobalsNodes();string $rl=""; string $rp=""; string $spoolmode=""; int $chunksize=100; int $rib='
                + ("1" if self.Renderer == "rendermanexport" else "0")
                + '; int $ui=0; string $renderer=""; string $globals="";'
            )
        elif self.Renderer in ["renderman22", "renderman22export"]:
            return """if (!`pluginInfo -q -l RenderMan_for_Maya.py`) {loadPlugin RenderMan_for_Maya.py;}
                      python("import rfm2.api.nodes");
                      string $rl="";
                      python("rfm2.api.nodes.rman_globals()");
                      string $options="";"""
        elif self.Renderer == "turtle":
            return 'string $extraOptions=""; string $rl=""; string $rp=""; float $resize=-1.; ilrLoadTurtle; setAttr TurtleRenderGlobals.renderer 0;'
        elif self.Renderer == "gelato":
            return 'string $opt=""; string $rl=""; string $rp=""; float $resize=-1.; select defaultRenderGlobals;'
        elif self.Renderer in ["arnold", "arnoldexport"]:
            return 'string $opt=""; string $rl=""; string $rp=""; float $resize=-1.; loadPlugin -quiet mtoa;;'
        elif self.Renderer in ["redshift", "redshiftexport"]:
            # Redshift 1.2.95 changed the redshiftGetRedshiftOptionsNode function to accept a single parameter. So try to call it without the parameter first, and if an error occurs (ie: catchQuiet returns True), then try to call it with the parameter.
            return (
                'string $rl=""; string $rp=""; float $resize=-1.; loadPlugin -quiet redshift4maya; redshiftRegisterRenderer(); if( catchQuiet( eval( "redshiftGetRedshiftOptionsNode()" ) ) ) { eval( "redshiftGetRedshiftOptionsNode(true)" ); };\n'
                'string $redshiftVersion = `pluginInfo -q -version "redshift4maya"`;string $redshiftVersions[];$redshiftVersions = stringToStringArray($redshiftVersion, ".");float $redshiftMajorVersion = ( float )( $redshiftVersions[0]+"."+$redshiftVersions[1] );\n'
                + self.unlockRedshiftRenderSetupOverrides()
            )
        elif self.Renderer in ["vray", "vrayexport"]:
            return 'string $opt=""; string $rl=""; string $rp=""; float $resize=-1.; vrayRegisterRenderer(); vrayCreateVRaySettingsNode(); select vraySettings;'
        elif self.Renderer == "3delight":
            return 'string $opt = ""; string $rl=""; string $rp=""; DRG_batchRenderInit(); string $render_pass = DRG_selectedRenderPass(); if ($render_pass != "") { select $render_pass;};'
        elif self.Renderer == "mentalrayexport":
            return 'source mentalrayBatchExportProcedure.mel; string $filename=""; string $rl=""; string $rp=""; string $opt=""; float $resize=-1.; int $perLayer=1; miLoadMayatomr; miCreateDefaultNodes(); select defaultRenderGlobals; setAttr .renderAll 1;'
        elif self.Renderer == "finalrender":
            return 'int $kpi = 0; int $rep = 1; int $amt = 0; int $irr=0; int $frr[4]; string $rl=""; string $rp=""; int $numCpu=0; string $dr=""; string $strHosts = ""; frLoad; copyCommonRenderGlobals(currentRenderer(), "finalRender"); lockNode -lock false defaultFinalRenderSettings; select defaultRenderGlobals; setAttr .renderAll 1;'
        elif self.Renderer in ["maxwell", "maxwellexport"]:
            return "if (!`pluginInfo -q -l maxwell`) {loadPlugin maxwell;} setAttr defaultRenderGlobals.renderAll 1;"
        elif self.Renderer == "mayakrakatoa":
            return 'if (!`pluginInfo -q -l MayaKrakatoa`) {loadPlugin MayaKrakatoa;} string $rl=""; string $rp=""; string $options=""; select defaultRenderGlobals; setAttr .renderAll 1; float $resize=-1.;'
        elif self.Renderer == "octanerender":
            return 'string $opt = ""; string $rl=""; string $rp=""; float $resize=-1.; int $interactive=0; if(!`pluginInfo -q -l "OctanePlugin"`) {loadPlugin "OctanePlugin";} select defaultRenderGlobals; setAttr .renderAll 1;'
        elif self.Renderer == "causticvisualizer":
            return 'string $opt = ""; string $rl=""; string $rp=""; float $resize=-1.; int $interactive=0; select defaultRenderGlobals; setAttr .renderAll 1;'
        elif self.Renderer == "ifmirayphotoreal":
            return 'string $rl=""; string $rp="";select defaultRenderGlobals; setAttr .renderAll 1; float $resize=-1.;'
        else:
            self.LogWarning(
                "Renderer "
                + self.Renderer
                + " is currently unsupported, so falling back to generic render arguments"
            )
            return 'string $rl=""; string $rp="";select defaultRenderGlobals; setAttr .renderAll 1; float $resize=-1.;'

        return ""

    def LocalAssetCachingCommand(self):

        cacheDirectoryConfigEntry = "SlaveLACDirectoryWindows"
        if SystemUtils.IsRunningOnMac():
            cacheDirectoryConfigEntry = "SlaveLACDirectoryOSX"
        elif SystemUtils.IsRunningOnLinux():
            cacheDirectoryConfigEntry = "SlaveLACDirectoryLinux"

        cacheDirectory = self.GetConfigEntryWithDefault(
            cacheDirectoryConfigEntry, ""
        ).strip()
        if not cacheDirectory:
            self.LogWarning(
                "Disabling local asset caching: The local asset cache directory for this platform is not set. You must set this option in the MayaBatch repository plugin settings."
            )
            return ""

        cacheDirectory = os.path.expandvars(cacheDirectory).replace("\\", "/")
        if not os.path.exists(cacheDirectory):
            try:
                os.makedirs(cacheDirectory)
            except OSError:
                # ensure that another Worker hasn't created this directory while we tried to.
                if not os.path.exists(cacheDirectory):
                    self.FailRender(
                        'Failed to create local asset cache directory: "%s". You can modify this directory in the MayaBatch repository plugin settings.'
                        % cacheDirectory
                    )

        networkPrefixes = self.GetConfigEntryWithDefault(
            "RemoteAssetPaths", "//;X:;Y:;Z:"
        ).replace("\\", "/")
        daysToDelete = self.GetIntegerConfigEntryWithDefault(
            "SlaveLACDaysToDelete", 5
        )

        # This do_local_asset_caching function is defined in AssetTools.mel.
        scriptString = (
            '\ndo_local_asset_caching( "'
            + cacheDirectory
            + '", "'
            + networkPrefixes
            + '", '
            + str(daysToDelete)
            + " );\n"
        )

        return scriptString

    def GetStartFrameCommand(self):
        if len(self.StartFrame) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .animation; setAttr .animation 1; removeRenderLayerAdjustmentAndUnlock .startFrame; setAttr .startFrame "
                    + self.StartFrame
                    + ";"
                )
            elif (
                self.Renderer == "mayasoftware"
                or self.Renderer == "mentalray"
                or self.Renderer == "gelato"
                or self.Renderer == "mentalrayexport"
                or self.Renderer == "finalrender"
                or self.Renderer == "mayakrakatoa"
                or self.Renderer == "octanerender"
                or self.Renderer == "causticvisualizer"
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .animation; setAttr .animation 1; removeRenderLayerAdjustmentAndUnlock .startFrame; setAttr .startFrame "
                    + self.StartFrame
                    + ";"
                )
            elif self.Renderer in {
                "mayavector",
                "mayahardware",
                "mayahardware2",
                "turtle",
                "arnold",
                "arnoldexport",
                "redshift",
                "redshiftexport",
                "vray",
                "vrayexport",
                "ifmirayphotoreal",
                "renderman22",
                "renderman22export",
            }:
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.animation; setAttr defaultRenderGlobals.animation 1; removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.startFrame; setAttr defaultRenderGlobals.startFrame "
                    + self.StartFrame
                    + ";"
                )
            elif (
                self.Renderer == "renderman"
                or self.Renderer == "rendermanris"
                or self.Renderer == "rendermanexport"
            ):
                return (
                    "setAttr -l 0 defaultRenderGlobals.animation; setAttr defaultRenderGlobals.animation 1; setAttr -l 0 defaultRenderGlobals.startFrame; setAttr defaultRenderGlobals.startFrame "
                    + self.StartFrame
                    + ";"
                )
            elif self.Renderer == "3delight":
                return (
                    "removeRenderLayerAdjustmentAndUnlock .startFrame; catch(`setAttr .startFrame "
                    + self.StartFrame
                    + "`);"
                )
            elif (
                self.Renderer == "maxwell" or self.Renderer == "maxwellexport"
            ):
                return (
                    "maxwellUnlockAndSet defaultRenderGlobals.animation 1; maxwellUnlockAndSet defaultRenderGlobals.startFrame "
                    + self.StartFrame
                    + ";"
                )
            else:
                return (
                    "removeRenderLayerAdjustmentAndUnlock .animation; setAttr .animation 1; removeRenderLayerAdjustmentAndUnlock .startFrame; setAttr .startFrame "
                    + self.StartFrame
                    + ";"
                )
        return ""

    def GetEndFrameCommand(self):
        if len(self.EndFrame) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .animation; setAttr .animation 1; removeRenderLayerAdjustmentAndUnlock .endFrame; setAttr .endFrame "
                    + self.EndFrame
                    + ";"
                )
            elif (
                self.Renderer == "mayasoftware"
                or self.Renderer == "mentalray"
                or self.Renderer == "gelato"
                or self.Renderer == "mentalrayexport"
                or self.Renderer == "finalrender"
                or self.Renderer == "mayakrakatoa"
                or self.Renderer == "octanerender"
                or self.Renderer == "causticvisualizer"
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .animation; setAttr .animation 1; removeRenderLayerAdjustmentAndUnlock .endFrame; setAttr .endFrame "
                    + self.EndFrame
                    + ";"
                )
            elif self.Renderer in {
                "mayavector",
                "mayahardware",
                "mayahardware2",
                "turtle",
                "arnold",
                "arnoldexport",
                "redshift",
                "redshiftexport",
                "vray",
                "vrayexport",
                "ifmirayphotoreal",
                "renderman22",
                "renderman22export",
            }:
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.animation; setAttr defaultRenderGlobals.animation 1; removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.endFrame; setAttr defaultRenderGlobals.endFrame "
                    + self.EndFrame
                    + ";"
                )
            elif (
                self.Renderer == "renderman"
                or self.Renderer == "rendermanris"
                or self.Renderer == "rendermanexport"
            ):
                return (
                    "setAttr -l 0 defaultRenderGlobals.animation; setAttr defaultRenderGlobals.animation 1; setAttr -l 0 defaultRenderGlobals.endFrame; setAttr defaultRenderGlobals.endFrame "
                    + self.EndFrame
                    + ";"
                )
            elif self.Renderer == "3delight":
                return (
                    "removeRenderLayerAdjustmentAndUnlock .endFrame; catch(`setAttr .endFrame "
                    + self.EndFrame
                    + "`);"
                )
            elif (
                self.Renderer == "maxwell" or self.Renderer == "maxwellexport"
            ):
                return (
                    "maxwellUnlockAndSet defaultRenderGlobals.animation 1; maxwellUnlockAndSet defaultRenderGlobals.endFrame "
                    + self.EndFrame
                    + ";"
                )
            else:
                return (
                    "removeRenderLayerAdjustmentAndUnlock .animation; setAttr .animation 1; removeRenderLayerAdjustmentAndUnlock .endFrame; setAttr .endFrame "
                    + self.EndFrame
                    + ";"
                )
        return ""

    def GetByFrameCommand(self):
        if len(self.ByFrame) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .byFrameStep; catch(`setAttr .byFrameStep "
                    + self.ByFrame
                    + "`);"
                )
            elif (
                self.Renderer == "mayasoftware"
                or self.Renderer == "mentalray"
                or self.Renderer == "gelato"
                or self.Renderer == "mentalrayexport"
                or self.Renderer == "finalrender"
                or self.Renderer == "mayakrakatoa"
                or self.Renderer == "octanerender"
                or self.Renderer == "causticvisualizer"
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .byFrameStep; catch(`setAttr .byFrameStep "
                    + self.ByFrame
                    + "`);"
                )
            elif self.Renderer in {
                "mayavector",
                "mayahardware",
                "mayahardware2",
                "renderman",
                "rendermanris",
                "rendermanexport",
                "renderman22",
                "renderman22export",
                "turtle",
                "maxwell",
                "maxwellexport",
                "arnold",
                "arnoldexport",
                "redshift",
                "redshiftexport",
                "ifmirayphotoreal",
            }:
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.byFrameStep; catch(`setAttr defaultRenderGlobals.byFrameStep "
                    + self.ByFrame
                    + "`);"
                )
            elif self.Renderer == "vray" or self.Renderer == "vrayexport":
                # return 'setAttr "vraySettings.frameStep" ' + self.ByFrame + '; setAttr "vraySettings.animation" true;'
                # return 'setAttr "defaultRenderGlobals.byFrameStep" ' + self.ByFrame + '; setAttr "defaultRenderGlobals.animation" true;;'
                return (
                    'setAttr "defaultRenderGlobals.byFrameStep" '
                    + self.ByFrame
                    + '; setAttr "defaultRenderGlobals.animation" true;; setAttr "vraySettings.frameStep" '
                    + self.ByFrame
                    + '; setAttr "vraySettings.animation" true;'
                )
            elif self.Renderer == "3delight":
                return (
                    "removeRenderLayerAdjustmentAndUnlock .increment; catch(`setAttr .increment "
                    + self.ByFrame
                    + "`);"
                )
            else:
                return (
                    "removeRenderLayerAdjustmentAndUnlock .byFrameStep; catch(`setAttr .byFrameStep "
                    + self.ByFrame
                    + "`);"
                )
        return ""

    def GetRenumberFrameStartCommand(self):
        if len(self.RenumberFrameStart) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .modifyExtension; setAttr .modifyExtension 1; removeRenderLayerAdjustmentAndUnlock .startExtension; setAttr .startExtension "
                    + self.RenumberFrameStart
                    + ";"
                )
            elif (
                self.Renderer == "mayasoftware"
                or self.Renderer == "mentalray"
                or self.Renderer == "gelato"
                or self.Renderer == "mentalrayexport"
                or self.Renderer == "finalrender"
                or self.Renderer == "mayakrakatoa"
                or self.Renderer == "octanerender"
                or self.Renderer == "causticvisualizer"
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .modifyExtension; setAttr .modifyExtension 1; removeRenderLayerAdjustmentAndUnlock .startExtension; setAttr .startExtension "
                    + self.RenumberFrameStart
                    + ";"
                )
            elif (
                self.Renderer == "mayavector"
                or self.Renderer == "mayahardware"
                or self.Renderer == "mayahardware2"
                or self.Renderer == "turtle"
                or self.Renderer == "arnold"
                or self.Renderer == "arnoldexport"
                or self.Renderer == "redshift"
                or self.Renderer == "redshiftExport"
                or self.Renderer == "ifmirayphotoreal"
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.modifyExtension; setAttr defaultRenderGlobals.modifyExtension 1; removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.startExtension; setAttr defaultRenderGlobals.startExtension "
                    + self.RenumberFrameStart
                    + ";"
                )
            elif (
                self.Renderer == "renderman" or self.Renderer == "rendermanris"
            ):
                return (
                    'rmanSetGlobalAttr "renumber" 1;         rmanSetGlobalAttr "renumberStart" '
                    + self.RenumberFrameStart
                    + ";"
                )
            if self.Renderer == "renderman22":
                # As of Renderman 22.3 Renderman does not support Frame renumbering.
                return ""
            elif (
                self.Renderer == "maxwell" or self.Renderer == "maxwellexport"
            ):
                return (
                    "maxwellUnlockAndSet defaultRenderGlobals.modifyExtension 1; maxwellUnlockAndSet defaultRenderGlobals.startExtension "
                    + self.RenumberFrameStart
                    + ";"
                )
            else:
                return (
                    "removeRenderLayerAdjustmentAndUnlock .modifyExtension; setAttr .modifyExtension 1; removeRenderLayerAdjustmentAndUnlock .startExtension; setAttr .startExtension "
                    + self.RenumberFrameStart
                    + ";"
                )
        return ""

    def GetImagePrefixCommand(self):
        """
        This function is used to write a command modify the Image Prefix in maya.
        """
        if len(self.ImagePrefix) > 0:

            # Mental Ray doesn't properly handle these tokens when writing the output of incremental saves (file version is in the name)
            # Even though it shows it in the render settings that it's properly using the tokens.
            if self.Renderer == "mentalray" and (
                "%s" in self.ImagePrefix or "<Scene>" in self.ImagePrefix
            ):
                sceneName = os.path.splitext(os.path.basename(self.SceneFile))[
                    0
                ]
                self.ImagePrefix = self.ImagePrefix.replace(
                    "%s", sceneName
                ).replace("<Scene>", sceneName)

            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    'removeRenderLayerAdjustmentAndUnlock .imageFilePrefix; catch(`setAttr -type "string" .imageFilePrefix "'
                    + self.ImagePrefix
                    + '"`);'
                )
            elif (
                self.Renderer == "mayasoftware"
                or self.Renderer == "mentalray"
                or self.Renderer == "gelato"
                or self.Renderer == "mentalrayexport"
                or self.Renderer == "finalrender"
                or self.Renderer == "mayakrakatoa"
                or self.Renderer == "octanerender"
                or self.Renderer == "causticvisualizer"
            ):
                return (
                    'removeRenderLayerAdjustmentAndUnlock .imageFilePrefix; catch(`setAttr -type "string" .imageFilePrefix "'
                    + self.ImagePrefix
                    + '"`);'
                )
            elif (
                self.Renderer == "mayavector"
                or self.Renderer == "mayahardware"
                or self.Renderer == "mayahardware2"
                or self.Renderer == "renderman"
                or self.Renderer == "rendermanris"
                or self.Renderer == "rendermanexport"
                or self.Renderer == "turtle"
                or self.Renderer == "maxwell"
                or self.Renderer == "maxwellexport"
                or self.Renderer == "arnold"
                or self.Renderer == "arnoldexport"
                or self.Renderer == "ifmirayphotoreal"
            ):
                return (
                    'removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.imageFilePrefix; catch(`setAttr -type "string" defaultRenderGlobals.imageFilePrefix "'
                    + self.ImagePrefix
                    + '"`);'
                )
            elif (
                self.Renderer == "redshift"
                or self.Renderer == "redshiftexport"
            ):
                redshiftData = [
                    'if( $redshiftMajorVersion >1.2 || ( $redshiftMajorVersion == 1.2 && (int)$redshiftVersions[2] > 81) ){ removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.imageFilePrefix; catch(`setAttr -type "string" defaultRenderGlobals.imageFilePrefix "'
                    + self.ImagePrefix
                    + '"`); }',
                    ' else { removeRenderLayerAdjustmentAndUnlock redshiftOptions.imageFilePrefix; catch(`setAttr -type "string" redshiftOptions.imageFilePrefix "'
                    + self.ImagePrefix
                    + '"`); }',
                ]
                return "".join(redshiftData)
            elif self.Renderer in {"renderman22", "renderman22export"}:
                # Renderman command line renderer does not use this method and instead uses "$options += " -imageFile ...".  We are not using that method because it modifies both the Image Prefix and the Output Directory which we want to handle separately
                # We instead modify the Global property which Renderman reads when rendering.
                return (
                    'removeRenderLayerAdjustmentAndUnlock rmanGlobals.imageFileFormat; catch(`setAttr -type "string" rmanGlobals.imageFileFormat "'
                    + self.ImagePrefix
                    + '"`);'
                )
            elif self.Renderer == "vray" or self.Renderer == "vrayexport":
                return (
                    'setAttr -type "string" "vraySettings.fileNamePrefix" "'
                    + self.ImagePrefix
                    + '";'
                )
            else:
                return (
                    'removeRenderLayerAdjustmentAndUnlock .imageFilePrefix; catch(`setAttr -type "string" .imageFilePrefix "'
                    + self.ImagePrefix
                    + '"`);'
                )
        return ""

    def GetRenderDirectoryCommand(self):
        if len(self.RenderDirectory) > 0:
            flags = "-fr" if (self.Version > 2012) else "-rt"

            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    "workspace "
                    + flags
                    + ' "images" "'
                    + self.CurrentRenderDirectory
                    + '"; workspace '
                    + flags
                    + ' "depth" "'
                    + self.CurrentRenderDirectory
                    + '";'
                )
            elif (
                self.Renderer == "mayasoftware"
                or self.Renderer == "mentalray"
                or self.Renderer == "mayavector"
                or self.Renderer == "mayahardware"
                or self.Renderer == "mayahardware2"
                or self.Renderer == "turtle"
                or self.Renderer == "vray"
                or self.Renderer == "vrayexport"
                or self.Renderer == "mentalrayexport"
                or self.Renderer == "finalrender"
                or self.Renderer == "maxwell"
                or self.Renderer == "maxwellexport"
                or self.Renderer == "mayakrakatoa"
                or self.Renderer == "octanerender"
                or self.Renderer == "causticvisualizer"
                or self.Renderer == "redshift"
                or self.Renderer == "ifmirayphotoreal"
            ):
                return (
                    "workspace "
                    + flags
                    + ' "images" "'
                    + self.CurrentRenderDirectory
                    + '"; workspace '
                    + flags
                    + ' "depth" "'
                    + self.CurrentRenderDirectory
                    + '";'
                )
            elif self.Renderer == "redshiftexport":
                sceneName = ' `workspace -q -rd` + "redshift/" '
                if len(self.RenderLayer) > 0:  # dir depends on layer
                    sceneName += ' + "' + self.RenderLayer + '/" '
                sceneName += " + basenameEx($name) "
                if self.Animation:
                    sceneName += ' + ".####"'
                sceneName += ' + ".rs"'

                renderDirBuilder = StringBuilder()
                renderDirBuilder.AppendLine("$rp = " + sceneName + ";")
                renderDirBuilder.AppendLine(" string $path = dirname($rp);")
                renderDirBuilder.AppendLine(" if(! `filetest -d $path` ){")
                renderDirBuilder.AppendLine(" sysFile -md $path; }")
                return renderDirBuilder.ToString()
            elif self.Renderer == "arnold" or self.Renderer == "arnoldexport":
                return (
                    "workspace "
                    + flags
                    + ' "images" "'
                    + self.CurrentRenderDirectory
                    + '";workspace '
                    + flags
                    + ' "depth" "'
                    + self.CurrentRenderDirectory
                    + '";workspace -fileRule "images" "'
                    + self.CurrentRenderDirectory
                    + '";'
                )
            elif (
                self.Renderer == "renderman"
                or self.Renderer == "rendermanris"
                or self.Renderer == "rendermanexport"
            ):
                return 'rmanSetImageDir "' + self.CurrentRenderDirectory + '";'
            elif self.Renderer in {"renderman22", "renderman22export"}:
                return (
                    'removeRenderLayerAdjustmentAndUnlock rmanGlobals.imageOutputDir; catch(`setAttr -type "string" rmanGlobals.imageOutputDir "'
                    + self.CurrentRenderDirectory
                    + '"`);'
                )
            elif self.Renderer == "gelato":
                return (
                    "workspace "
                    + flags
                    + ' "images" "'
                    + self.CurrentRenderDirectory
                    + '";'
                )
            else:
                return (
                    "workspace "
                    + flags
                    + ' "images" "'
                    + self.CurrentRenderDirectory
                    + '"; workspace '
                    + flags
                    + ' "depth" "'
                    + self.CurrentRenderDirectory
                    + '";'
                )
        return ""

    def GetCameraCommand(self):
        if len(self.Camera) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    'makeCameraRenderable("'
                    + self.Camera
                    + '"); if (`attributeExists batchCamera vraySettings` != 0) setAttr -type "string" "vraySettings.batchCamera" "'
                    + self.Camera
                    + '";'
                )
            elif self.Renderer in {
                "mayasoftware",
                "mentalray",
                "mayavector",
                "mayahardware",
                "mayahardware2",
                "renderman",
                "rendermanris",
                "renderman22",
                "turtle",
                "gelato",
                "mentalrayexport",
                "finalrender",
                "maxwell",
                "maxwellexport",
                "mayakrakatoa",
                "arnold",
                "arnoldexport",
                "octanerender",
                "causticvisualizer",
                "redshift",
                "redshiftexport",
                "ifmirayphotoreal",
            }:
                return 'makeCameraRenderable("' + self.Camera + '");'
            elif self.Renderer == "vray" or self.Renderer == "vrayexport":
                return (
                    'makeCameraRenderable("'
                    + self.Camera
                    + '"); setAttr -type "string" "vraySettings.batchCamera" "'
                    + self.Camera
                    + '";'
                )
            elif self.Renderer == "3delight":
                return (
                    'string $render_pass = DRG_selectedRenderPass(); DRP_setCamera($render_pass, "'
                    + self.Camera
                    + '");'
                )
            else:
                return (
                    'makeCameraRenderable("'
                    + self.Camera
                    + '"); if (`attributeExists batchCamera vraySettings` != 0) setAttr -type "string" "vraySettings.batchCamera" "'
                    + self.Camera
                    + '";'
                )
        return ""

    def GetWidthCommand(self):
        if len(self.Width) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultResolution.width; catch(`setAttr defaultResolution.width "
                    + self.Width
                    + "`);"
                )
            elif (
                self.Renderer == "mayasoftware"
                or self.Renderer == "mentalray"
                or self.Renderer == "mayavector"
                or self.Renderer == "mayahardware"
                or self.Renderer == "mayahardware2"
                or self.Renderer == "turtle"
                or self.Renderer == "gelato"
                or self.Renderer == "mentalrayexport"
                or self.Renderer == "finalrender"
                or self.Renderer == "maxwell"
                or self.Renderer == "maxwellexport"
                or self.Renderer == "mayakrakatoa"
                or self.Renderer == "arnold"
                or self.Renderer == "arnoldexport"
                or self.Renderer == "octanerender"
                or self.Renderer == "causticvisualizer"
                or self.Renderer == "redshift"
                or self.Renderer == "redshiftexport"
                or self.Renderer == "ifmirayphotoreal"
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultResolution.width; catch(`setAttr defaultResolution.width "
                    + self.Width
                    + "`);"
                )
            elif self.Renderer == "vray" or self.Renderer == "vrayexport":
                return 'setAttr "vraySettings.width" ' + self.Width + ";"
            elif self.Renderer == "3delight":
                return "DRG_setResolutionX(" + self.Width + ");"
            else:
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultResolution.width; catch(`setAttr defaultResolution.width "
                    + self.Width
                    + "`);"
                )
        return ""

    def GetHeightCommand(self):
        if len(self.Height) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultResolution.height; catch(`setAttr defaultResolution.height "
                    + self.Height
                    + "`);"
                )
            elif (
                self.Renderer == "mayasoftware"
                or self.Renderer == "mentalray"
                or self.Renderer == "mayavector"
                or self.Renderer == "mayahardware"
                or self.Renderer == "mayahardware2"
                or self.Renderer == "turtle"
                or self.Renderer == "gelato"
                or self.Renderer == "mentalrayexport"
                or self.Renderer == "finalrender"
                or self.Renderer == "maxwell"
                or self.Renderer == "maxwellexport"
                or self.Renderer == "mayakrakatoa"
                or self.Renderer == "arnold"
                or self.Renderer == "arnoldexport"
                or self.Renderer == "octanerender"
                or self.Renderer == "causticvisualizer"
                or self.Renderer == "redshift"
                or self.Renderer == "redshiftexport"
                or self.Renderer == "ifmirayphotoreal"
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultResolution.height; catch(`setAttr defaultResolution.height "
                    + self.Height
                    + "`);"
                )
            elif self.Renderer == "vray" or self.Renderer == "vrayexport":
                return 'setAttr "vraySettings.height" ' + self.Height + ";"
            elif self.Renderer == "3delight":
                return "DRG_setResolutionY(" + self.Height + ");"
            else:
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultResolution.height; catch(`setAttr defaultResolution.height "
                    + self.Height
                    + "`);"
                )
        return ""

    def GetScaleCommand(self):
        if len(self.Scale) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return "$resize=" + self.Scale + ";"
            elif (
                self.Renderer != "maxwell"
                and self.Renderer != "maxwellexport"
                and self.Renderer != "finalrender"
                and self.Renderer != "3delight"
            ):
                return "$resize=" + self.Scale + ";"
        return ""

    def GetResolutionCommand(self):
        if len(self.Width) > 0 and len(self.Height) > 0:
            if (
                self.Renderer == "renderman"
                or self.Renderer == "rendermanris"
                or self.Renderer == "rendermanexport"
            ):
                return (
                    'rmanSetGlobalAttr "Format:resolution" "'
                    + self.Width
                    + " "
                    + self.Height
                    + '";'
                )
            elif self.Renderer in {"renderman22", "renderman22export"}:
                return '$options += " -resolution %s %s";' % (
                    self.Width,
                    self.Height,
                )
        return ""

    # ~ def GetAspectRatioCommand( self ):
    # ~ if len( self.AspectRatio ) > 0:
    # ~ if self.Renderer == "file" or ( self.UsingRenderLayers and len( self.RenderLayer ) == 0 ):
    # ~ return 'removeRenderLayerAdjustmentAndUnlock defaultResolution.deviceAspectRatio; catch(`setAttr defaultResolution.deviceAspectRatio ' + self.AspectRatio + '`);'
    # ~ elif self.Renderer == "mayasoftware" or self.Renderer == "gelato" or self.Renderer == "finalrender":
    # ~ return 'removeRenderLayerAdjustmentAndUnlock defaultResolution.lockDeviceAspectRatio; setAttr defaultResolution.lockDeviceAspectRatio 1; removeRenderLayerAdjustmentAndUnlock defaultResolution.deviceAspectRatio; setAttr defaultResolution.deviceAspectRatio ' + self.AspectRatio + ';'
    # ~ elif self.Renderer == "mayavector" or self.Renderer == "mayahardware" or self.Renderer == "mayahardware2":
    # ~ return 'removeRenderLayerAdjustmentAndUnlock defaultResolution.pixelAspect; catch(`setAttr defaultResolution.pixelAspect ' + self.AspectRatio + '`);'
    # ~ elif self.Renderer == "mentalray" or self.Renderer == "turtle" or self.Renderer == "mentalrayexport":
    # ~ return 'removeRenderLayerAdjustmentAndUnlock defaultResolution.deviceAspectRatio; catch(`setAttr defaultResolution.deviceAspectRatio ' + self.AspectRatio + '`);'
    # ~ else:
    # ~ return 'removeRenderLayerAdjustmentAndUnlock defaultResolution.deviceAspectRatio; catch(`setAttr defaultResolution.deviceAspectRatio ' + self.AspectRatio + '`);'
    # ~ return ''

    def GetSkipExistingFramesCommand(self):
        if self.Version >= 2014 and self.SkipExistingFrames:
            if self.Renderer == "mayasoftware" or self.Renderer == "mentalray":
                return "removeRenderLayerAdjustmentAndUnlock .skipExistingFrames; catch(`setAttr .skipExistingFrames 1`);"
            if (
                self.Renderer == "mayavector"
                or self.Renderer == "mayahardware"
                or self.Renderer == "mayahardware2"
            ):
                return "removeRenderLayerAdjustmentAndUnlock defaultRenderGlobals.skipExistingFrames; catch(`setAttr defaultRenderGlobals.skipExistingFrames 1`);"
        return ""

    def GetRenderLayerCommand(self):
        if len(self.RenderLayer) > 0:
            if self.Renderer == "file" or (
                self.UsingRenderLayers and len(self.RenderLayer) == 0
            ):
                return '$rl="' + self.RenderLayer + '";'
            elif self.Renderer in {
                "mayasoftware",
                "mentalray",
                "mayavector",
                "mayahardware",
                "mayahardware2",
                "renderman",
                "rendermanris",
                "turtle",
                "gelato",
                "vray",
                "mentalrayexport",
                "finalrender",
                "mayakrakatoa",
                "arnold",
                "arnoldexport",
                "octanerender",
                "causticvisualizer",
                "redshift",
                "ifmirayphotoreal",
            }:
                return '$rl="' + self.RenderLayer + '";'
            elif self.Renderer == "redshiftexport":
                return "editRenderLayerGlobals -crl " + self.RenderLayer + ";"
            elif self.Renderer == "3delight":
                return (
                    'string $node = "'
                    + self.RenderLayer
                    + '"; if ($node == "") $node = "defaultRenderLayer"; DRG_connectRenderPassAttr("layerToRender", $node);'
                )
            elif self.Renderer in {"maxwell", "maxwellexport"}:
                return (
                    "selectLayerMembers "
                    + self.RenderLayer
                    + "; setAttr defaultRenderGlobals.renderAll 0;"
                )
            else:
                return '$rl="' + self.RenderLayer + '";'
        return ""

    def GetMotionBlurCommand(self):
        if len(self.MotionBlur) > 0:
            if self.Renderer == "mayasoftware" or self.Renderer == "gelato":
                return (
                    "removeRenderLayerAdjustmentAndUnlock .motionBlur; catch(`setAttr .motionBlur "
                    + self.MotionBlur
                    + "`);"
                )
            elif (
                self.Renderer == "mayahardware"
                or self.Renderer == "mayahardware2"
            ):
                return (
                    "removeRenderLayerAdjustmentAndUnlock .enableMotionBlur; catch(`setAttr .enableMotionBlur "
                    + self.MotionBlur
                    + "`);"
                )
            elif self.Renderer == "finalrender":
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultFinalRenderSettings.motionBlur; catch(`setAttr defaultFinalRenderSettings.motionBlur "
                    + self.MotionBlur
                    + "`);"
                )
            elif self.Renderer == "ifmirayphotoreal":
                return (
                    "removeRenderLayerAdjustmentAndUnlock ifmGlobalsCommon.motionBlur; catch(`setAttr ifmGlobalsCommon.motionBlur "
                    + self.MotionBlur
                    + "`);"
                )
        return ""

    def GetAntiAliasingCommand(self):
        if len(self.AntiAliasing) > 0:
            if self.Renderer == "mayasoftware":
                antialiasing = self.AntiAliasing
                if antialiasing == "low":
                    antialiasing = "3"
                elif antialiasing == "medium":
                    antialiasing = "2"
                elif antialiasing == "high":
                    antialiasing = "1"
                elif antialiasing == "highest":
                    antialiasing = "0"
                return (
                    "removeRenderLayerAdjustmentAndUnlock defaultRenderQuality.edgeAntiAliasing; catch(`setAttr defaultRenderQuality.edgeAntiAliasing "
                    + antialiasing
                    + "`);"
                )
        return ""

    def GetThreadsCommand(self):
        if len(self.Threads) > 0:
            if self.Renderer in ["mayasoftware"]:
                return (
                    "setAttr .numCpusToUse "
                    + self.Threads
                    + "; if(!`about -mac`) { threadCount -n "
                    + self.Threads
                    + "; };"
                )
            elif self.Renderer in ["mentalray"]:
                numThreads = int(self.Threads)
                if numThreads > 0:
                    return (
                        "global int $g_mrBatchRenderCmdOption_NumThreadOn = true; global int $g_mrBatchRenderCmdOption_NumThread = "
                        + self.Threads
                        + ";"
                    )
                else:
                    return "global int $g_mrBatchRenderCmdOption_NumThreadAutoOn = true; global int $g_mrBatchRenderCmdOption_NumThreadAuto = true;"
            elif self.Renderer in ["vray"]:
                return (
                    'setAttr "vraySettings.sys_max_threads" '
                    + self.Threads
                    + ";"
                )
            elif self.Renderer in [
                "renderman",
                "rendermanris",
                "rendermanexport",
            ]:
                return (
                    'rmanSetGlobalAttr "limits:threads" "'
                    + self.Threads
                    + '";'
                )
            elif self.Renderer in {"renderman22", "renderman22export"}:
                return '$options += " -numThreads %s";' % self.Threads
            elif self.Renderer == "3delight":
                return (
                    "removeRenderLayerAdjustmentAndUnlock .numberOfCPUs; catch(`setAttr .numberOfCPUs "
                    + self.Threads
                    + "`);"
                )
            elif self.Renderer in ["finalrender"]:
                return "$numCpu = " + self.Threads + ";"
            elif self.Renderer in ["maxwell", "maxwellexport"]:
                return (
                    "removeRenderLayerAdjustmentAndUnlock maxwellRenderOptions.numThreads; catch(`setAttr maxwellRenderOptions.numThreads "
                    + self.Threads
                    + "`);"
                )
            elif self.Renderer in ["arnold", "arnoldexport"]:
                numThreads = int(self.Threads)
                if numThreads > 0:
                    return (
                        "removeRenderLayerAdjustmentAndUnlock defaultArnoldRenderOptions.threads_autodetect; catch(`setAttr defaultArnoldRenderOptions.threads_autodetect 0`);removeRenderLayerAdjustmentAndUnlock defaultArnoldRenderOptions.threads;catch(`setAttr defaultArnoldRenderOptions.threads "
                        + self.Threads
                        + "`);"
                    )
                else:
                    return "removeRenderLayerAdjustmentAndUnlock defaultArnoldRenderOptions.threads_autodetect; catch(`setAttr defaultArnoldRenderOptions.threads_autodetect 1`);"
        return ""

    def GetMemoryCommand(self):
        if self.Renderer == "mentalray":
            autoMemoryLimit = self.GetBooleanPluginInfoEntryWithDefault(
                "AutoMemoryLimit", True
            )
            if autoMemoryLimit:
                return "global int $g_mrBatchRenderCmdOption_MemLimitAutoOn = true; global int $g_mrBatchRenderCmdOption_MemLimitAuto = true;"
            else:
                memoryLimit = self.GetIntegerPluginInfoEntryWithDefault(
                    "MemoryLimit", 0
                )
                if memoryLimit >= 0:
                    return (
                        "global int $g_mrBatchRenderCmdOption_MemLimitOn = true; global int $g_mrBatchRenderCmdOption_MemLimit = "
                        + str(memoryLimit)
                        + ";"
                    )
        elif self.Renderer == "vray":
            if self.GetBooleanPluginInfoEntryWithDefault(
                "VRayAutoMemoryEnabled", False
            ):
                self.LogInfo("Auto memory detection for VRay enabled")

                # This value is already in MB.
                autoMemoryBuffer = self.GetLongPluginInfoEntryWithDefault(
                    "VRayAutoMemoryBuffer", 500
                )
                self.LogInfo(
                    "Auto memory buffer is " + str(autoMemoryBuffer) + " MB"
                )

                # Convert this value to MB.
                availableMemory = (SystemUtils.GetAvailableRam() / 1024) / 1024
                self.LogInfo(
                    "Available system memory is "
                    + str(availableMemory)
                    + " MB"
                )

                # Now calculate the limit we should pass to vray.
                autoMemoryLimit = availableMemory - autoMemoryBuffer
                self.LogInfo(
                    "Setting VRay dynamic memory limit to "
                    + str(autoMemoryLimit)
                    + " MB"
                )

                return (
                    'setAttr "vraySettings.sys_rayc_dynMemLimit" '
                    + str(autoMemoryLimit)
                    + ";"
                )
            else:
                self.LogInfo("Auto memory detection for VRay disabled")
        return ""

    def GetRegionCommand(self):
        if self.RegionRendering:
            if (
                len(self.Left) > 0
                and len(self.Right) > 0
                and len(self.Top) > 0
                and len(self.Bottom) > 0
            ):
                if (
                    self.Renderer == "mayasoftware"
                    or self.Renderer == "redshift"
                ):
                    # setMayaSoftwareRegion is a shorthand to set the region attributes of the defaultRenderGlobals which both mayaSoftware and Redshift use
                    return (
                        "setMayaSoftwareRegion("
                        + self.Left
                        + ","
                        + self.Right
                        + ","
                        + self.Top
                        + ","
                        + self.Bottom
                        + ");"
                    )
                elif self.Renderer == "mentalray":
                    return (
                        "setMentalRayRenderRegion("
                        + self.Left
                        + ","
                        + self.Right
                        + ","
                        + self.Top
                        + ","
                        + self.Bottom
                        + ");"
                    )
                elif self.Renderer in {
                    "renderman",
                    "rendermanris",
                    "renderman22",
                }:
                    if len(self.Width) > 0 and len(self.Height) > 0:
                        width = int(self.Width)
                        height = int(self.Height)
                        if width > 0 and height > 0:
                            leftPercent = float(self.Left) / float(width)
                            rightPercent = float(self.Right) / float(width)
                            topPercent = float(self.Top) / float(height)
                            bottomPercent = float(self.Bottom) / float(height)
                            if self.Renderer == "renderman22":
                                return (
                                    "setAttr rmanGlobals.opt_cropWindowEnable 1;setAttr rmanGlobals.opt_cropWindowTopLeft %s %s; setAttr rmanGlobals.opt_cropWindowBottomRight %s %s;"
                                    % (
                                        leftPercent,
                                        topPercent,
                                        rightPercent,
                                        bottomPercent,
                                    )
                                )
                            else:
                                return (
                                    "rmanSetCropWindow "
                                    + str(leftPercent)
                                    + " "
                                    + str(rightPercent)
                                    + " "
                                    + str(topPercent)
                                    + " "
                                    + str(bottomPercent)
                                    + ";"
                                )

                elif self.Renderer == "turtle":
                    return (
                        '$extraOptions += "-region '
                        + self.Left
                        + " "
                        + self.Top
                        + " "
                        + self.Right
                        + " "
                        + self.Bottom
                        + '";'
                    )
                elif self.Renderer == "vray":
                    # return 'global int $batchDoRegion; $batchDoRegion=1; setAttr defaultRenderGlobals.left ' + self.Left + '; setAttr defaultRenderGlobals.rght ' + self.Right + '; setAttr defaultRenderGlobals.bot ' + self.Bottom + '; setAttr defaultRenderGlobals.top ' + self.Top + ';'
                    return (
                        "vraySetBatchDoRegion("
                        + self.Left
                        + ","
                        + self.Right
                        + ","
                        + self.Top
                        + ","
                        + self.Bottom
                        + ");;"
                    )
                elif self.Renderer == "3delight":
                    if len(self.Width) > 0 and len(self.Height) > 0:
                        width = int(self.Width)
                        height = int(self.Height)
                        if width > 0 and height > 0:
                            leftPercent = float(self.Left) / float(width)
                            rightPercent = float(self.Right) / float(width)
                            topPercent = float(self.Top) / float(height)
                            bottomPercent = float(self.Bottom) / float(height)
                            regionBuilder = StringBuilder()
                            regionBuilder.AppendLine(
                                "removeRenderLayerAdjustmentAndUnlock .useCropWindow; catch(`setAttr .useCropWindow 1`);"
                            )
                            regionBuilder.AppendLine(
                                "removeRenderLayerAdjustmentAndUnlock .cropMinX; catch(`setAttr .cropMinX "
                                + str(leftPercent)
                                + "`);"
                            )
                            regionBuilder.AppendLine(
                                "removeRenderLayerAdjustmentAndUnlock .cropMinY; catch(`setAttr .cropMinY "
                                + str(topPercent)
                                + "`);"
                            )
                            regionBuilder.AppendLine(
                                "removeRenderLayerAdjustmentAndUnlock .cropMaxX; catch(`setAttr .cropMaxX "
                                + str(rightPercent)
                                + "`);"
                            )
                            regionBuilder.AppendLine(
                                "removeRenderLayerAdjustmentAndUnlock .cropMaxY; catch(`setAttr .cropMaxY "
                                + str(bottomPercent)
                                + "`);"
                            )
                            return regionBuilder.ToString()
                elif self.Renderer == "finalrender":
                    return (
                        "$irr=1; $frr[0]="
                        + self.Left
                        + "; $frr[1]="
                        + self.Bottom
                        + "; $frr[2]="
                        + self.Right
                        + "; $frr[3]="
                        + self.Top
                        + ";"
                    )
                elif self.Renderer == "arnold":
                    return (
                        "setAttr defaultArnoldRenderOptions.regionMinX "
                        + self.Left
                        + ";setAttr defaultArnoldRenderOptions.regionMaxX "
                        + self.Right
                        + ";setAttr defaultArnoldRenderOptions.regionMinY "
                        + self.Top
                        + ";setAttr defaultArnoldRenderOptions.regionMaxY "
                        + self.Bottom
                        + ";;"
                    )
                elif self.Renderer == "ifmirayphotoreal":
                    width = int(self.Width)
                    height = int(self.Height)
                    if width > 0 and height > 0:
                        leftPercent = float(self.Left) / float(width)
                        rightPercent = float(self.Right) / float(width)
                        topPercent = float(self.Top) / float(height)
                        bottomPercent = float(self.Bottom) / float(height)

                        regionBuilder = StringBuilder()
                        regionBuilder.AppendLine(
                            "removeRenderLayerAdjustmentAndUnlock ifmGlobalsCommon.region; catch(`setAttr ifmGlobalsCommon.region 1`);"
                        )
                        regionBuilder.AppendLine(
                            "removeRenderLayerAdjustmentAndUnlock ifmGlobalsCommon.regionLeft; catch(`setAttr ifmGlobalsCommon.regionLeft "
                            + str(leftPercent)
                            + "`);"
                        )
                        regionBuilder.AppendLine(
                            "removeRenderLayerAdjustmentAndUnlock ifmGlobalsCommon.regionTop; catch(`setAttr ifmGlobalsCommon.regionTop "
                            + str(topPercent)
                            + "`);"
                        )
                        regionBuilder.AppendLine(
                            "removeRenderLayerAdjustmentAndUnlock ifmGlobalsCommon.regionRight; catch(`setAttr ifmGlobalsCommon.regionRight "
                            + str(rightPercent)
                            + "`);"
                        )
                        regionBuilder.AppendLine(
                            "removeRenderLayerAdjustmentAndUnlock ifmGlobalsCommon.regionBottom; catch(`setAttr ifmGlobalsCommon.regionBottom "
                            + str(bottomPercent)
                            + "`);"
                        )
                        return regionBuilder.ToString()
        return ""

    def GetVerboseCommand(self):
        if self.Renderer == "mentalray":
            self.Verbosity = self.GetPluginInfoEntryWithDefault(
                "MentalRayVerbose", "Progress Messages"
            )

            verbosity = "5"
            if self.Verbosity == "No Messages":
                verbosity = "0"
            elif self.Verbosity == "Fatal Messages Only":
                verbosity = "1"
            elif self.Verbosity == "Error Messages":
                verbosity = "2"
            elif self.Verbosity == "Warning Messages":
                verbosity = "3"
            elif self.Verbosity == "Info Messages":
                verbosity = "4"
            elif self.Verbosity == "Progress Messages":
                verbosity = "5"
            elif self.Verbosity == "Detailed Messages (Debug)":
                verbosity = "6"
            return (
                "global int $g_mrBatchRenderCmdOption_VerbosityOn = true; global int $g_mrBatchRenderCmdOption_Verbosity = "
                + verbosity
                + ";"
            )
        elif self.Renderer == "finalrender":
            return "setAttr defaultFinalRenderSettings.displayMessages on; setAttr defaultFinalRenderSettings.verboseLevel 2;"
        elif self.Renderer == "arnold" or self.Renderer == "arnoldexport":
            # Create a named tuple so the properties are easier to access later on.
            ArnoldVerbosity = namedtuple("ArnoldVerbosity", ["default", "max"])
            # Set the default verbosity settings to match the newest version at this time
            arnoldVerboseDict = defaultdict(
                lambda: ArnoldVerbosity(default=2, max=3),
                {
                    1: ArnoldVerbosity(default=1, max=2),
                    2: ArnoldVerbosity(default=1, max=2),
                    3: ArnoldVerbosity(default=2, max=3),
                },
            )

            mtoaVersion = self.GetIntegerPluginInfoEntryWithDefault(
                "MayaToArnoldVersion", 2
            )
            verboseSettings = arnoldVerboseDict[mtoaVersion]
            verbosity = self.GetIntegerPluginInfoEntryWithDefault(
                "ArnoldVerbose", verboseSettings.default
            )
            # Arnold will error if the verbosity level is higher than the maximum
            if verbosity > verboseSettings.max:
                verbosity = verboseSettings.max
            self.Verbosity = str(verbosity)
            return (
                "removeRenderLayerAdjustmentAndUnlock defaultArnoldRenderOptions.log_verbosity; catch(`setAttr defaultArnoldRenderOptions.log_verbosity "
                + self.Verbosity
                + "`);"
            )
        elif self.Renderer == "octanerender":
            return "removeRenderLayerAdjustmentAndUnlock octaneSettings.Verbose; catch(`setAttr octaneSettings.Verbose true`);"
        elif self.Renderer == "causticvisualizer":
            return "removeRenderLayerAdjustmentAndUnlock CausticVisualizerBatchSettings.consoleMaxVerbosityLevel; catch(`setAttr CausticVisualizerBatchSettings.consoleMaxVerbosityLevel 4`);"
        elif self.Renderer == "redshift":
            verbosity = self.GetIntegerPluginInfoEntryWithDefault(
                "RedshiftVerbose", 2
            )
            if verbosity > 2:
                verbosity = 2
            return "setAttr redshiftOptions.logLevel " + str(verbosity) + ";"
        elif self.Renderer == "vray" or self.Renderer == "vrayexport":
            return 'setAttr "vraySettings.sys_progress_increment" 1;'
        return ""

    def GetMiscCommands(self):
        if self.Renderer == "maxwell" or self.Renderer == "maxwellexport":
            cmdArguments = ""

            slaveFound = False
            # thisSlave = Environment.MachineName.lower()
            thisSlave = self.GetSlaveName().lower()
            interactiveSlaves = self.GetConfigEntryWithDefault(
                "MaxwellInteractiveSlaves", ""
            ).split(",")
            for slave in interactiveSlaves:
                if slave.lower().strip() == thisSlave:
                    self.LogInfo(
                        "This Worker is in the Maxwell interactive license list - an interactive license for Maxwell will be used instead of a render license"
                    )
                    slaveFound = True
                    break
            if not slaveFound:
                cmdArguments += " -node"

            if self.GetBooleanPluginInfoEntryWithDefault(
                "MaxwellResumeRender", False
            ):
                cmdArguments += " -trytoresume"

            if len(cmdArguments) > 0:
                return (
                    'setAttr -type "string" maxwellRenderOptions.cmdLine "'
                    + cmdArguments.strip()
                    + '";'
                )

        elif self.Renderer == "arnold":
            cmdArguments = (
                'removeRenderLayerAdjustmentAndUnlock defaultArnoldRenderOptions.abortOnLicenseFail; setAttr "defaultArnoldRenderOptions.abortOnLicenseFail" '
                + str(
                    int(
                        self.GetBooleanConfigEntryWithDefault(
                            "AbortOnArnoldLicenseFail", True
                        )
                    )
                )
                + ";"
            )
            cmdArguments += "removeRenderLayerAdjustmentAndUnlock defaultArnoldRenderOptions.renderType; catch(`setAttr defaultArnoldRenderOptions.renderType 0`);"

            return cmdArguments
        elif self.Renderer == "renderman":
            return '$renderer="renderMan"; $globals="renderManGlobals";'

        elif self.Renderer == "rendermanris":
            return (
                '$renderer = "renderManRIS"; $globals = "renderManRISGlobals";'
            )

        elif self.Renderer == "rendermanexport":
            if self.GetBooleanPluginInfoEntryWithDefault(
                "RenderWithRis", False
            ):
                return '$renderer = "renderManRIS"; $globals = "renderManRISGlobals";'
            else:
                return '$renderer="renderMan"; $globals="renderManGlobals";'
        elif self.Renderer == "renderman22export":
            return r'$options += " -rib -ribFile \\\"%s/%s\\\""; ' % (
                self.GetPluginInfoEntry("RIBDirectory"),
                self.GetPluginInfoEntry("RIBPrefix"),
            )

        elif self.Renderer == "redshift":
            redshiftMiscArgs = []
            selectedGPUs = self.GetGpuOverrides()
            if len(selectedGPUs) > 0:
                gpus = ",".join(str(gpu) for gpu in selectedGPUs)
                self.LogInfo(
                    "This Worker is overriding its GPU affinity, so the following GPUs will be used by RedShift: "
                    + gpus
                )
                redshiftMiscArgs.append(
                    "redshiftSelectCudaDevices({" + gpus + "});"
                )

            if self.RegionRendering:

                renderElementIndex = 0
                while True:
                    renderElementNode = self.GetPluginInfoEntryWithDefault(
                        "RenderElementNodeName" + str(renderElementIndex), None
                    )
                    if not renderElementNode:
                        break

                    renderElementImagePrefixEntry = (
                        "RenderElement"
                        + str(renderElementIndex)
                        + "RegionPrefix"
                    )
                    if self.SingleRegionJob:
                        renderElementImagePrefixEntry += self.SingleRegionIndex

                    renderElementImagePrefix = self.GetPluginInfoEntryWithDefault(
                        renderElementImagePrefixEntry, None
                    )
                    redshiftMiscArgs.append(
                        "removeRenderLayerAdjustmentAndUnlock "
                        + renderElementNode
                        + '.filePrefix; setAttr -type "string" '
                        + renderElementNode
                        + '.filePrefix "'
                        + renderElementImagePrefix
                        + '";'
                    )
                    renderElementIndex += 1
            return "\n".join(redshiftMiscArgs)

        elif (
            self.Renderer == "mayakrakatoa"
            and self.KrakatoaJobFileContainsKrakatoaParameters
        ):
            return (
                'setAttr "MayaKrakatoaRenderSettings.finalPassDensity" '
                + self.KrakatoaFinalPassDensity
                + ';\nsetAttr "MayaKrakatoaRenderSettings.finalPassDensityExponent" '
                + self.KrakatoaFinalPassDensityExponent
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.useLightingPassDensity" '
                + self.KrakatoaUseLightingPassDensity
                + ';\nsetAttr "MayaKrakatoaRenderSettings.lightingPassDensity" '
                + self.KrakatoaLightingPassDensity
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.lightingPassDensityExponent" '
                + self.KrakatoaLightingPassDensityExponent
                + ';\nsetAttr "MayaKrakatoaRenderSettings.useEmissionStrength" '
                + self.KrakatoaUseEmissionStrength
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.emissionStrength" '
                + self.KrakatoaEmissionStrength
                + ';\nsetAttr "MayaKrakatoaRenderSettings.emissionStrengthExponent" '
                + self.KrakatoaEmissionStrengthExponent
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.useEmission" '
                + self.KrakatoaUseEmission
                + ';\nsetAttr "MayaKrakatoaRenderSettings.useAbsorption" '
                + self.KrakatoaUseAbsorption
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.enableMotionBlur" '
                + self.KrakatoaEnableMotionBlur
                + ';\nsetAttr "MayaKrakatoaRenderSettings.motionBlurParticleSegments" '
                + self.KrakatoaMotionBlurParticleSegments
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.jitteredMotionBlur" '
                + self.KrakatoaJitteredMotionBlur
                + ';\nsetAttr "MayaKrakatoaRenderSettings.shutterAngle" '
                + self.KrakatoaShutterAngle
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.enableDOF" '
                + self.KrakatoaEnableDOF
                + ';\nsetAttr "MayaKrakatoaRenderSettings.sampleRateDOF" '
                + self.KrakatoaSampleRateDOF
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.enableMatteObjects" '
                + self.KrakatoaEnableMatteObjects
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.renderingMethod" '
                + self.KrakatoaRenderingMethod
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.voxelSize" '
                + self.KrakatoaVoxelSize
                + ';\nsetAttr "MayaKrakatoaRenderSettings.voxelFilterRadius" '
                + self.KrakatoaVoxelFilterRadius
                + ';\n\
                setAttr "MayaKrakatoaRenderSettings.forceEXROutput" '
                + self.KrakatoaForceEXROutput
                + ";\n"
            )

        elif self.Renderer == "octanerender":
            miscBuilder = StringBuilder()
            maxSamples = self.GetPluginInfoEntryWithDefault(
                "OctaneMaxSamples", ""
            )
            if maxSamples != "":
                miscBuilder.AppendLine(
                    "removeRenderLayerAdjustmentAndUnlock octaneSettings.MaxSamples; catch(`setAttr octaneSettings.MaxSamples "
                    + maxSamples
                    + "`);"
                )

            selectedGPUs = self.GetGpuOverrides()

            if len(selectedGPUs) > 0:
                miscBuilder.AppendLine("for( $r = 0;$r< 8;$r++ )")
                miscBuilder.AppendLine("{")
                miscBuilder.AppendLine("   setAttr octaneSettings.GPU[$r] 0;")
                miscBuilder.AppendLine("};")

                selectedGPUs = [str(x) for x in selectedGPUs]

                for gpuId in selectedGPUs:
                    miscBuilder.AppendLine(
                        "setAttr octaneSettings.GPU[" + gpuId + "] 1;"
                    )

                gpus = ",".join(selectedGPUs)
                self.LogInfo(
                    "This Worker is overriding its GPU affinity, so the following GPUs will be used by Octane: "
                    + gpus
                )

            return miscBuilder.ToString()

        elif self.Renderer == "ifmirayphotoreal":

            # If the number of gpus per task is set, then need to calculate the gpus to use.
            gpusPerTask = self.GetIntegerPluginInfoEntryWithDefault(
                "GPUsPerTask", 0
            )
            gpusSelectDevices = self.GetPluginInfoEntryWithDefault(
                "GPUsSelectDevices", ""
            )
            useCpus = self.GetBooleanPluginInfoEntryWithDefault(
                "IRayUseCpus", True
            )
            cpuLoad = self.GetFloatPluginInfoEntryWithDefault("IRayCPULoad", 4)
            maxSamples = self.GetIntegerPluginInfoEntryWithDefault(
                "IRayMaxSamples", 1024
            )

            miscBuilder = StringBuilder()

            selectedGPUs = self.GetGpuOverrides()
            if len(selectedGPUs) > 0:
                miscBuilder.AppendLine(
                    "$resourceCount = `ifmResource -count`;"
                )
                miscBuilder.AppendLine("for( $r = 1;$r<$resourceCount;$r++ )")
                miscBuilder.AppendLine("{")
                miscBuilder.AppendLine("   ifmResource -d $r;")
                miscBuilder.AppendLine("};")

                gpuList = []
                for gpuId in selectedGPUs:
                    gpuList.append(str(gpuId))
                    miscBuilder.AppendLine(
                        "ifmResource -e " + str(gpuId + 1) + ";"
                    )

                gpus = ",".join(gpuList)
                self.LogInfo(
                    "This Worker is overriding its GPU affinity, so the following GPUs will be used by IRay: "
                    + gpus
                )

            if useCpus:
                miscBuilder.AppendLine("ifmResource -e 0;")
                miscBuilder.AppendLine(
                    "ifmResource -cl " + str(cpuLoad) + " 0;"
                )
                self.LogInfo(
                    "Using CPUs for rendering with IRay, the following will be used for the CPU load: "
                    + str(cpuLoad)
                )
            else:
                miscBuilder.AppendLine("ifmResource -d 0;")

            miscBuilder.AppendLine(
                "setAttr ifmGlobalsIrayPhotoreal.irayMaxSamples "
                + str(maxSamples)
                + ";"
            )

            return miscBuilder.ToString()

        elif (
            self.GetBooleanPluginInfoEntryWithDefault("Animation", True)
            and self.Renderer == "vray"
        ):
            # New versions of Vray have a second frame list that use different commmands, so we'll just set it to the standard option
            miscBuilder = StringBuilder()
            miscBuilder.AppendLine(
                'if( `attributeExists "animType" vraySettings` )'
            )
            miscBuilder.AppendLine("{")
            miscBuilder.AppendLine('   setAttr "vraySettings.animType" 1;')
            miscBuilder.AppendLine("}")
            return miscBuilder.ToString()

        return ""

    def GetRenderCommand(self):
        if self.Renderer == "file" or (
            self.UsingRenderLayers and len(self.RenderLayer) == 0
        ):
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "", "");'
        elif self.Renderer == "mayasoftware":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "mayaSoftware", $opt);'
        elif self.Renderer == "mayahardware":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "mayaHardware", $hardwareRenderOptions);'
        elif self.Renderer == "mayahardware2":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "mayaHardware2", $ogsRenderOptions);'
        elif self.Renderer == "mayavector":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "mayaVector", "");'
        elif self.Renderer == "mentalray":
            return 'setMayaSoftwareLayers($rl, $rp); miCreateMentalJobs(); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "mentalRay", $opt);'
        elif (
            self.Renderer == "renderman"
            or self.Renderer == "rendermanris"
            or self.Renderer == "rendermanexport"
        ):
            return "setMayaSoftwareLayers($rl, $rp); setCurrentRenderer($renderer); renderManExecCmdlineRender($spoolmode, $chunksize, $rib, $ui);"
        elif self.Renderer in {"renderman22", "renderman22export"}:
            return 'setMayaSoftwareLayers($rl, ""); mayaBatchRenderProcedure(0, "", "", "renderman", $options);'
        elif self.Renderer == "turtle":
            return 'ilrSetRenderLayersAndPasses($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "turtle", $extraOptions);'
        elif self.Renderer == "gelato":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "gelato", $opt);'
        elif self.Renderer == "arnold":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize);mayaBatchRenderProcedure(0, "", "", "arnold", $opt);'
        elif self.Renderer == "arnoldexport":
            cmdArguments = ['string $exportString = "arnoldExportAss";']

            if self.RenderLayer:
                cmdArguments.append(
                    "editRenderLayerGlobals -currentRenderLayer $rl;"
                )
                cmdArguments.append('setMayaSoftwareLayers($rl, "");')

            if self.Animation:
                # if you specifiy the start and end frame when exporting the frame number is automatically added to the ass file.
                cmdArguments.append(
                    '$exportString = $exportString + " -sf '
                    + self.StartFrame
                    + " -ef "
                    + self.EndFrame
                    + '";'
                )
            else:
                # Set the current frame so the correct frame is exported but the frame number is not added to the filename
                cmdArguments.append("currentTime -e " + self.StartFrame + ";")

            if self.GetBooleanPluginInfoEntryWithDefault(
                "ArnoldExportCompressed", False
            ):
                cmdArguments.append('$exportString = $exportString + " -c";')

            cmdArguments.append(
                'if(`getAttr defaultArnoldRenderOptions.binaryAss` == 0){$exportString = $exportString + " -a";}'
            )
            cmdArguments.append(
                'if(`getAttr defaultArnoldRenderOptions.outputAssBoundingBox`){$exportString = $exportString + " -bb";}'
            )
            cmdArguments.append(
                'if(`getAttr defaultArnoldRenderOptions.expandProcedurals`){$exportString = $exportString + " -ep";}'
            )
            cmdArguments.append(
                'if(`getAttr defaultArnoldRenderOptions.exportAllShadingGroups`){$exportString = $exportString + " -shg";	}'
            )
            cmdArguments.append("eval $exportString;")

            return "\n".join(cmdArguments)
        elif self.Renderer == "redshift":
            # somewhere in between redshift 2.5.30 and 2.5.47, they changed from using redshiftOptions.imageFilePrefix to defaultRenderGlobals.imageFilePrefix
            # they overwrote defaultRenderGlobals.imageFilePrefix with whatever was in redshiftOptions.imageFilePrefix when the scene was loaded, causing
            # a different output path for the first frame rendered
            # this fix was given to us by Nicolas from Redshift
            redshiftRender = [
                "int $buildNumber = (int)$redshiftVersions[2];",
                'if ($redshiftMajorVersion == 2.5 && $buildNumber > 30 && $buildNumber < 47 && size(`getAttr "defaultRenderGlobals.imageFilePrefix"`) > 0) {',
                'setAttr -type "string" "redshiftOptions.imageFilePrefix" "";',
                "}",
                'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); redshiftBatchRender("");',
            ]
            return "".join(redshiftRender)
        elif self.Renderer == "redshiftexport":
            if self.Animation:
                return (
                    "currentTime "
                    + self.StartFrame
                    + "; rsProxy -fp $rp -s `getAttr defaultRenderGlobals.startFrame` -e `getAttr defaultRenderGlobals.endFrame` -b `getAttr defaultRenderGlobals.byFrameStep` ;"
                )
            else:
                return "rsProxy -fp $rp;"
        elif self.Renderer == "vray":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "vray", $opt);'
        elif self.Renderer == "mayakrakatoa":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "MayaKrakatoa", $options);'
        elif self.Renderer == "3delight":
            return 'setMayaSoftwareLayers($rl, $rp); mayaBatchRenderProcedure(0, "", "", "_3delight", $opt);'
        elif self.Renderer == "vrayexport":
            exportFile = RepositoryUtils.CheckPathMapping(
                self.GetPluginInfoEntry("VRayExportFile")
            ).replace("\\", "/")

            exportBuilder = StringBuilder()
            exportBuilder.AppendLine(
                'setAttr vraySettings.vrscene_on 1; setAttr -type "string" vraySettings.vrscene_filename "'
                + exportFile
                + '";;'
            )
            exportBuilder.AppendLine(
                "setAttr vraySettings.vrscene_render_on 0;;"
            )
            exportBuilder.AppendLine(
                'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "vray", $opt);;'
            )
            return exportBuilder.ToString()
        elif self.Renderer == "mentalrayexport":
            exportFile = RepositoryUtils.CheckPathMapping(
                self.GetPluginInfoEntry("MentalRayExportfile")
            ).replace("\\", "/")

            exportBuilder = StringBuilder()
            exportBuilder.AppendLine('$filename = "' + exportFile + '";')

            if self.GetBooleanPluginInfoEntryWithDefault(
                "MentalRayExportBinary", False
            ):
                exportBuilder.AppendLine('$opt +=" -binary ";')
            else:
                exportBuilder.AppendLine(
                    '$opt +=" -tabstop '
                    + self.GetPluginInfoEntryWithDefault(
                        "MentalRayExportTabStop", "8"
                    )
                    + '";'
                )

            perFrame = self.GetIntegerPluginInfoEntryWithDefault(
                "MentalRayExportPerFrame", 2
            )
            exportBuilder.AppendLine(
                '$opt +=" -perframe ' + str(perFrame) + '";'
            )
            if perFrame != 0:
                exportBuilder.AppendLine(
                    '$opt +=" -padframe '
                    + self.GetPluginInfoEntryWithDefault(
                        "MentalRayExportPadFrame", "4"
                    )
                    + '";'
                )

            if not self.GetBooleanPluginInfoEntryWithDefault(
                "MentalRayExportPerLayer", False
            ):
                exportBuilder.AppendLine("$perLayer=0;")

            passContributionMaps = self.GetBooleanPluginInfoEntryWithDefault(
                "MentalRayExportPassContributionMaps", False
            )
            if passContributionMaps:
                exportBuilder.AppendLine('$opt +=" -pcm";')

            passUserData = self.GetBooleanPluginInfoEntryWithDefault(
                "MentalRayExportPassUserData", False
            )
            if passUserData:
                exportBuilder.AppendLine('$opt +=" -pud";')

            pathnames = self.GetPluginInfoEntryWithDefault(
                "MentalRayExportPathNames", ""
            ).strip()
            if len(pathnames) > 0:
                pathnames = pathnames.replace("1", "a")  # absolute
                pathnames = pathnames.replace("2", "r")  # relative
                pathnames = pathnames.replace("3", "n")  # none
                exportBuilder.AppendLine(
                    '$opt +=" -exportPathNames \\"' + pathnames + '\\"";'
                )

            if self.GetBooleanPluginInfoEntryWithDefault(
                "MentalRayExportFragment", False
            ):
                exportBuilder.AppendLine('$opt +=" -fragmentExport ";')
                if self.GetBooleanPluginInfoEntryWithDefault(
                    "MentalRayExportFragmentMaterials", False
                ):
                    exportBuilder.AppendLine('$opt +=" -fragmentMaterials ";')
                if self.GetBooleanPluginInfoEntryWithDefault(
                    "MentalRayExportFragmentShaders", False
                ):
                    exportBuilder.AppendLine(
                        '$opt +=" -fragmentIncomingShdrs ";'
                    )
                if self.GetBooleanPluginInfoEntryWithDefault(
                    "MentalRayExportFragmentChildDag", False
                ):
                    exportBuilder.AppendLine('$opt +=" -fragmentChildDag ";')

            filters = self.GetPluginInfoEntryWithDefault(
                "MentalRayExportFilterString", ""
            ).strip()
            if len(filters) > 0:
                exportBuilder.AppendLine(
                    '$opt +=" -exportFilterString ' + filters + '";'
                )

            exportBuilder.AppendLine(
                "setMayaSoftwareLayers($rl, $rp); miCreateMentalJobs(); setImageSizePercent($resize); if ($perLayer) { mentalrayBatchExportProcedure($filename, $opt); } else { mentalrayBatchExportSingleFile($filename, $opt); };"
            )

            return exportBuilder.ToString()
        elif self.Renderer == "finalrender":
            return "frSetDRBatchHosts($strHosts); setMayaSoftwareLayers($rl, $rp); if (!$irr) finalRender -batch -kpi $kpi -rep $rep -amt $amt -n $numCpu; else finalRender -batch -kpi $kpi -rep $rep -amt $amt -n $numCpu -rr $frr[0] $frr[1] $frr[2] $frr[3];"
        elif self.Renderer == "maxwell":
            maxwellBuilder = StringBuilder()

            renderTime = self.GetPluginInfoEntryWithDefault(
                "MaxwellRenderTime", ""
            )
            if len(renderTime) > 0:
                maxwellBuilder.AppendLine(
                    "removeRenderLayerAdjustmentAndUnlock maxwellRenderOptions.renderTime; catch(`setAttr maxwellRenderOptions.renderTime "
                    + renderTime
                    + "`);"
                )

            samplingLevel = self.GetPluginInfoEntryWithDefault(
                "MaxwellSamplingLevel", ""
            )
            if len(samplingLevel) > 0:
                maxwellBuilder.AppendLine(
                    "removeRenderLayerAdjustmentAndUnlock maxwellRenderOptions.samplingLevel; catch(`setAttr maxwellRenderOptions.samplingLevel "
                    + samplingLevel
                    + "`);"
                )

            maxwellBuilder.AppendLine(
                'string $maxwellVersion = `pluginInfo -q -version "maxwell"`;'
            )
            maxwellBuilder.AppendLine("string $maxwellVersionTokens[];")
            maxwellBuilder.AppendLine(
                'tokenize($maxwellVersion, ".", $maxwellVersionTokens);'
            )
            maxwellBuilder.AppendLine(
                "int $majorVersion = $maxwellVersionTokens[0];"
            )
            maxwellBuilder.AppendLine(
                "int $minorVersion = $maxwellVersionTokens[1];"
            )
            maxwellBuilder.AppendLine(
                "if( $majorVersion > 2 || ( $majorVersion == 2 && $minorVersion >= 5 ) ) {"
            )
            maxwellBuilder.AppendLine('maxwellBatchRender("");')
            maxwellBuilder.AppendLine("} else {")
            maxwellBuilder.AppendLine("maxwell -batchRender;")
            maxwellBuilder.AppendLine("}")

            return maxwellBuilder.ToString()
        elif self.Renderer == "maxwellexport":
            maxwellBuilder = StringBuilder()

            maxwellBuilder.AppendLine(
                "maxwellUnlockAndSet maxwellRenderOptions.persistentMXS 1;"
            )

            mxsFile = self.GetPluginInfoEntryWithDefault("MaxwellMXSFile", "")
            mxsFile = RepositoryUtils.CheckPathMapping(mxsFile).replace(
                "\\", "/"
            )
            if len(mxsFile) > 0:
                maxwellBuilder.AppendLine(
                    'setAttr -type "string" maxwellRenderOptions.mxsPath "'
                    + mxsFile
                    + '";'
                )

            maxwellBuilder.AppendLine(
                "removeRenderLayerAdjustmentAndUnlock maxwellRenderOptions.exportOnly;"
            )
            maxwellBuilder.AppendLine(
                "catch(`setAttr maxwellRenderOptions.exportOnly 1`);"
            )

            maxwellBuilder.AppendLine(
                'string $maxwellVersion = `pluginInfo -q -version "maxwell"`;'
            )
            maxwellBuilder.AppendLine("string $maxwellVersionTokens[];")
            maxwellBuilder.AppendLine(
                'tokenize($maxwellVersion, ".", $maxwellVersionTokens);'
            )
            maxwellBuilder.AppendLine(
                "int $majorVersion = $maxwellVersionTokens[0];"
            )
            maxwellBuilder.AppendLine(
                "int $minorVersion = $maxwellVersionTokens[1];"
            )
            maxwellBuilder.AppendLine(
                "if( $majorVersion > 2 || ( $majorVersion == 2 && $minorVersion >= 5 ) ) {"
            )
            maxwellBuilder.AppendLine('maxwellBatchRender("");')
            maxwellBuilder.AppendLine("} else {")
            maxwellBuilder.AppendLine("maxwell -batchRender;")
            maxwellBuilder.AppendLine("}")

            return maxwellBuilder.ToString()
        elif self.Renderer == "octanerender":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure($interactive, "", "", "OctaneRender", $opt);;'
        elif self.Renderer == "causticvisualizer":
            return 'setMayaSoftwareLayers($rl, $rp);r\n setImageSizePercent($resize);r\n mayaBatchRenderProcedure($interactive, "", "", "CausticVisualizer", $opt);;'
        elif self.Renderer == "ifmirayphotoreal":
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "ifmIrayPhotoreal", "");'
        else:
            return 'setMayaSoftwareLayers($rl, $rp); setImageSizePercent($resize); mayaBatchRenderProcedure(0, "", "", "", "");'

        return ""

    def GetGpuOverrides(self):
        resultGPUs = []

        # If the number of gpus per task is set, then need to calculate the gpus to use.
        gpusPerTask = self.GetIntegerPluginInfoEntryWithDefault(
            "GPUsPerTask", 0
        )
        gpusSelectDevices = self.GetPluginInfoEntryWithDefault(
            "GPUsSelectDevices", ""
        )

        if self.OverrideGpuAffinity():
            overrideGPUs = self.GpuAffinity()
            if gpusPerTask == 0 and gpusSelectDevices != "":
                gpus = gpusSelectDevices.split(",")
                notFoundGPUs = []
                for gpu in gpus:
                    if int(gpu) in overrideGPUs:
                        resultGPUs.append(gpu)
                    else:
                        notFoundGPUs.append(gpu)

                if len(notFoundGPUs) > 0:
                    self.LogWarning(
                        "The Worker is overriding its GPU affinity and the following GPUs do not match the Workers affinity so they will not be used: "
                        + ",".join(notFoundGPUs)
                    )
                if len(resultGPUs) == 0:
                    self.FailRender(
                        "The Worker does not have affinity for any of the GPUs specified in the job."
                    )
            elif gpusPerTask > 0:
                if gpusPerTask > len(overrideGPUs):
                    self.LogWarning(
                        "The Worker is overriding its GPU affinity and the Worker only has affinity for "
                        + str(len(overrideGPUs))
                        + " Workers of the "
                        + str(gpusPerTask)
                        + " requested."
                    )
                    resultGPUs = overrideGPUs
                else:
                    resultGPUs = list(overrideGPUs)[:gpusPerTask]
            else:
                resultGPUs = overrideGPUs
        elif gpusPerTask == 0 and gpusSelectDevices != "":
            resultGPUs = gpusSelectDevices.split(",")

        elif gpusPerTask > 0:
            gpuList = []
            for i in range(
                (self.GetThreadNumber() * gpusPerTask),
                (self.GetThreadNumber() * gpusPerTask) + gpusPerTask,
            ):
                gpuList.append(str(i))
            resultGPUs = gpuList

        resultGPUs = list(resultGPUs)

        return resultGPUs

    def GetThreadCount(self):
        threads = self.GetIntegerPluginInfoEntryWithDefault("MaxProcessors", 0)
        if self.OverrideCpuAffinity() and self.GetBooleanConfigEntryWithDefault(
            "LimitThreadsToCPUAffinity", False
        ):
            affinity = len(self.CpuAffinity())
            if threads == 0:
                threads = affinity
            else:
                threads = min(affinity, threads)

        return str(threads)

    def is_known_fatal_strict_error(self, line):
        """
        Parse a line to determine if it contains a known fatal error.
        :param line: A line of text which we want to check if it contains a known fatal error
        :return: Whether or not the line contains a fatal error
        """
        for known_error in self.fatal_strict_errors:
            # fatal_errors contains a list of strings and non string iterables.
            if isinstance(known_error, string_types):
                if known_error in line:
                    # if known error is a string and is contained in the line then it is a fatal error.
                    return True
            elif all(innerError in line for innerError in known_error):
                # if known_error is a non string iterable which contains strings then it is fatal if everything in the iterable is in the line.
                return True

        return False


class MayaBatchProcess(ManagedProcess):
    deadlinePlugin = None

    Version = 0
    Build = "none"
    SceneFile = ""
    ProjectPath = ""
    StartupScriptPath = ""
    Renderer = ""
    DelayLoadScene = False

    ReadyForInput = False
    FinishedFrameCount = 0

    PreviousFinishedFrame = ""
    SkipNextFrame = False

    vrayRenderingImage = False

    CausticCurrentFrame = 0
    CausticTotalPasses = 0

    def __init__(
        self,
        deadlinePlugin,
        version,
        build,
        sceneFile,
        projectPath,
        startupScriptPath,
        renderer,
        delayLoadScene=False,
    ):
        self.deadlinePlugin = deadlinePlugin

        self.Version = version
        self.Build = build
        self.SceneFile = sceneFile
        self.ProjectPath = projectPath
        self.StartupScriptPath = startupScriptPath
        self.Renderer = renderer
        self.DelayLoadScene = delayLoadScene

        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument

        self.initialFrame = None

    def Cleanup(self):
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback

        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback

    def InitializeProcess(self):
        self.ProcessPriority = ProcessPriorityClass.BelowNormal
        self.UseProcessTree = True
        self.PopupHandling = True
        self.StdoutHandling = True

        # FumeFX initial values to support Task Render Status
        self.FumeFXStartFrame = 0
        self.FumeFXEndFrame = 0
        self.FumeFXCurrFrame = 0
        self.FumeFXMemUsed = "0Mb"
        self.FumeFXFrameTime = "00:00.00"
        self.FumeFXEstTime = "00:00:00"

        # FumeFX STDout Handlers (requires min. FumeFX v3.5.3)
        self.AddStdoutHandlerCallback(
            ".*FumeFX: Starting simulation \(([-]?[0-9]+) - ([-]?[0-9]+)\).*"
        ).HandleCallback += (
            self.HandleFumeFXProgress
        )  # 0: STDOUT: "FumeFX: Starting simulation (-20 - 40)."
        self.AddStdoutHandlerCallback(
            ".*FumeFX: Frame: ([-]?[0-9]+)"
        ).HandleCallback += (
            self.HandleFumeFXProgress
        )  # 0: STDOUT: "FumeFX: Frame: -15"
        self.AddStdoutHandlerCallback(
            ".*FumeFX: Memory used: ([0-9]+[a-zA-Z]*)"
        ).HandleCallback += (
            self.HandleFumeFXProgress
        )  # 0: STDOUT: "FumeFX: Memory used: 86Mb"
        self.AddStdoutHandlerCallback(
            ".*FumeFX: Frame Time: ([0-9]+:[0-9]+\.[0-9]+)"
        ).HandleCallback += (
            self.HandleFumeFXProgress
        )  # 0: STDOUT: "FumeFX: Frame Time: 00:01.69"
        self.AddStdoutHandlerCallback(
            ".*FumeFX: Estimated Time: ([0-9]+:[0-9]+:[0-9]+)"
        ).HandleCallback += (
            self.HandleFumeFXProgress
        )  # 0: STDOUT: "FumeFX: Estimated Time: 00:00:18"

        # This indicates that maya batch is ready for input from us.
        self.AddStdoutHandlerCallback(
            r"READY FOR INPUT"
        ).HandleCallback += self.HandleReadyForInput

        # Catch licensing errors.
        self.AddStdoutHandlerCallback(
            "FLEXlm error: .*"
        ).HandleCallback += self.HandleFatalError
        self.AddStdoutHandlerCallback(
            "Maya: License was not obtained"
        ).HandleCallback += self.HandleFatalError

        # Catch Startup Script Errors
        self.AddStdoutHandlerCallback(
            "An error occurred during the Startup Script."
        ).HandleCallback += self.HandleFatalError

        # Catch Yeti Licensing Errors
        self.AddStdoutHandlerCallback(
            ".*ERROR pgLicenseCheck.*"
        ).HandleCallback += self.HandleErrorMessage

        # Progress updates, works when rendering multiple frames per chunk.
        self.AddStdoutHandlerCallback(
            "Finished Rendering.*\\.([0-9]+)\\.[^\\.]+"
        ).HandleCallback += self.HandleChunkedProgress1
        self.AddStdoutHandlerCallback(
            ".*Finished Rendering.*"
        ).HandleCallback += self.HandleChunkedProgress2

        # CUDA errors piped as stdout.
        self.AddStdoutHandlerCallback(
            ".*CUDA_ERROR_UNKNOWN.*"
        ).HandleCallback += self.HandleFatalError
        self.AddStdoutHandlerCallback(
            ".*Failed to init the CUDA driver API.*"
        ).HandleCallback += self.HandleFatalError
        self.AddStdoutHandlerCallback(
            ".*The system does not support the required CUDA compute capabilities.*"
        ).HandleCallback += self.HandleFatalError

        # Some status messages.
        self.AddStdoutHandlerCallback(
            "Constructing shading groups|Rendering current frame"
        ).HandleCallback += self.HandleStatusMessage

        # Handle Redshift GPU affinity error
        if self.Renderer == "redshift":
            self.AddStdoutHandlerCallback(
                r"redshiftSelectCudaDevices\.mel line \d+: Invalid device id: (\d+)$"
            ).HandleCallback += self.HandleRedshiftGPUAffinityError

        # Error message handling.
        self.AddStdoutHandlerCallback(
            ".*Error: .*|.*Warning: .*"
        ).HandleCallback += self.HandleErrorMessage

        # Mental Ray progress handling.
        self.AddStdoutHandlerCallback(
            "progr: +([0-9]+\\.[0-9]+)% +rendered"
        ).HandleCallback += self.HandleMentalRayProgress
        self.AddStdoutHandlerCallback(
            "progr: +([0-9]+\\.[0-9]+)% +computing final gather points"
        ).HandleCallback += self.HandleMentalRayGathering
        self.AddStdoutHandlerCallback(
            "progr: writing image file .* \\(frame ([0-9]+)\\)"
        ).HandleCallback += self.HandleMentalRayWritingFrame
        self.AddStdoutHandlerCallback(
            "progr: +rendering finished"
        ).HandleCallback += self.HandleMentalRayComplete

        self.AddStdoutHandlerCallback(
            "\\[PROGRESS\\] Completed frame*"
        ).HandleCallback += self.HandleProgressMessage2
        self.AddStdoutHandlerCallback(
            ".*\\[PROGRESS\\] TURTLE rendering frame 100\\.00.*"
        ).HandleCallback += self.HandleProgressMessage2
        self.AddStdoutHandlerCallback(
            ".*Render complete.*"
        ).HandleCallback += self.HandleProgressMessage2

        self.AddStdoutHandlerCallback(
            "\\[PROGRESS\\] Percentage of rendering done: (.*)"
        ).HandleCallback += self.HandleProgressMessage3
        self.AddStdoutHandlerCallback(
            ".*\\[PROGRESS\\] TURTLE rendering frame ([0-9]+\\.[0-9]+).*"
        ).HandleCallback += self.HandleProgressMessage3
        self.AddStdoutHandlerCallback(
            ".*RIMG : +([0-9]+)%"
        ).HandleCallback += self.HandleProgressMessage3

        if self.Renderer == "vray" or self.Renderer == "vrayexport":
            self.CountRenderableCameras = self.deadlinePlugin.GetIntegerPluginInfoEntryWithDefault(
                "CountRenderableCameras", 1
            )

            # if each renderable camera is submitted as a separate job, then the number of renderable cameras is 1 per job and 'Camera' is nonempty
            if (
                self.deadlinePlugin.GetPluginInfoEntryWithDefault("Camera", "")
                != ""
                or self.CountRenderableCameras < 1
            ):
                self.CountRenderableCameras = 1

            self.vrayRenderingImage = False
            self.AddStdoutHandlerCallback(
                "V-Ray error: .*"
            ).HandleCallback += self.HandleFatalError
            self.AddStdoutHandlerCallback(
                "V-Ray: Building light cache*"
            ).HandleCallback += self.HandleVrayMessage
            self.AddStdoutHandlerCallback(
                "V-Ray: Prepass ([0-9]+) of ([0-9]+)*"
            ).HandleCallback += self.HandleVrayMessage
            self.AddStdoutHandlerCallback(
                "V-Ray: Rendering image*"
            ).HandleCallback += self.HandleVrayMessage
            self.AddStdoutHandlerCallback(
                "V-Ray: +([0-9]+)%"
            ).HandleCallback += self.HandleVrayProgress
            self.AddStdoutHandlerCallback(
                "V-Ray: +([0-9]+) %"
            ).HandleCallback += self.HandleVrayProgress
            self.AddStdoutHandlerCallback(
                "([0-9]+) % completed"
            ).HandleCallback += self.HandleVrayProgress
            self.AddStdoutHandlerCallback(
                "V-Ray: Total frame time"
            ).HandleCallback += self.HandleVrayFrameComplete

            self.AddStdoutHandlerCallback(
                "V-Ray: Updating frame at time ([0-9]+)"
            ).HandleCallback += self.HandleVrayExportProgress
            self.AddStdoutHandlerCallback(
                "V-Ray: Render complete"
            ).HandleCallback += self.HandleVrayExportComplete
            self.AddStdoutHandlerCallback(
                ".*V-Ray warning.* The file path for .* cannot be created.*"
            ).HandleCallback += self.HandleFatalError

        if (
            self.Renderer == "renderman"
            or self.Renderer == "rendermanris"
            or self.Renderer == "rendermanexport"
        ):
            self.AddStdoutHandlerCallback(
                "rfm Notice: Rendering .* at ([0-9]+)"
            ).HandleCallback += self.HandleRendermanProgress

        # Catch 3Delight Errors
        if self.Renderer == "3delight":
            self.AddStdoutHandlerCallback(
                ".*3DL ERROR .*"
            ).HandleCallback += self.HandleFatalError
            self.AddStdoutHandlerCallback(
                r"\[\d+\.?\d* \d+\.?\d* \d+\.?\d*\]"
            ).HandleCallback += self.HandlePointCloudOutput

        # Catch Arnold Errors
        if self.Renderer == "arnold" or self.Renderer == "arnoldexport":
            self.AddStdoutHandlerCallback(
                r"Plug-in, \"mtoa\", was not found on MAYA_PLUG_IN_PATH"
            ).HandleCallback += self.HandleFatalError
            self.AddStdoutHandlerCallback(
                r"\[mtoa\] Failed batch render"
            ).HandleCallback += self.HandleFatalError
            self.AddStdoutHandlerCallback(
                "render done"
            ).HandleCallback += self.HandleProgressMessage2

        if self.Renderer == "octanerender":
            self.AddStdoutHandlerCallback(
                r"Octane: starting animation of frame"
            ).HandleCallback += self.HandleOctaneStartFrame
            self.AddStdoutHandlerCallback(
                r"Octane: Refreshed image, ([0-9]+) samples per pixel of ([0-9]+)"
            ).HandleCallback += self.HandleOctaneProgress

        if self.Renderer == "causticvisualizer":
            self.AddStdoutHandlerCallback(
                r"Executing frame ([0-9]+)"
            ).HandleCallback += self.HandleCausticVisualizerCurrentFrame
            self.AddStdoutHandlerCallback(
                r"Rendering ([0-9]+) passes"
            ).HandleCallback += self.HandleCausticVisualizerTotalPasses
            self.AddStdoutHandlerCallback(
                r"Rendered to pass ([0-9]+)"
            ).HandleCallback += self.HandleCausticVisualizerCurrentPass

        if self.Renderer == "ifmirayphotoreal":
            self.AddStdoutHandlerCallback(
                r"Writing.*\\.\\.\\."
            ).HandleCallback += self.HandleIRayEndFrame
            self.AddStdoutHandlerCallback(
                r".*Received update to ([0-9]+) iterations.*"
            ).HandleCallback += self.HandleIRayProgressMessage

        if self.Renderer == "redshift":
            self.AddStdoutHandlerCallback(
                r"Frame rendering aborted."
            ).HandleCallback += self.HandleFatalError
            self.AddStdoutHandlerCallback(
                r"Rendering was internally aborted"
            ).HandleCallback += self.HandleFatalError
            self.AddStdoutHandlerCallback(
                r'Cannot find procedure "rsPreference"'
            ).HandleCallback += self.HandleFatalError
            self.AddStdoutHandlerCallback(
                "Rendering frame \\d+ \\((\\d+)/(\\d+)\\)"
            ).HandleCallback += self.HandleRedshiftNewFrameProgress
            self.AddStdoutHandlerCallback(
                "Block (\\d+)/(\\d+) .+ rendered"
            ).HandleCallback += self.HandleRedshiftBlockRendered

        self.AddStdoutHandlerCallback(
            "\\[PROGRESS\\] ([0-9]+) percent"
        ).HandleCallback += self.HandleProgressMessage1
        self.AddStdoutHandlerCallback(
            "([0-9]+)%"
        ).HandleCallback += self.HandleProgressMessage1

        # Set the popup ignorers.
        self.AddPopupIgnorer(".*entry point.*")
        self.AddPopupIgnorer(".*Entry Point.*")

        # Ignore Vray popup
        self.AddPopupIgnorer(".*Render history settings.*")
        self.AddPopupIgnorer(".*Render history note.*")

        # Handle QuickTime popup dialog
        # "QuickTime does not support the current Display Setting.  Please change it and restart this application."
        self.AddPopupHandler("Unsupported Display", "OK")
        self.AddPopupHandler("Nicht.*", "OK")

    ## Called by Deadline to get the render executable.
    def RenderExecutable(self):
        versionString = str(self.Version).replace(".", "_")

        mayaExecutable = ""
        mayaExeList = self.deadlinePlugin.GetConfigEntry("PypeWrapper")

        if SystemUtils.IsRunningOnWindows():
            if self.Build == "32bit":
                self.deadlinePlugin.LogInfo("Enforcing 32 bit build of Maya")
                mayaExecutable = FileUtils.SearchFileListFor32Bit(mayaExeList)
                if mayaExecutable == "":
                    self.deadlinePlugin.LogWarning(
                        "32 bit Maya "
                        + versionString
                        + ' render executable was not found in the semicolon separated list "'
                        + mayaExeList
                        + '". Checking for any executable that exists instead.'
                    )

            elif self.Build == "64bit":
                self.deadlinePlugin.LogInfo("Enforcing 64 bit build of Maya")
                mayaExecutable = FileUtils.SearchFileListFor64Bit(mayaExeList)
                if mayaExecutable == "":
                    self.deadlinePlugin.LogWarning(
                        "64 bit Maya "
                        + versionString
                        + ' render executable was not found in the semicolon separated list "'
                        + mayaExeList
                        + '". Checking for any executable that exists instead.'
                    )

        if mayaExecutable == "":
            self.deadlinePlugin.LogInfo("Not enforcing a build of Maya")
            mayaExecutable = FileUtils.SearchFileList(mayaExeList)
            if mayaExecutable == "":
                self.deadlinePlugin.FailRender(
                    "Maya "
                    + versionString
                    + ' render executable was not found in the semicolon separated list "'
                    + mayaExeList
                    + '". The path to the render executable can be configured from the Plugin Configuration in the Deadline Monitor.'
                )

        return mayaExecutable

    ## Called by Deadline to get the render arguments.
    def RenderArgument(self):
        renderArguments = "-prompt"

        # If self.DelayLoadScene is True, that means we'll be loading the scene from the melscript code, instead of via initial command line.
        if not self.DelayLoadScene:
            renderArguments += ' -file "' + self.SceneFile + '"'
            renderArguments += StringUtils.BlankIfEitherIsBlank(
                ' -script "',
                StringUtils.BlankIfEitherIsBlank(self.StartupScriptPath, '"'),
            )

        renderArguments += StringUtils.BlankIfEitherIsBlank(
            ' -proj "', StringUtils.BlankIfEitherIsBlank(self.ProjectPath, '"')
        )
        return renderArguments

    def HandleReadyForInput(self):
        self.ReadyForInput = True

    def IsReadyForInput(self):
        return self.ReadyForInput

    def ResetReadyForInput(self):
        self.ReadyForInput = False

    def ReadyForInputCommand(self):
        return 'print( "READY FOR INPUT\\n" );'

    def ResetFrameCount(self):
        self.FinishedFrameCount = 0
        self.PreviousFinishedFrame = ""
        self.SkipNextFrame = False
        self.initialFrame = None

    def HandleFatalError(self):
        self.deadlinePlugin.LogWarning(self.GetRegexMatch(0))
        self.deadlinePlugin.WriteScriptToLog(isError=True)
        self.SuppressThisLine()
        self.deadlinePlugin.FailRender(self.GetRegexMatch(0))

    def HandlePointCloudOutput(self):
        self.SuppressThisLine()

    def HandleChunkedProgress1(self):
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()
        if endFrame - startFrame + 1 != 0:
            self.deadlinePlugin.SetProgress(
                100
                * (int(self.GetRegexMatch(1)) - startFrame + 1)
                / (endFrame - startFrame + 1)
            )

    def HandleChunkedProgress2(self):
        self.FinishedFrameCount += 1
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()
        if endFrame - startFrame + 1 != 0:
            self.deadlinePlugin.SetProgress(
                100 * (self.FinishedFrameCount / (endFrame - startFrame + 1))
            )

    def HandleRedshiftNewFrameProgress(self):
        self.FinishedFrameCount = float(self.GetRegexMatch(1)) - 1
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()
        if endFrame - startFrame + 1 != 0:
            progress = 100 * (
                self.FinishedFrameCount / (endFrame - startFrame + 1)
            )
            self.deadlinePlugin.SetProgress(progress)

    def HandleRedshiftBlockRendered(self):
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()

        completedBlockNumber = float(self.GetRegexMatch(1))
        totalBlockCount = float(self.GetRegexMatch(2))
        finishedFrames = completedBlockNumber / totalBlockCount
        finishedFrames = finishedFrames + self.FinishedFrameCount

        if endFrame - startFrame + 1 != 0:
            progress = 100 * (finishedFrames / (endFrame - startFrame + 1))
            self.deadlinePlugin.SetProgress(progress)

    def HandleRedshiftGPUAffinityError(self):
        """
        Redshift emits a warning message on standard output when the MELscript procedure redshiftSelectCudaDevices() is
        called with a GPU ordinal that is "invalid". Redshift then falls back to using all available GPUs.

        When a user configures GPU affinity, they likely don't want to use Redshift's fallback behavior - especially
        since Redshift would then try to allocate the majority of the remaining GPUs VRAM. We catch this warning
        message and fail the render with a more user-friendly message
        """
        gpu_device_id = self.GetRegexMatch(1)
        self.deadlinePlugin.FailRender(
            "Redshift has detected that the selected GPU '%s' is invalid. Failing the task to prevent Redshift from using all GPUs."
            % gpu_device_id
        )

    def HandleStatusMessage(self):
        self.deadlinePlugin.SetStatusMessage(self.GetRegexMatch(0))

    def HandleErrorMessage(self):
        errorMessage = self.GetRegexMatch(0)

        # This message is always fatal, because it means the scene could not be loaded.
        if errorMessage.find("Cannot load scene") != -1:
            self.deadlinePlugin.LogWarning(self.GetRegexMatch(0))
            self.deadlinePlugin.WriteScriptToLog(isError=True)
            self.SuppressThisLine()
            self.deadlinePlugin.FailRender(errorMessage)

        if not self.deadlinePlugin.GetBooleanPluginInfoEntryWithDefault(
            "StrictErrorChecking", True
        ):
            self.deadlinePlugin.LogWarning(
                "Strict error checking off, ignoring the following error or warning."
            )
        else:

            if self.deadlinePlugin.is_known_fatal_strict_error(errorMessage):
                self.deadlinePlugin.LogWarning(self.GetRegexMatch(0))
                self.deadlinePlugin.WriteScriptToLog(isError=True)
                self.SuppressThisLine()
                self.deadlinePlugin.FailRender(
                    "Strict error checking on, caught the following error or warning.\n"
                    + errorMessage
                    + "\nIf this error message is unavoidable but not fatal, please email support@thinkboxsoftware.com with the error message, and disable the Maya job setting Strict Error Checking."
                )
            else:
                # Check if we're suppressing warnings.
                if (
                    self.deadlinePlugin.GetBooleanConfigEntryWithDefault(
                        "SuppressWarnings", False
                    )
                    and errorMessage.find("Warning:") != -1
                ):
                    self.SuppressThisLine()
                else:
                    # Only print this out if we're not suppressing warnings.
                    self.deadlinePlugin.LogWarning(
                        "Strict error checking on, ignoring the following unrecognized error or warning. If it is fatal, please email support@thinkboxsoftware.com with the error message."
                    )

    def HandleProgressMessage1(self):
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()
        if endFrame - startFrame + 1 != 0:
            self.deadlinePlugin.SetProgress(
                (float(self.GetRegexMatch(1)) + self.FinishedFrameCount * 100)
                / (endFrame - startFrame + 1)
            )
            # self.SuppressThisLine()

    def HandleProgressMessage2(self):
        if self.Renderer != "vray" and self.Renderer != "vrayexport":
            self.FinishedFrameCount += 1

            startFrame = self.deadlinePlugin.GetStartFrame()
            endFrame = self.deadlinePlugin.GetEndFrame()
            if endFrame - startFrame + 1 != 0:
                self.deadlinePlugin.SetProgress(
                    (self.FinishedFrameCount * 100)
                    / (endFrame - startFrame + 1)
                )

    def HandleProgressMessage3(self):
        self.deadlinePlugin.SetProgress(float(self.GetRegexMatch(1)))
        # self.SuppressThisLine()

    def HandleVrayMessage(self):
        progressStatus = None
        errorMessage = self.GetRegexMatch(0)
        if errorMessage.find("V-Ray: Building light cache") != -1:
            progressStatus = "Building light cache."
        elif errorMessage.find("V-Ray: Building global photon map") != -1:
            progressStatus = self.GetRegexMatch(0)
        elif errorMessage.find("V-Ray: Prepass") != -1:
            progressStatus = self.GetRegexMatch(0)
        elif errorMessage.find("V-Ray: Rendering image") != -1:
            progressStatus = self.GetRegexMatch(0)
            self.vrayRenderingImage = True

        if progressStatus is not None:
            self.deadlinePlugin.SetStatusMessage(progressStatus)

    def HandleVrayProgress(self):
        if self.vrayRenderingImage == True:
            startFrame = self.deadlinePlugin.GetStartFrame()
            endFrame = self.deadlinePlugin.GetEndFrame()
            if endFrame - startFrame + 1 > 0:
                self.deadlinePlugin.SetProgress(
                    (
                        float(self.GetRegexMatch(1))
                        + float(self.FinishedFrameCount) * 100
                    )
                    / (
                        (endFrame - startFrame + 1)
                        * self.CountRenderableCameras
                    )
                )

    def HandleVrayFrameComplete(self):
        if self.vrayRenderingImage == True:
            self.FinishedFrameCount += 1
            self.vrayRenderingImage = False

    def HandleVrayExportProgress(self):
        if self.Renderer == "vrayexport":
            self.FinishedFrameCount += 1

            startFrame = self.deadlinePlugin.GetStartFrame()
            endFrame = self.deadlinePlugin.GetEndFrame()
            if endFrame - startFrame + 1 != 0:
                self.deadlinePlugin.SetProgress(
                    ((self.FinishedFrameCount - 1) * 100)
                    / (endFrame - startFrame + 1)
                )

    def HandleVrayExportComplete(self):
        if self.Renderer == "vrayexport":
            self.deadlinePlugin.SetProgress(100)

    def HandleIRayEndFrame(self):
        self.FinishedFrameCount += 1

    def HandleIRayProgressMessage(self):
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()
        maxSamples = self.deadlinePlugin.GetIntegerPluginInfoEntryWithDefault(
            "IRayMaxSamples", 1024
        )

        if endFrame - startFrame + 1 != 0:
            framePercentage = float(self.GetRegexMatch(1)) / float(maxSamples)

            self.deadlinePlugin.SetProgress(
                ((framePercentage + (self.FinishedFrameCount)) * 100)
                / (endFrame - startFrame + 1)
            )

    def HandleRendermanProgress(self):
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()
        totalFrames = endFrame - startFrame + 1

        if totalFrames > 1:
            currentFrame = float(self.GetRegexMatch(1))
            if self.initialFrame is None:
                self.initialFrame = currentFrame

            normalizedFrame = currentFrame
            if self.initialFrame > 1:
                normalizedFrame = currentFrame - startFrame + 1

            self.deadlinePlugin.SetProgress(
                normalizedFrame * 100.0 / totalFrames
            )

        self.deadlinePlugin.SetStatusMessage(self.GetRegexMatch(0))

    def HandleOctaneStartFrame(self):
        self.FinishedFrameCount += 1

    def HandleOctaneProgress(self):
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()
        if endFrame - startFrame + 1 != 0:
            currSamples = float(self.GetRegexMatch(1))
            maxSampes = float(self.GetRegexMatch(2))
            self.deadlinePlugin.SetProgress(
                (
                    ((currSamples * 100.0) / maxSampes)
                    + (self.FinishedFrameCount - 1) * 100
                )
                / (endFrame - startFrame + 1)
            )

        self.deadlinePlugin.SetStatusMessage(self.GetRegexMatch(0))

    def HandleCausticVisualizerCurrentFrame(self):
        self.CausticCurrentFrame = int(self.GetRegexMatch(1))

    def HandleCausticVisualizerTotalPasses(self):
        self.CausticTotalPasses = int(self.GetRegexMatch(1))

    def HandleCausticVisualizerCurrentPass(self):
        if self.CausticTotalPasses > 0:
            totalFrameCount = (
                self.deadlinePlugin.GetEndFrame()
                - self.deadlinePlugin.GetStartFrame()
                + 1
            )
            if totalFrameCount != 0:
                causticCurrentPass = int(self.GetRegexMatch(1))
                currentFrameCount = (
                    self.CausticCurrentFrame
                    - self.deadlinePlugin.GetStartFrame()
                )
                self.deadlinePlugin.SetProgress(
                    (
                        ((causticCurrentPass * 100) / self.CausticTotalPasses)
                        + (currentFrameCount * 100)
                    )
                    / totalFrameCount
                )

    ########################################################################
    ## Mental Ray progress handling.
    ########################################################################
    def HandleMentalRayProgress(self):
        startFrame = self.deadlinePlugin.GetStartFrame()
        endFrame = self.deadlinePlugin.GetEndFrame()
        if endFrame - startFrame + 1 != 0:
            self.deadlinePlugin.SetProgress(
                (float(self.GetRegexMatch(1)) + self.FinishedFrameCount * 100)
                / (endFrame - startFrame + 1)
            )
            self.deadlinePlugin.SetStatusMessage(self.GetRegexMatch(0))
            # self.SuppressThisLine()

    def HandleMentalRayComplete(self):
        if self.SkipNextFrame:
            self.SkipNextFrame = False
        else:
            self.FinishedFrameCount += 1
            startFrame = self.deadlinePlugin.GetStartFrame()
            endFrame = self.deadlinePlugin.GetEndFrame()
            if endFrame - startFrame + 1 != 0:
                self.deadlinePlugin.SetProgress(
                    (self.FinishedFrameCount * 100)
                    / (endFrame - startFrame + 1)
                )

    def HandleMentalRayGathering(self):
        self.deadlinePlugin.SetStatusMessage(self.GetRegexMatch(0))
        # self.SuppressThisLine()

    def HandleMentalRayWritingFrame(self):
        currFinishedFrame = self.GetRegexMatch(1)
        if self.PreviousFinishedFrame == currFinishedFrame:
            self.SkipNextFrame = True
        else:
            self.PreviousFinishedFrame = currFinishedFrame

    def HandleFumeFXProgress(self):
        if re.match(r"FumeFX: Starting simulation ", self.GetRegexMatch(0)):
            self.FumeFXStartFrame = self.GetRegexMatch(1)
            self.FumeFXEndFrame = self.GetRegexMatch(2)
        elif re.match(r"FumeFX: Frame: ", self.GetRegexMatch(0)):
            self.FumeFXCurrFrame = self.GetRegexMatch(1)
            denominator = (
                float(self.FumeFXEndFrame) - float(self.FumeFXStartFrame) + 1.0
            )
            progress = (
                (
                    float(self.FumeFXCurrFrame)
                    - float(self.FumeFXStartFrame)
                    + 1.0
                )
                / denominator
            ) * 100.0
            self.deadlinePlugin.SetProgress(progress)
            msg = (
                "FumeFX: ("
                + str(self.FumeFXCurrFrame)
                + " to "
                + str(self.FumeFXEndFrame)
                + ") - Mem: "
                + str(self.FumeFXMemUsed)
                + " - LastTime: "
                + str(self.FumeFXFrameTime)
                + " - ETA: "
                + str(self.FumeFXEstTime)
            )
            self.deadlinePlugin.SetStatusMessage(msg)
        elif re.match(r"FumeFX: Memory used:", self.GetRegexMatch(0)):
            self.FumeFXMemUsed = self.GetRegexMatch(1)
        elif re.match(r"FumeFX: Frame Time:", self.GetRegexMatch(0)):
            self.FumeFXFrameTime = self.GetRegexMatch(1)
        elif re.match(r"FumeFX: Estimated Time:", self.GetRegexMatch(0)):
            self.FumeFXEstTime = self.GetRegexMatch(1)
        else:
            pass
