#!/usr/bin/env python3

from System.IO import Path
from System.Text.RegularExpressions import Regex

from Deadline.Plugins import PluginType, DeadlinePlugin
from Deadline.Scripting import (
    StringUtils,
    FileUtils,
    DirectoryUtils,
    RepositoryUtils
)

import re
import os
import platform


######################################################################
# This is the function that Deadline calls to get an instance of the
# main DeadlinePlugin class.
######################################################################
def GetDeadlinePlugin():
    return AyonDeadlinePlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()


class AyonDeadlinePlugin(DeadlinePlugin):
    """
        Standalone plugin for publishing from Ayon

        Calls Ayonexecutable 'ayon_console' from first correctly found
        file based on plugin configuration. Uses 'publish' command and passes
        path to metadata json file, which contains all needed information
        for publish process.
    """
    def __init__(self):
        super().__init__()
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
        job = self.GetJob()

        # set required env vars for Ayon
        # cannot be in InitializeProcess as it is too soon
        config = RepositoryUtils.GetPluginConfig("Ayon")
        ayon_server_url = (
                job.GetJobEnvironmentKeyValue("AYON_SERVER_URL") or
                config.GetConfigEntryWithDefault("AyonServerUrl", "")
        )
        ayon_api_key = (
                job.GetJobEnvironmentKeyValue("AYON_API_KEY") or
                config.GetConfigEntryWithDefault("AyonApiKey", "")
        )
        ayon_bundle_name = job.GetJobEnvironmentKeyValue("AYON_BUNDLE_NAME")

        environment = {
            "AYON_SERVER_URL": ayon_server_url,
            "AYON_API_KEY": ayon_api_key,
            "AYON_BUNDLE_NAME": ayon_bundle_name,
        }

        for env, val in environment.items():
            self.SetProcessEnvironmentVariable(env, val)

        exe_list = self.GetConfigEntry("AyonExecutable")
        # clean '\ ' for MacOS pasting
        if platform.system().lower() == "darwin":
            exe_list = exe_list.replace("\\ ", " ")

        expanded_paths = []
        for path in exe_list.split(";"):
            if path.startswith("~"):
                path = os.path.expanduser(path)
            expanded_paths.append(path)
        exe = FileUtils.SearchFileList(";".join(expanded_paths))

        if exe == "":
            self.FailRender(
                "Ayon executable was not found " +
                "in the semicolon separated list " +
                "\"" + ";".join(exe_list) + "\". " +
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
            if not frameMatch.Success:
                break
            paddingSize = int(frameMatch.Groups[1].Value)
            if paddingSize > 0:
                padding = StringUtils.ToZeroPaddedString(
                    frame, paddingSize, False)
            else:
                padding = str(frame)
            arguments = arguments.replace(
                frameMatch.Groups[0].Value, padding)

        return arguments

    def HandleProgress(self):
        progress = float(self.GetRegexMatch(1))
        self.SetProgress(progress)
