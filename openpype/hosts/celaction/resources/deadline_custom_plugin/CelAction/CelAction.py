from System.Text.RegularExpressions import *

from Deadline.Plugins import *
from Deadline.Scripting import *

import _winreg

######################################################################
# This is the function that Deadline calls to get an instance of the
# main DeadlinePlugin class.
######################################################################


def GetDeadlinePlugin():
    return CelActionPlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()

######################################################################
# This is the main DeadlinePlugin class for the CelAction plugin.
######################################################################


class CelActionPlugin(DeadlinePlugin):

    def __init__(self):
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument
        self.StartupDirectoryCallback += self.StartupDirectory

    def Cleanup(self):
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback

        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback
        del self.StartupDirectoryCallback

    def GetCelActionRegistryKey(self):
        # Modify registry for frame separation
        path = r'Software\CelAction\CelAction2D\User Settings'
        _winreg.CreateKey(_winreg.HKEY_CURRENT_USER, path)
        regKey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, path, 0,
                                 _winreg.KEY_ALL_ACCESS)
        return regKey

    def GetSeparatorValue(self, regKey):
        useSeparator, _ = _winreg.QueryValueEx(
            regKey, 'RenderNameUseSeparator')
        separator, _ = _winreg.QueryValueEx(regKey, 'RenderNameSeparator')

        return useSeparator, separator

    def SetSeparatorValue(self, regKey, useSeparator, separator):
        _winreg.SetValueEx(regKey, 'RenderNameUseSeparator',
                           0, _winreg.REG_DWORD, useSeparator)
        _winreg.SetValueEx(regKey, 'RenderNameSeparator',
                           0, _winreg.REG_SZ, separator)

    def InitializeProcess(self):
        # Set the plugin specific settings.
        self.SingleFramesOnly = False

        # Set the process specific settings.
        self.StdoutHandling = True
        self.PopupHandling = True

        # Ignore 'celaction' Pop-up dialog
        self.AddPopupIgnorer(".*Rendering.*")

        # Ignore 'celaction' Pop-up dialog
        self.AddPopupIgnorer(".*Wait.*")

        # Ignore 'celaction' Pop-up dialog
        self.AddPopupIgnorer(".*Timeline Scrub.*")

        celActionRegKey = self.GetCelActionRegistryKey()

        self.SetSeparatorValue(celActionRegKey, 1, self.GetConfigEntryWithDefault(
            "RenderNameSeparator", ".").strip())

    def RenderExecutable(self):
        return RepositoryUtils.CheckPathMapping(self.GetConfigEntry("Executable").strip())

    def RenderArgument(self):
        arguments = RepositoryUtils.CheckPathMapping(
            self.GetPluginInfoEntry("Arguments").strip())
        arguments = arguments.replace(
            "<STARTFRAME>", str(self.GetStartFrame()))
        arguments = arguments.replace("<ENDFRAME>", str(self.GetEndFrame()))
        arguments = self.ReplacePaddedFrame(
            arguments, "<STARTFRAME%([0-9]+)>", self.GetStartFrame())
        arguments = self.ReplacePaddedFrame(
            arguments, "<ENDFRAME%([0-9]+)>", self.GetEndFrame())
        arguments = arguments.replace("<QUOTE>", "\"")
        return arguments

    def StartupDirectory(self):
        return self.GetPluginInfoEntryWithDefault("StartupDirectory", "").strip()

    def ReplacePaddedFrame(self, arguments, pattern, frame):
        frameRegex = Regex(pattern)
        while True:
            frameMatch = frameRegex.Match(arguments)
            if frameMatch.Success:
                paddingSize = int(frameMatch.Groups[1].Value)
                if paddingSize > 0:
                    padding = StringUtils.ToZeroPaddedString(
                        frame, paddingSize, False)
                else:
                    padding = str(frame)
                arguments = arguments.replace(
                    frameMatch.Groups[0].Value, padding)
            else:
                break

        return arguments
