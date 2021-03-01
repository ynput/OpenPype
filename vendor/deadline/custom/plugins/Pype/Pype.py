import sys
import subprocess
import platform
import os

from Deadline.Plugins import DeadlinePlugin, PluginType


######################################################################
## This is the function that Deadline calls to get an instance of the
## main DeadlinePlugin class.
######################################################################
def GetDeadlinePlugin():
    return PypeDeadlinePlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()



class PypeDeadlinePlugin(DeadlinePlugin):
    """
        Standalone plugin for publishing from Pype.

        Calls Pype executable 'pype_console' from first correctly found
        file based on plugin configuration. Uses 'publish' command and passes
        path to metadata json file, which contains all needed information
        for publish process.
    """
    def __init__(self):
        self.StartJobCallback += self.StartJob
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderTasksCallback += self.RenderTasks

    def Cleanup(self):
        del self.StartJobCallback
        del self.InitializeProcessCallback
        del self.RenderTasksCallback

    def StartJob(self):
        # adding python search paths
        paths = self.GetConfigEntryWithDefault("PythonSearchPaths", "").strip()
        paths = paths.split(";")

        for path in paths:
            self.LogInfo("Extending sys.path with: " + str(path))
            sys.path.append(path)

        self.LogInfo("PypeDeadlinePlugin start")
        try:
            metadata_file = \
                self.GetProcessEnvironmentVariable("PYPE_METADATA_FILE")
            if not metadata_file:
                raise RuntimeError("Env var PYPE_METADATA_FILE value missing")

            pype_app = self.get_pype_executable_path()

            args = [
                pype_app,
                'publish',
                metadata_file
            ]

            env = {}
            env = dict(os.environ)

            job = self.GetJob()
            for key in job.GetJobEnvironmentKeys():
                env[str(key)] = str(job.GetJobEnvironmentKeyValue(key))

            exit_code = subprocess.call(args, shell=True, env=env)
            if exit_code != 0:
                raise RuntimeError("Publishing failed, check worker's log")

            self.LogInfo("PypeDeadlinePlugin end")
        except Exception:
            import traceback
            self.LogInfo(traceback.format_exc())
            self.LogInfo("PypeDeadlinePlugin failed")
            raise

    ## Called by Deadline to initialize the process.
    def InitializeProcess(self):
        # Set the plugin specific settings.
        self.PluginType = PluginType.Simple

    def RenderTasks(self):
        # do nothing, no render, just publishing, still must be here
        pass

    def get_pype_executable_path(self):
        """
            Returns calculated path based on settings and platform

            Uses 'pype_console' executable
        """
        pype_command = "pype_console"
        if platform.system().lower() == "linux":
            pype_command = "pype_console.sh"
        if platform.system().lower() == "windows":
            pype_command = "pype_console.exe"

        pype_root = self.GetConfigEntryWithDefault("PypeExecutable", "")

        pype_app = os.path.join(pype_root.strip(), pype_command)
        if not os.path.exists(pype_app):
            raise RuntimeError("App '{}' doesn't exist. " +
                               "Fix it in Tools > Configure Events > " +
                               "pype".format(pype_app))

        return pype_app
