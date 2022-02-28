# -*- coding: utf-8 -*-
"""Abstract package for submitting jobs to Deadline.

It provides Deadline JobInfo data class.

"""
import os
from abc import abstractmethod
import platform
import getpass
from collections import OrderedDict

import six
import attr
import requests

import pyblish.api
from openpype.lib.abstract_metaplugins import AbstractMetaInstancePlugin


def requests_post(*args, **kwargs):
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
        kwargs['verify'] = False if os.getenv("OPENPYPE_DONT_VERIFY_SSL",
                                              True) else True  # noqa
    # add 10sec timeout before bailing out
    kwargs['timeout'] = 10
    return requests.post(*args, **kwargs)


def requests_get(*args, **kwargs):
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
        kwargs['verify'] = False if os.getenv("OPENPYPE_DONT_VERIFY_SSL",
                                              True) else True  # noqa
    # add 10sec timeout before bailing out
    kwargs['timeout'] = 10
    return requests.get(*args, **kwargs)


@attr.s
class DeadlineJobInfo(object):
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
            dict: as `{'EnvironmentKeyValue0', 'key=value'}`

        """
        out = {}
        for index, v in enumerate(self._environmentKeyValue):
            out["EnvironmentKeyValue{}".format(index)] = v
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
            dict: as `{'ExtraInfo0': 'value'}`

        """
        out = {}
        for index, v in enumerate(self._extraInfos):
            out["ExtraInfo{}".format(index)] = v
        return out

    @ExtraInfo.setter
    def ExtraInfo(self, val):  # noqa: N802
        self._extraInfos.append(val)

    @property
    def ExtraInfoKeyValue(self):  # noqa: N802
        """Return all ExtraInfoKeyValue values formatted for Deadline.

        Returns:
            dict: as {'ExtraInfoKeyValue0': 'key=value'}`

        """
        out = {}
        for index, v in enumerate(self._extraInfoKeyValues):
            out["ExtraInfoKeyValue{}".format(index)] = v
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
            dict: as `{'TaskExtraInfoName0': 'value'}`

        """
        out = {}
        for index, v in enumerate(self._taskExtraInfos):
            out["TaskExtraInfoName{}".format(index)] = v
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
            dict: as `{'OutputFilename0': 'filename'}`

        """
        out = {}
        for index, v in enumerate(self._outputFilename):
            out["OutputFilename{}".format(index)] = v
        return out

    @OutputFilename.setter
    def OutputFilename(self, val):  # noqa: N802
        self._outputFilename.append(val)

    @property
    def OutputFilenameTile(self):  # noqa: N802
        """Return all OutputFilename#Tile values formatted for Deadline.

        Returns:
            dict: as `{'OutputFilenme#Tile': 'tile'}`

        """
        out = {}
        for index, v in enumerate(self._outputFilenameTile):
            out["OutputFilename{}Tile".format(index)] = v
        return out

    @OutputFilenameTile.setter
    def OutputFilenameTile(self, val):  # noqa: N802
        self._outputFilenameTile.append(val)

    @property
    def OutputDirectory(self):  # noqa: N802
        """Return all OutputDirectory values formatted for Deadline.

        Returns:
            dict: as `{'OutputDirectory0': 'dir'}`

        """
        out = {}
        for index, v in enumerate(self._outputDirectory):
            out["OutputDirectory{}".format(index)] = v
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

    def serialize(self):
        """Return all data serialized as dictionary.

        Returns:
            OrderedDict: all serialized data.

        """
        def filter_data(a, v):
            if a.name.startswith("_"):
                return False
            if v is None:
                return False
            return True

        serialized = attr.asdict(
            self, dict_factory=OrderedDict, filter=filter_data)
        serialized.update(self.EnvironmentKeyValue)
        serialized.update(self.ExtraInfo)
        serialized.update(self.ExtraInfoKeyValue)
        serialized.update(self.TaskExtraInfoName)
        serialized.update(self.OutputFilename)
        serialized.update(self.OutputFilenameTile)
        serialized.update(self.OutputDirectory)
        return serialized


@six.add_metaclass(AbstractMetaInstancePlugin)
class AbstractSubmitDeadline(pyblish.api.InstancePlugin):
    """Class abstracting access to Deadline."""

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    use_published = True
    asset_dependencies = False

    def __init__(self, *args, **kwargs):
        super(AbstractSubmitDeadline, self).__init__(*args, **kwargs)
        self._instance = None
        self._deadline_url = None
        self.scene_path = None
        self.job_info = None
        self.plugin_info = None
        self.aux_files = None

    def process(self, instance):
        """Plugin entry point."""
        self._instance = instance
        context = instance.context
        self._deadline_url = context.data.get("defaultDeadline")
        self._deadline_url = instance.data.get(
            "deadlineUrl", self._deadline_url)

        assert self._deadline_url, "Requires Deadline Webservice URL"

        file_path = None
        if self.use_published:
            file_path = self.from_published_scene()

        # fallback if nothing was set
        if not file_path:
            self.log.warning("Falling back to workfile")
            file_path = context.data["currentFile"]

        self.scene_path = file_path
        self.log.info("Using {} for render/export.".format(file_path))

        self.job_info = self.get_job_info()
        self.plugin_info = self.get_plugin_info()
        self.aux_files = self.get_aux_files()

        self.process_submission()

    def process_submission(self):
        """Process data for submission.

        This takes Deadline JobInfo, PluginInfo, AuxFile, creates payload
        from them and submit it do Deadline.

        Returns:
            str: Deadline job ID

        """
        payload = self.assemble_payload()
        return self.submit(payload)

    @abstractmethod
    def get_job_info(self):
        """Return filled Deadline JobInfo.

        This is host/plugin specific implementation of how to fill data in.

        See:
            :class:`DeadlineJobInfo`

        Returns:
            :class:`DeadlineJobInfo`: Filled Deadline JobInfo.

        """
        pass

    @abstractmethod
    def get_plugin_info(self):
        """Return filled Deadline PluginInfo.

        This is host/plugin specific implementation of how to fill data in.

        See:
            :class:`DeadlineJobInfo`

        Returns:
            dict: Filled Deadline JobInfo.

        """
        pass

    def get_aux_files(self):
        """Return list of auxiliary files for Deadline job.

        If needed this should be overridden, otherwise return empty list as
        that field even empty must be present on Deadline submission.

        Returns:
            list: List of files.

        """
        return []

    def from_published_scene(self, replace_in_path=True):
        """Switch work scene for published scene.

        If rendering/exporting from published scenes is enabled, this will
        replace paths from working scene to published scene.

        Args:
            replace_in_path (bool): if True, it will try to find
                old scene name in path of expected files and replace it
                with name of published scene.

        Returns:
            str: Published scene path.
            None: if no published scene is found.

        Note:
            Published scene path is actually determined from project Anatomy
            as at the time this plugin is running scene can still no be
            published.

        """
        anatomy = self._instance.context.data['anatomy']
        file_path = None
        for i in self._instance.context:
            if "workfile" in i.data["families"] \
                    or i.data["family"] == "workfile":
                # test if there is instance of workfile waiting
                # to be published.
                assert i.data["publish"] is True, (
                    "Workfile (scene) must be published along")
                # determine published path from Anatomy.
                template_data = i.data.get("anatomyData")
                rep = i.data.get("representations")[0].get("ext")
                template_data["representation"] = rep
                template_data["ext"] = rep
                template_data["comment"] = None
                anatomy_filled = anatomy.format(template_data)
                template_filled = anatomy_filled["publish"]["path"]
                file_path = os.path.normpath(template_filled)

                self.log.info("Using published scene for render {}".format(
                    file_path))

                if not os.path.exists(file_path):
                    self.log.error("published scene does not exist!")
                    raise

                if not replace_in_path:
                    return file_path

                # now we need to switch scene in expected files
                # because <scene> token will now point to published
                # scene file and that might differ from current one
                new_scene = os.path.splitext(
                    os.path.basename(file_path))[0]
                orig_scene = os.path.splitext(
                    os.path.basename(
                        self._instance.context.data["currentFile"]))[0]
                exp = self._instance.data.get("expectedFiles")

                if isinstance(exp[0], dict):
                    # we have aovs and we need to iterate over them
                    new_exp = {}
                    for aov, files in exp[0].items():
                        replaced_files = []
                        for f in files:
                            replaced_files.append(
                                str(f).replace(orig_scene, new_scene)
                            )
                        new_exp[aov] = replaced_files
                    # [] might be too much here, TODO
                    self._instance.data["expectedFiles"] = [new_exp]
                else:
                    new_exp = []
                    for f in exp:
                        new_exp.append(
                            str(f).replace(orig_scene, new_scene)
                        )
                    self._instance.data["expectedFiles"] = new_exp

                self.log.info("Scene name was switched {} -> {}".format(
                    orig_scene, new_scene
                ))

        return file_path

    def assemble_payload(
            self, job_info=None, plugin_info=None, aux_files=None):
        """Assemble payload data from its various parts.

        Args:
            job_info (DeadlineJobInfo): Deadline JobInfo. You can use
                :class:`DeadlineJobInfo` for it.
            plugin_info (dict): Deadline PluginInfo. Plugin specific options.
            aux_files (list, optional): List of auxiliary file to submit with
                the job.

        Returns:
            dict: Deadline Payload.

        """
        job = job_info or self.job_info
        return {
            "JobInfo": job.serialize(),
            "PluginInfo": plugin_info or self.plugin_info,
            "AuxFiles": aux_files or self.aux_files
        }

    def submit(self, payload):
        """Submit payload to Deadline API end-point.

        This takes payload in the form of JSON file and POST it to
        Deadline jobs end-point.

        Args:
            payload (dict): dict to become json in deadline submission.

        Returns:
            str: resulting Deadline job id.

        Throws:
            RuntimeError: if submission fails.

        """
        url = "{}/api/jobs".format(self._deadline_url)
        response = requests_post(url, json=payload)
        if not response.ok:
            self.log.error("Submission failed!")
            self.log.error(response.status_code)
            self.log.error(response.content)
            self.log.debug(payload)
            raise RuntimeError(response.text)

        result = response.json()
        # for submit publish job
        self._instance.data["deadlineSubmissionJob"] = result

        return result["_id"]
