from System.IO import *
from System.Text.RegularExpressions import *

from Deadline.Plugins import PluginType, DeadlinePlugin
from Deadline.Scripting import (
    StringUtils,
    FileUtils,
    RepositoryUtils,
    SystemUtils
)

import re


def GetDeadlinePlugin():
    return PythonPlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()


class PythonPlugin(DeadlinePlugin):

    def __init__(self):
        """Hook up the callbacks in the constructor."""

        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument
        self.setupEnvironment()

    def Cleanup(self):
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback

        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback

    def InitializeProcess(self):
        self.PluginType = PluginType.Simple
        self.StdoutHandling = True

        self.SingleFramesOnly = self.GetBooleanPluginInfoEntryWithDefault(
            "SingleFramesOnly", False
        )
        
        self.LogInfo("Single Frames Only: %s" % self.SingleFramesOnly)

        self.AddStdoutHandlerCallback(
            ".*Progress: (\d+)%.*").HandleCallback += self.HandleProgress
        self.AddStdoutHandlerCallback(
            ".*ALF_PROGRESS ([0-9]+)%.*").HandleCallback += self.HandleStdoutFrameProgress  # noqa: E501

    def setupEnvironment(self):
        import os
        
        # TODO: Remove this hardcoded environment logic
        SELF_DIR = r'R:\\HOUDINI_VRAY'

        if 'PIPELINE_DIR' not in os.environ:
            os.environ[
                'PIPELINE_DIR'] = r'R:\\PIPELINE2.0\\pub\\shared\\python'

        # Houdini version
        HOUDINI_MAJOR_VERSION = '19.5'
        HOUDINI_MINOR_VERSION = '640'

        # Houdini installation directory
        HFS = r'C:/Program Files/Side Effects Software/Houdini {}.{}/'.format(
            HOUDINI_MAJOR_VERSION, HOUDINI_MINOR_VERSION)

        # V-Ray installation root
        INSTALL_ROOT = SELF_DIR

        # V-Ray version and build
        VRAY_AUTH_CLIENT_FILE_PATH = INSTALL_ROOT
        VRAY_VERSION = '6'
        VRAY_BUILD = 'vray_adv_61009_houdini19.5.640_eeebff7_22509'
        # VRAY_BUILD = 'vray_adv_61009_houdini19.5.640_6df9f0b_22504'

        # Installation root for V-Ray
        INSTALL_ROOT = os.path.join(INSTALL_ROOT, '19.5', VRAY_VERSION,
                                    VRAY_BUILD)

        # Houdini package directory
        HOUDINI_PACKAGE_DIR = os.path.join(SELF_DIR, 'packages')

        # Set environment variables
        os.environ['HFS'] = HFS
        os.environ['HOUDINI_PACKAGE_VERBOSE'] = '1'
        os.environ['INSTALL_ROOT'] = INSTALL_ROOT
        os.environ['VRAY_AUTH_CLIENT_FILE_PATH'] = VRAY_AUTH_CLIENT_FILE_PATH
        os.environ['VRAY_VERSION'] = VRAY_VERSION
        os.environ['VRAY_BUILD'] = VRAY_BUILD
        os.environ['HOUDINI_PACKAGE_DIR'] = HOUDINI_PACKAGE_DIR

    def RenderExecutable(self):
        # version = self.GetPluginInfoEntry("Version")

        exe_list = self.GetConfigEntry("Python_Executable")
        exe = FileUtils.SearchFileList(exe_list)
        if exe == "":
            self.FailRender(
                "Python executable was not found in the semicolon separated "
                "list \"{}\". The path to the render executable can be "
                "configured from the Plugin Configuration in the Deadline "
                "Monitor.".format(exe_list)
            )
        return exe

    def RenderArgument(self):
        scriptFile = self.GetPluginInfoEntryWithDefault("ScriptFile",
                                                        self.GetDataFilename())
        scriptFile = RepositoryUtils.CheckPathMapping(scriptFile)

        arguments = self.GetPluginInfoEntryWithDefault("Arguments", "")
        arguments = RepositoryUtils.CheckPathMapping(arguments)

        arguments = re.sub(r"<(?i)STARTFRAME>", str(self.GetStartFrame()),
                           arguments)
        arguments = re.sub(r"<(?i)ENDFRAME>", str(self.GetEndFrame()),
                           arguments)
        arguments = re.sub(r"<(?i)QUOTE>", "\"", arguments)

        arguments = self.ReplacePaddedFrame(arguments,
                                            "<(?i)STARTFRAME%([0-9]+)>",
                                            self.GetStartFrame())
        arguments = self.ReplacePaddedFrame(arguments,
                                            "<(?i)ENDFRAME%([0-9]+)>",
                                            self.GetEndFrame())

        count = 0
        for filename in self.GetAuxiliaryFilenames():
            localAuxFile = Path.Combine(self.GetJobsDataDirectory(), filename)
            arguments = re.sub(r"<(?i)AUXFILE" + str(count) + r">",
                               localAuxFile.replace("\\", "/"), arguments)
            count += 1

        if SystemUtils.IsRunningOnWindows():
            scriptFile = scriptFile.replace("/", "\\")
        else:
            scriptFile = scriptFile.replace("\\", "/")

        return "-u \"" + scriptFile + "\" " + arguments

    def ReplacePaddedFrame(self, arguments, pattern, frame):
        regex = re.compile(pattern)
        while True:
            match = regex.match(arguments)
            if match.Success:
                padding_size = int(match.group(1))
                if padding_size > 0:
                    padding = StringUtils.ToZeroPaddedString(frame,
                                                             padding_size,
                                                             False)
                else:
                    padding = str(frame)
                arguments = arguments.replace(match.group(0),
                                              padding)
            else:
                break

        return arguments

    def HandleProgress(self):
        progress = float(self.GetRegexMatch(1))
        self.SetProgress(progress)

    def HandleStdoutFrameProgress(self):
        overallProgress = float(self.GetRegexMatch(1))
        self.SetProgress(overallProgress)
        self.SetStatusMessage("Progress: {}%".format(overallProgress))
