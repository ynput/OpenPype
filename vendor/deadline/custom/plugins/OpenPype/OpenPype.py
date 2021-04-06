from System.IO import Path
from System.Text.RegularExpressions import Regex

from Deadline.Plugins import PluginType, DeadlinePlugin
from Deadline.Scripting import StringUtils, FileUtils, RepositoryUtils

import re


######################################################################
# This is the function that Deadline calls to get an instance of the
# main DeadlinePlugin class.
######################################################################
def GetDeadlinePlugin():
    return OpenPypeDeadlinePlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()


class OpenPypeDeadlinePlugin(DeadlinePlugin):
    """
        Standalone plugin for publishing from OpenPype.

        Calls OpenPype executable 'openpype_console' from first correctly found
        file based on plugin configuration. Uses 'publish' command and passes
        path to metadata json file, which contains all needed information
        for publish process.
    """
    def __init__(self):
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument

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
            "SingleFramesOnly", False)
        self.LogInfo("Single Frames Only: %s" % self.SingleFramesOnly)

        self.AddStdoutHandlerCallback(
            ".*Progress: (\d+)%.*").HandleCallback += self.HandleProgress

    def RenderExecutable(self):
        exeList = self.GetConfigEntry("OpenPypeExecutable")
        exe = FileUtils.SearchFileList(exeList)
        if exe == "":
            self.FailRender(
                "OpenPype executable was not found " +
                "in the semicolon separated list \"" + exeList + "\". " +
                "The path to the render executable can be configured " +
                "from the Plugin Configuration in the Deadline Monitor.")
        return exe

    def RenderArgument(self):
        arguments = str(self.GetPluginInfoEntryWithDefault("Arguments", ""))
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

        return arguments

    def ReplacePaddedFrame(self, arguments, pattern, frame):
        frameRegex = Regex(pattern)
        while True:
            frameMatch = frameRegex.Match(arguments)
            if frameMatch.Success:
                paddingSize = int(frameMatch.Groups[1].Value)
                if paddingSize > 0:
                    padding = StringUtils.ToZeroPaddedString(frame,
                                                             paddingSize,
                                                             False)
                else:
                    padding = str(frame)
                arguments = arguments.replace(frameMatch.Groups[0].Value,
                                              padding)
            else:
                break

        return arguments

    def HandleProgress(self):
        progress = float(self.GetRegexMatch(1))
        self.SetProgress(progress)
