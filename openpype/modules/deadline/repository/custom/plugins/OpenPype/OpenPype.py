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

    @staticmethod
    def get_openpype_version_from_path(path, build=True):
        """Get OpenPype version from provided path.
             path (str): Path to scan.
             build (bool, optional): Get only builds, not sources

        Returns:
            str or None: version of OpenPype if found.

        """
        # fix path for application bundle on macos
        if platform.system().lower() == "darwin":
            path = os.path.join(path, "MacOS")

        version_file = os.path.join(path, "openpype", "version.py")
        if not os.path.isfile(version_file):
            return None

        # skip if the version is not build
        exe = os.path.join(path, "openpype_console.exe")
        if platform.system().lower() in ["linux", "darwin"]:
            exe = os.path.join(path, "openpype_console")

        # if only builds are requested
        if build and not os.path.isfile(exe):  # noqa: E501
            print(f"   ! path is not a build: {path}")
            return None

        version = {}
        with open(version_file, "r") as vf:
            exec(vf.read(), version)

        version_match = re.search(r"(\d+\.\d+.\d+).*", version["__version__"])
        return version_match[1]

    def RenderExecutable(self):
        job = self.GetJob()
        openpype_versions = []
        # if the job requires specific OpenPype version,
        # lets go over all available and find compatible build.
        requested_version = job.GetJobEnvironmentKeyValue("OPENPYPE_VERSION")
        if requested_version:
            self.LogInfo((
                "Scanning for compatible requested "
                f"version {requested_version}"))
            dir_list = self.GetConfigEntry("OpenPypeInstallationDirs")

            # clean '\ ' for MacOS pasting
            if platform.system().lower() == "darwin":
                dir_list = dir_list.replace("\\ ", " ")

            for dir_list in dir_list.split(","):
                install_dir = DirectoryUtils.SearchDirectoryList(dir_list)
                if install_dir:
                    sub_dirs = [
                        f.path for f in os.scandir(install_dir)
                        if f.is_dir()
                    ]
                    for subdir in sub_dirs:
                        version = self.get_openpype_version_from_path(subdir)
                        if not version:
                            continue
                        openpype_versions.append((version, subdir))

        exe_list = self.GetConfigEntry("OpenPypeExecutable")
        # clean '\ ' for MacOS pasting
        if platform.system().lower() == "darwin":
            exe_list = exe_list.replace("\\ ", " ")
        exe = FileUtils.SearchFileList(exe_list)
        if openpype_versions:
            # if looking for requested compatible version,
            # add the implicitly specified to the list too.
            version = self.get_openpype_version_from_path(
                os.path.dirname(exe))
            if version:
                openpype_versions.append((version, os.path.dirname(exe)))

        if requested_version:
            # sort detected versions
            if openpype_versions:
                openpype_versions.sort(
                    key=lambda ver: [
                        int(t) if t.isdigit() else t.lower()
                        for t in re.split(r"(\d+)", ver[0])
                    ])
            requested_major, requested_minor, _ = requested_version.split(".")[:3]  # noqa: E501
            compatible_versions = []
            for version in openpype_versions:
                v = version[0].split(".")[:3]
                if v[0] == requested_major and v[1] == requested_minor:
                    compatible_versions.append(version)
            if not compatible_versions:
                self.FailRender(("Cannot find compatible version available "
                                 "for version {} requested by the job. "
                                 "Please add it through plugin configuration "
                                 "in Deadline or install it to configured "
                                 "directory.").format(requested_version))
            # sort compatible versions nad pick the last one
            compatible_versions.sort(
                key=lambda ver: [
                    int(t) if t.isdigit() else t.lower()
                    for t in re.split(r"(\d+)", ver[0])
                ])
            # create list of executables for different platform and let
            # Deadline decide.
            exe_list = [
                os.path.join(
                    compatible_versions[-1][1], "openpype_console.exe"),
                os.path.join(
                    compatible_versions[-1][1], "openpype_console"),
                os.path.join(
                    compatible_versions[-1][1], "MacOS", "openpype_console")
            ]
            exe = FileUtils.SearchFileList(";".join(exe_list))

        if exe == "":
            self.FailRender(
                "OpenPype executable was not found " +
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
