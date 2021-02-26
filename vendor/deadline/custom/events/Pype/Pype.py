import sys
import json
import subprocess
import platform
import os
import tempfile
import time

import Deadline.Events
import Deadline.Scripting


def GetDeadlineEventListener():
    return PypeEventListener()


def CleanupDeadlineEventListener(eventListener):
    eventListener.Cleanup()


class PypeEventListener(Deadline.Events.DeadlineEventListener):
    """ 
        Called on every Deadline plugin event, used for injecting Pype
        environment variables into rendering process.

        Expects that job already contains env vars:
                 AVALON_PROJECT
                 AVALON_ASSET
                 AVALON_TASK
                 AVALON_APP_NAME
        Without these only global environment would be pulled from Pype

        Configure 'Path to Pype executable dir' in Deadlines 
            'Tools > Configure Events > pype '
        Only directory path is needed.

    """      
    ALREADY_INJECTED = False

    def __init__(self):
        self.OnJobSubmittedCallback += self.OnJobSubmitted
        self.OnJobStartedCallback += self.OnJobStarted
        self.OnJobFinishedCallback += self.OnJobFinished
        self.OnJobRequeuedCallback += self.OnJobRequeued
        self.OnJobFailedCallback += self.OnJobFailed
        self.OnJobSuspendedCallback += self.OnJobSuspended
        self.OnJobResumedCallback += self.OnJobResumed
        self.OnJobPendedCallback += self.OnJobPended
        self.OnJobReleasedCallback += self.OnJobReleased
        self.OnJobDeletedCallback += self.OnJobDeleted
        self.OnJobErrorCallback += self.OnJobError
        self.OnJobPurgedCallback += self.OnJobPurged

        self.OnHouseCleaningCallback += self.OnHouseCleaning
        self.OnRepositoryRepairCallback += self.OnRepositoryRepair

        self.OnSlaveStartedCallback += self.OnSlaveStarted
        self.OnSlaveStoppedCallback += self.OnSlaveStopped
        self.OnSlaveIdleCallback += self.OnSlaveIdle
        self.OnSlaveRenderingCallback += self.OnSlaveRendering
        self.OnSlaveStartingJobCallback += self.OnSlaveStartingJob
        self.OnSlaveStalledCallback += self.OnSlaveStalled

        self.OnIdleShutdownCallback += self.OnIdleShutdown
        self.OnMachineStartupCallback += self.OnMachineStartup
        self.OnThermalShutdownCallback += self.OnThermalShutdown
        self.OnMachineRestartCallback += self.OnMachineRestart

        self.ALREADY_INJECTED = False

    def Cleanup(self):
        del self.OnJobSubmittedCallback
        del self.OnJobStartedCallback
        del self.OnJobFinishedCallback
        del self.OnJobRequeuedCallback
        del self.OnJobFailedCallback
        del self.OnJobSuspendedCallback
        del self.OnJobResumedCallback
        del self.OnJobPendedCallback
        del self.OnJobReleasedCallback
        del self.OnJobDeletedCallback
        del self.OnJobErrorCallback
        del self.OnJobPurgedCallback

        del self.OnHouseCleaningCallback
        del self.OnRepositoryRepairCallback

        del self.OnSlaveStartedCallback
        del self.OnSlaveStoppedCallback
        del self.OnSlaveIdleCallback
        del self.OnSlaveRenderingCallback
        del self.OnSlaveStartingJobCallback
        del self.OnSlaveStalledCallback

        del self.OnIdleShutdownCallback
        del self.OnMachineStartupCallback
        del self.OnThermalShutdownCallback
        del self.OnMachineRestartCallback

    def inject_pype_environment(self, job, additonalData=None):

        if self.ALREADY_INJECTED:
            self.LogInfo("Environment injected previously")
            return

        # adding python search paths
        paths = self.GetConfigEntryWithDefault("PythonSearchPaths", "").strip()
        paths = paths.split(";")

        for path in paths:
            self.LogInfo("Extending sys.path with: " + str(path))
            sys.path.append(path)

        self.LogInfo("inject_pype_environment start")     
        try:
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

            # tempfile.TemporaryFile cannot be used because of locking
            export_url = os.path.join(tempfile.gettempdir(),
                                      time.strftime('%Y%m%d%H%M%S'),
                                      'env.json')  # add HHMMSS + delete later
            self.LogInfo("export_url {}".format(export_url))

            add_args = {}
            add_args['project'] = \
                job.GetJobEnvironmentKeyValue('AVALON_PROJECT')
            add_args['asset'] = job.GetJobEnvironmentKeyValue('AVALON_ASSET')
            add_args['task'] = job.GetJobEnvironmentKeyValue('AVALON_TASK')
            add_args['app'] = job.GetJobEnvironmentKeyValue('AVALON_APP_NAME')
            self.LogInfo("args::{}".format(add_args))

            args = [
                pype_app,
                'extractenvironments',
                export_url
            ]
            if all(add_args.values()):
                for key, value in add_args.items():
                    args.append("--{}".format(key))
                    args.append(value)

            self.LogInfo("args::{}".format(args))

            exit_code = subprocess.call(args, shell=True)
            if exit_code != 0:
                raise RuntimeError("Publishing failed")

            with open(export_url) as fp:
                contents = json.load(fp)
                self.LogInfo("contents::{}".format(contents))
                for key, value in contents.items():
                    job.SetJobEnvironmentKeyValue(key, value)

            Deadline.Scripting.RepositoryUtils.SaveJob(job)  # IMPORTANT
            self.ALREADY_INJECTED = True
            
            os.remove(export_url)

            self.LogInfo("inject_pype_environment end")
        except Exception:
            import traceback           
            self.LogInfo(traceback.format_exc())
            self.LogInfo("inject_pype_environment failed")
            Deadline.Scripting.RepositoryUtils.FailJob(job)
            raise

    def updateFtrackStatus(self, job, statusName, createIfMissing=False):
        """Updates version status on ftrack"""
        pass

    def OnJobSubmitted(self, job):
        self.LogInfo("OnJobSubmitted LOGGING")
        # for 1st time submit
        self.inject_pype_environment(job)
        self.updateFtrackStatus(job, "Render Queued")

    def OnJobStarted(self, job):
        self.LogInfo("OnJobStarted")
        # inject_pype_environment shouldnt be here, too late already
        self.updateFtrackStatus(job, "Rendering")

    def OnJobFinished(self, job):
        self.updateFtrackStatus(job, "Artist Review")

    def OnJobRequeued(self, job):
        self.LogInfo("OnJobRequeued LOGGING")
        self.inject_pype_environment(job)

    def OnJobFailed(self, job):
        pass

    def OnJobSuspended(self, job):
        self.LogInfo("OnJobSuspended LOGGING")
        self.updateFtrackStatus(job, "Render Queued")

    def OnJobResumed(self, job):
        self.LogInfo("OnJobResumed LOGGING")
        self.updateFtrackStatus(job, "Rendering")

    def OnJobPended(self, job):
        self.LogInfo("OnJobPended LOGGING")

    def OnJobReleased(self, job):
        pass

    def OnJobDeleted(self, job):
        pass

    def OnJobError(self, job, task, report):
        self.LogInfo("OnJobError LOGGING")
        #data = {"task": task, "report": report}

    def OnJobPurged(self, job):
        pass

    def OnHouseCleaning(self):
        pass

    def OnRepositoryRepair(self, job):
        pass

    def OnSlaveStarted(self, job):
        self.LogInfo("OnSlaveStarted LOGGING")

    def OnSlaveStopped(self, job):
        pass

    def OnSlaveIdle(self, job):
        pass

    def OnSlaveRendering(self, host_name, job):
        self.LogInfo("OnSlaveRendering LOGGING")
        
    def OnSlaveStartingJob(self, host_name, job):
        self.LogInfo("OnSlaveStartingJob LOGGING")
        # inject params must be here for Resubmits
        self.inject_pype_environment(job)

    def OnSlaveStalled(self, job):
        pass

    def OnIdleShutdown(self, job):
        pass

    def OnMachineStartup(self, job):
        pass

    def OnThermalShutdown(self, job):
        pass

    def OnMachineRestart(self, job):
        pass
