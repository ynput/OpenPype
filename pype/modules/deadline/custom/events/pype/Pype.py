import os
import sys
import logging
import json

import Deadline.Events
import Deadline.Scripting


def GetDeadlineEventListener():
    return PypeEventListener()


def CleanupDeadlineEventListener(eventListener):
    eventListener.Cleanup()


class PypeEventListener(Deadline.Events.DeadlineEventListener):

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

    def inject_pype_environment(self, job, additonalData={}):

        # returning early if no plugins are configured
        # if not self.GetConfigEntryWithDefault(config_entry, ""):
        #     return

        # adding python search paths
        paths = self.GetConfigEntryWithDefault("PythonSearchPaths", "").strip()
        paths = paths.split(";")

        for path in paths:
            self.LogInfo("Extending sys.path with: " + str(path))
            sys.path.append(path)


        # setup logging
        level_item = self.GetConfigEntryWithDefault("LoggingLevel", "DEBUG")
        level = logging.DEBUG

        if level_item == "INFO":
            level = logging.INFO
        if level_item == "WARNING":
            level = logging.WARNING
        if level_item == "ERROR":
            level = logging.ERROR

        logging.basicConfig(level=level)
        logger = logging.getLogger()

        self.LogInfo("TESTING LOGGING")

        # setup username
        os.environ["LOGNAME"] = job.UserName


    def updateFtrackStatus(self, job, statusName, createIfMissing=False):
        "Updates version status on ftrack"
        pass


    def OnJobSubmitted(self, job):

        self.updateFtrackStatus(job, "Render Queued")

    def OnJobStarted(self, job):

        self.inject_pype_environment(job)
        self.updateFtrackStatus(job, "Rendering")

    def OnJobFinished(self, job):

        self.updateFtrackStatus(job, "Artist Review")

    def OnJobRequeued(self, job):

        pass

    def OnJobFailed(self, job):

        pass

    def OnJobSuspended(self, job):

        self.updateFtrackStatus(job, "Render Queued")

    def OnJobResumed(self, job):

        self.inject_pype_environment(job)
        self.updateFtrackStatus(job, "Rendering")

    def OnJobPended(self, job):

        pass

    def OnJobReleased(self, job):

        pass

    def OnJobDeleted(self, job):

        pass

    def OnJobError(self, job, task, report):

        data = {"task": task, "report": report}
        self.inject_pype_environment(job, data)

    def OnJobPurged(self, job):

        pass

    def OnHouseCleaning(self):

        pass

    def OnRepositoryRepair(self, job):

        pass

    def OnSlaveStarted(self, job):

        pass

    def OnSlaveStopped(self, job):

        pass

    def OnSlaveIdle(self, job):

        pass

    def OnSlaveRendering(self, job):

        pass

    def OnSlaveStartingJob(self, job):

        pass

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
