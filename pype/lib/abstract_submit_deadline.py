# -*- coding: utf-8 -*-
"""Abstract class for submitting jobs to Deadline."""
import os
from abc import ABCMeta, abstractmethod
import platform
import getpass

import six
import attr
import requests

import pyblish.api


@attr.s
class DeadlineJobInfo:
    """Mapping of all Deadline *JobInfo* attributes.

    This contains all JobInfo attributes plus their default values.
    Those attributes set to `None` shouldn't be posted to Deadline as
    the only required one is `Plugin`. Their default values used by Deadline
    are stated in
    comments.

    ..seealso:
        https://docs.thinkboxsoftware.com/products/deadline/10.1/1_User%20Manual/manual/manual-submission.html

    """

    # Required
    # ----------------------------------------------
    Plugin = attr.ib()

    # General
    Frames = attr.ib(default=None)  # default: 0
    Name = attr.ib(default="Untitled")
    Comment = attr.ib(default=None)  # default: empty
    Department = attr.ib(default=None)  # default: empty
    BatchName = attr.ib(default=None)  # default: empty
    UserName = attr.ib(default=getpass.getuser())
    MachineName = attr.ib(default=platform.node())
    Pool = attr.ib(default=None)  # default: "none"
    SecondaryPool = attr.ib(default=None)
    Group = attr.ib(default=None)  # default: "none"
    Priority = attr.ib(default=50)
    ChunkSize = attr.ib(default=1)
    ConcurrentTasks = attr.ib(default=1)
    LimitConcurrentTasksToNumberOfCpus = attr.ib(
        default=None)  # default: "true"
    OnJobComplete = attr.ib(default="Nothing")
    SynchronizeAllAuxiliaryFiles = attr.ib(default=None)  # default: false
    ForceReloadPlugin = attr.ib(default=None)  # default: false
    Sequential = attr.ib(default=None)  # default: false
    SuppressEvents = attr.ib(default=None)  # default: false
    Protected = attr.ib(default=None)  # default: false
    InitialStatus = attr.ib(default="Active")
    NetworkRoot = attr.ib(default=None)

    # Timeouts
    # ----------------------------------------------
    MinRenderTimeSeconds = attr.ib(default=None)  # Default: 0
    MinRenderTimeMinutes = attr.ib(default=None)  # Default: 0
    TaskTimeoutSeconds = attr.ib(default=None)  # Default: 0
    TaskTimeoutMinutes = attr.ib(default=None)  # Default: 0
    StartJobTimeoutSeconds = attr.ib(default=None)  # Default: 0
    StartJobTimeoutMinutes = attr.ib(default=None)  # Default: 0
    InitializePluginTimeoutSeconds = attr.ib(default=None)  # Default: 0
    # can be one of <Error/Notify/ErrorAndNotify/Complete>
    OnTaskTimeout = attr.ib(default=None)  # Default: Error
    EnableTimeoutsForScriptTasks = attr.ib(default=None)  # Default: false
    EnableFrameTimeouts = attr.ib(default=None)  # Default: false
    EnableAutoTimeout = attr.ib(default=None)  # Default: false

    # Interruptible
    # ----------------------------------------------
    Interruptible = attr.ib(default=None)  # Default: false
    InterruptiblePercentage = attr.ib(default=None)
    RemTimeThreshold = attr.ib(default=None)

    # Notifications
    # ----------------------------------------------
    # can be comma separated list of users
    NotificationTargets = attr.ib(default=None)  # Default: blank
    ClearNotificationTargets = attr.ib(default=None)  # Default: false
    # A comma separated list of additional email addresses
    NotificationEmails = attr.ib(default=None)  # Default: blank
    OverrideNotificationMethod = attr.ib(default=None)  # Default: false
    EmailNotification = attr.ib(default=None)  # Default: false
    PopupNotification = attr.ib(default=None)  # Default: false
    # String with `[EOL]` used for end of line
    NotificationNote = attr.ib(default=None)  # Default: blank

    # Machine Limit
    # ----------------------------------------------
    MachineLimit = attr.ib(default=None)  # Default: 0
    MachineLimitProgress = attr.ib(default=None)  # Default: -1.0
    Whitelist = attr.ib(default=None)  # Default: blank
    Blacklist = attr.ib(default=None)  # Default: blank

    # Limits
    # ----------------------------------------------
    # comma separated list of limit groups
    LimitGroups = attr.ib(default=None)  # Default: blank

    # Dependencies
    # ----------------------------------------------
    # comma separated list of job IDs
    JobDependencies = attr.ib(default=None)  # Default: blank
    JobDependencyPercentage = attr.ib(default=None)  # Default: -1
    IsFrameDependent = attr.ib(default=None)  # Default: false
    FrameDependencyOffsetStart = attr.ib(default=None)  # Default: 0
    FrameDependencyOffsetEnd = attr.ib(default=None)  # Default: 0
    ResumeOnCompleteDependencies = attr.ib(default=None)  # Default: true
    ResumeOnDeletedDependencies = attr.ib(default=None)  # Default: false
    ResumeOnFailedDependencies = attr.ib(default=None)  # Default: false
    # comma separated list of asset paths
    RequiredAssets = attr.ib(default=None)  # Default: blank
    # comma separated list of script paths
    ScriptDependencies = attr.ib(default=None)  # Default: blank

    # Failure Detection
    # ----------------------------------------------
    OverrideJobFailureDetection = attr.ib(default=None)  # Default: false
    FailureDetectionJobErrors = attr.ib(default=None)  # 0..x
    OverrideTaskFailureDetection = attr.ib(default=None)  # Default: false
    FailureDetectionTaskErrors = attr.ib(default=None)  # 0..x
    IgnoreBadJobDetection = attr.ib(default=None)  # Default: false
    SendJobErrorWarning = attr.ib(default=None)  # Default: false

    # Cleanup
    # ----------------------------------------------
    DeleteOnComplete = attr.ib(default=None)  # Default: false
    ArchiveOnComplete = attr.ib(default=None)  # Default: false
    OverrideAutoJobCleanup = attr.ib(default=None)  # Default: false
    OverrideJobCleanup = attr.ib(default=None)
    JobCleanupDays = attr.ib(default=None)  # Default: false
    # <ArchiveJobs/DeleteJobs>
    OverrideJobCleanupType = attr.ib(default=None)

    # Scheduling
    # ----------------------------------------------
    # <None/Once/Daily/Custom>
    ScheduledType = attr.ib(default=None)  # Default: None
    # <dd/MM/yyyy HH:mm>
    ScheduledStartDateTime = attr.ib(default=None)
    ScheduledDays = attr.ib(default=None)  # Default: 1
    # <dd:hh:mm:ss>
    JobDelay = attr.ib(default=None)
    # <Day of the Week><Start/Stop>Time=<HH:mm:ss>
    Scheduled = attr.ib(default=None)

    # Scripts
    # ----------------------------------------------
    # all accept path to script
    PreJobScript = attr.ib(default=None)  # Default: blank
    PostJobScript = attr.ib(default=None)  # Default: blank
    PreTaskScript = attr.ib(default=None)  # Default: blank
    PostTaskScript = attr.ib(default=None)  # Default: blank

    # Event Opt-Ins
    # ----------------------------------------------
    # comma separated list of plugins
    EventOptIns = attr.ib(default=None)  # Default: blank

    # Environment
    # ----------------------------------------------
    _environmentKeyValue = attr.ib(factory=list)

    @property
    def EnvironmentKeyValue(self):  # noqa: N802
        """Return all environment key values formatted for Deadline.

        Returns:
            list of tuples: as `[('EnvironmentKeyValue0', 'key=value')]`

        """
        out = []
        index = 0
        for v in self._environmentKeyValue:
            out.append(("EnvironmentKeyValue{}".format(index), v))
            index += 1
        return out

    @EnvironmentKeyValue.setter
    def EnvironmentKeyValue(self, val):  # noqa: N802
        self._environmentKeyValue.append(val)

    IncludeEnvironment = attr.ib(default=None)  # Default: false
    UseJobEnvironmentOnly = attr.ib(default=None)  # Default: false
    CustomPluginDirectory = attr.ib(default=None)  # Default: blank

    # Job Extra Info
    # ----------------------------------------------
    _extraInfos = attr.ib(factory=list)
    _extraInfoKeyValues = attr.ib(factory=list)

    @property
    def ExtraInfo(self):  # noqa: N802
        """Return all ExtraInfo values formatted for Deadline.

        Returns:
            list of tuples: as `[('ExtraInfo0', 'value')]`

        """
        out = []
        index = 0
        for v in self._extraInfos:
            out.append(("ExtraInfo{}".format(index), v))
            index += 1
        return out

    @ExtraInfo.setter
    def ExtraInfo(self, val):  # noqa: N802
        self._extraInfos.append(val)

    @property
    def ExtraInfoKeyValue(self):  # noqa: N802
        """Return all ExtraInfoKeyValue values formatted for Deadline.

        Returns:
            list of tuples: as `[('ExtraInfoKeyValue0', 'key=value')]`

        """
        out = []
        index = 0
        for v in self._extraInfoKeyValues:
            out.append(("ExtraInfoKeyValue{}".format(index), v))
            index += 1
        return out

    @ExtraInfoKeyValue.setter
    def ExtraInfoKeyValue(self, val):  # noqa: N802
        self._extraInfoKeyValues.append(val)

    # Task Extra Info Names
    # ----------------------------------------------
    OverrideTaskExtraInfoNames = attr.ib(default=None)  # Default: false
    _taskExtraInfos = attr.ib(factory=list)

    @property
    def TaskExtraInfoName(self):  # noqa: N802
        """Return all TaskExtraInfoName values formatted for Deadline.

        Returns:
            list of tuples: as `[('TaskExtraInfoName0', 'value')]`

        """
        out = []
        index = 0
        for v in self._taskExtraInfos:
            out.append(("TaskExtraInfoName{}".format(index), v))
            index += 1
        return out

    @TaskExtraInfoName.setter
    def TaskExtraInfoName(self, val):  # noqa: N802
        self._taskExtraInfos.append(val)

    # Output
    # ----------------------------------------------
    _outputFilename = attr.ib(factory=list)
    _outputFilenameTile = attr.ib(factory=list)
    _outputDirectory = attr.ib(factory=list)

    @property
    def OutputFilename(self):  # noqa: N802
        """Return all OutputFilename values formatted for Deadline.

        Returns:
            list of tuples: as `[('OutputFilename0', 'filename')]`

        """
        out = []
        index = 0
        for v in self._outputFilename:
            out.append(("OutputFilename{}".format(index), v))
            index += 1
        return out

    @OutputFilename.setter
    def OutputFilename(self, val):  # noqa: N802
        self._outputFilename.append(val)

    @property
    def OutputFilenameTile(self):  # noqa: N802
        """Return all OutputFilename#Tile values formatted for Deadline.

        Returns:
            list of tuples: as `[('OutputFilename#Tile', 'tile')]`

        """
        out = []
        index = 0
        for v in self._outputFilenameTile:
            out.append(("OutputFilename{}Tile".format(index), v))
            index += 1
        return out

    @OutputFilenameTile.setter
    def OutputFilenameTile(self, val):  # noqa: N802
        self._outputFilenameTile.append(val)

    @property
    def OutputDirectory(self):  # noqa: N802
        """Return all OutputDirectory values formatted for Deadline.

        Returns:
            list of tuples: as `[('OutputDirectory0', 'dir')]`

        """
        out = []
        index = 0
        for v in self._outputDirectory:
            out.append(("OutputDirectory{}".format(index), v))
            index += 1
        return out

    @OutputDirectory.setter
    def OutputDirectory(self, val):  # noqa: N802
        self._outputDirectory.append(val)

    # Tile Job
    # ----------------------------------------------
    TileJob = attr.ib(default=None)  # Default: false
    TileJobFrame = attr.ib(default=None)  # Default: 0
    TileJobTilesInX = attr.ib(default=None)  # Default: 0
    TileJobTilesInY = attr.ib(default=None)  # Default: 0
    TileJobTileCount = attr.ib(default=None)  # Default: 0

    # Maintenance Job
    # ----------------------------------------------
    MaintenanceJob = attr.ib(default=None)  # Default: false
    MaintenanceJobStartFrame = attr.ib(default=None)  # Default: 0
    MaintenanceJobEndFrame = attr.ib(default=None)  # Default: 0


@attr.s
class DeadlinePluginInfo:
    SceneFile = attr.ib()


@six.add_metaclass(ABCMeta)
class AbstractSubmitDeadline(pyblish.api.InstancePlugin):

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    use_published = True
    asset_dependencies = False

    def submit(self, payload):
        url = "{}/api/jobs".format(self._deadline_url)
        response = self._requests_post(url, json=payload)
        if not response.ok:
            self.log.error("Submition failed!")
            self.log.error(response.status_code)
            self.log.error(response.content)
            self.log.debug(payload)
            raise RuntimeError(response.text)

        dependency = response.json()
        return dependency["_id"]

    def _requests_post(self, *args, **kwargs):
        """Wrap request post method.

        Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
        variable is found. This is useful when Deadline or Muster server are
        running with self-signed certificates and their certificate is not
        added to trusted certificates on client machines.

        Warning:
            Disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.

        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("PYPE_DONT_VERIFY_SSL", True) else True  # noqa
        # add 10sec timeout before bailing out
        kwargs['timeout'] = 10
        return requests.post(*args, **kwargs)

    def _requests_get(self, *args, **kwargs):
        """Wrap request get method.

        Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
        variable is found. This is useful when Deadline or Muster server are
        running with self-signed certificates and their certificate is not
        added to trusted certificates on client machines.

        Warning:
            Disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.

        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("PYPE_DONT_VERIFY_SSL", True) else True  # noqa
        # add 10sec timeout before bailing out
        kwargs['timeout'] = 10
        return requests.get(*args, **kwargs)
