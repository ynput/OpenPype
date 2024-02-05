# -*- coding: utf-8 -*-
"""Abstract package for submitting jobs to Deadline.

It provides Deadline JobInfo data class.

"""
import json.decoder
import os
from abc import abstractmethod
import platform
import getpass
from functools import partial
from collections import OrderedDict

import six
import attr
import requests

import pyblish.api
from openpype.pipeline.publish import (
    AbstractMetaInstancePlugin,
    KnownPublishError,
    OpenPypePyblishPluginMixin
)
from openpype.pipeline.publish.lib import (
    replace_with_published_scene_path
)
from openpype import AYON_SERVER_ENABLED

JSONDecodeError = getattr(json.decoder, "JSONDecodeError", ValueError)


def requests_post(*args, **kwargs):
    """Wrap request post method.

    Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
    variable is found. This is useful when Deadline server is
    running with self-signed certificates and its certificate is not
    added to trusted certificates on client machines.

    Warning:
        Disabling SSL certificate validation is defeating one line
        of defense SSL is providing, and it is not recommended.

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
    variable is found. This is useful when Deadline server is
    running with self-signed certificates and its certificate is not
    added to trusted certificates on client machines.

    Warning:
        Disabling SSL certificate validation is defeating one line
        of defense SSL is providing, and it is not recommended.

    """
    if 'verify' not in kwargs:
        kwargs['verify'] = False if os.getenv("OPENPYPE_DONT_VERIFY_SSL",
                                              True) else True  # noqa
    # add 10sec timeout before bailing out
    kwargs['timeout'] = 10
    return requests.get(*args, **kwargs)


class DeadlineKeyValueVar(dict):
    """

    Serializes dictionary key values as "{key}={value}" like Deadline uses
    for EnvironmentKeyValue.

    As an example:
        EnvironmentKeyValue0="A_KEY=VALUE_A"
        EnvironmentKeyValue1="OTHER_KEY=VALUE_B"

    The keys are serialized in alphabetical order (sorted).

    Example:
        >>> var = DeadlineKeyValueVar("EnvironmentKeyValue")
        >>> var["my_var"] = "hello"
        >>> var["my_other_var"] = "hello2"
        >>> var.serialize()


    """
    def __init__(self, key):
        super(DeadlineKeyValueVar, self).__init__()
        self.__key = key

    def serialize(self):
        key = self.__key

        # Allow custom location for index in serialized string
        if "{}" not in key:
            key = key + "{}"

        return {
            key.format(index): "{}={}".format(var_key, var_value)
            for index, (var_key, var_value) in enumerate(sorted(self.items()))
        }


class DeadlineIndexedVar(dict):
    """

    Allows to set and query values by integer indices:
        Query: var[1] or var.get(1)
        Set: var[1] = "my_value"
        Append: var += "value"

    Note: Iterating the instance is not guarantueed to be the order of the
          indices. To do so iterate with `sorted()`

    """
    def __init__(self, key):
        super(DeadlineIndexedVar, self).__init__()
        self.__key = key

    def serialize(self):
        key = self.__key

        # Allow custom location for index in serialized string
        if "{}" not in key:
            key = key + "{}"

        return {
            key.format(index): value for index, value in sorted(self.items())
        }

    def next_available_index(self):
        # Add as first unused entry
        i = 0
        while i in self.keys():
            i += 1
        return i

    def update(self, data):
        # Force the integer key check
        for key, value in data.items():
            self.__setitem__(key, value)

    def __iadd__(self, other):
        index = self.next_available_index()
        self[index] = other
        return self

    def __setitem__(self, key, value):
        if not isinstance(key, int):
            raise TypeError("Key must be an integer: {}".format(key))

        if key < 0:
            raise ValueError("Negative index can't be set: {}".format(key))
        dict.__setitem__(self, key, value)


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
    EnvironmentKeyValue = attr.ib(factory=partial(DeadlineKeyValueVar,
                                                  "EnvironmentKeyValue"))

    IncludeEnvironment = attr.ib(default=None)  # Default: false
    UseJobEnvironmentOnly = attr.ib(default=None)  # Default: false
    CustomPluginDirectory = attr.ib(default=None)  # Default: blank

    # Job Extra Info
    # ----------------------------------------------
    ExtraInfo = attr.ib(factory=partial(DeadlineIndexedVar, "ExtraInfo"))
    ExtraInfoKeyValue = attr.ib(factory=partial(DeadlineKeyValueVar,
                                                "ExtraInfoKeyValue"))

    # Task Extra Info Names
    # ----------------------------------------------
    OverrideTaskExtraInfoNames = attr.ib(default=None)  # Default: false
    TaskExtraInfoName = attr.ib(factory=partial(DeadlineIndexedVar,
                                                "TaskExtraInfoName"))

    # Output
    # ----------------------------------------------
    OutputFilename = attr.ib(factory=partial(DeadlineIndexedVar,
                                             "OutputFilename"))
    OutputFilenameTile = attr.ib(factory=partial(DeadlineIndexedVar,
                                                 "OutputFilename{}Tile"))
    OutputDirectory = attr.ib(factory=partial(DeadlineIndexedVar,
                                              "OutputDirectory"))

    # Asset Dependency
    # ----------------------------------------------
    AssetDependency = attr.ib(factory=partial(DeadlineIndexedVar,
                                              "AssetDependency"))

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
            if isinstance(v, (DeadlineIndexedVar, DeadlineKeyValueVar)):
                return False
            if v is None:
                return False
            return True

        serialized = attr.asdict(
            self, dict_factory=OrderedDict, filter=filter_data)

        # Custom serialize these attributes
        for attribute in [
            self.EnvironmentKeyValue,
            self.ExtraInfo,
            self.ExtraInfoKeyValue,
            self.TaskExtraInfoName,
            self.OutputFilename,
            self.OutputFilenameTile,
            self.OutputDirectory,
            self.AssetDependency
        ]:
            serialized.update(attribute.serialize())

        return serialized

    def update(self, data):
        """Update instance with data dict"""
        for key, value in data.items():
            setattr(self, key, value)

    def add_render_job_env_var(self):
        """Check if in OP or AYON mode and use appropriate env var."""
        if AYON_SERVER_ENABLED:
            self.EnvironmentKeyValue["AYON_RENDER_JOB"] = "1"
            self.EnvironmentKeyValue["AYON_BUNDLE_NAME"] = (
                os.environ["AYON_BUNDLE_NAME"])
        else:
            self.EnvironmentKeyValue["OPENPYPE_RENDER_JOB"] = "1"


@six.add_metaclass(AbstractMetaInstancePlugin)
class AbstractSubmitDeadline(pyblish.api.InstancePlugin,
                             OpenPypePyblishPluginMixin):
    """Class abstracting access to Deadline."""

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1

    import_reference = False
    use_published = True
    asset_dependencies = False
    default_priority = 50

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
            if not self.import_reference:
                file_path = self.from_published_scene()
            else:
                self.log.info("use the scene with imported reference for rendering") # noqa
                file_path = context.data["currentFile"]

        # fallback if nothing was set
        if not file_path:
            self.log.warning("Falling back to workfile")
            file_path = context.data["currentFile"]

        self.scene_path = file_path
        self.log.info("Using {} for render/export.".format(file_path))

        self.job_info = self.get_job_info()
        self.plugin_info = self.get_plugin_info()
        self.aux_files = self.get_aux_files()

        job_id = self.process_submission()
        self.log.info("Submitted job to Deadline: {}.".format(job_id))

        # TODO: Find a way that's more generic and not render type specific
        if instance.data.get("splitRender"):
            self.log.info("Splitting export and render in two jobs")
            self.log.info("Export job id: %s", job_id)
            render_job_info = self.get_job_info(dependency_job_ids=[job_id])
            render_plugin_info = self.get_plugin_info(job_type="render")
            payload = self.assemble_payload(
                job_info=render_job_info,
                plugin_info=render_plugin_info
            )
            render_job_id = self.submit(payload)
            self.log.info("Render job id: %s", render_job_id)

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
        return replace_with_published_scene_path(
            self._instance, replace_in_path=replace_in_path)

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
            KnownPublishError: if submission fails.

        """
        url = "{}/api/jobs".format(self._deadline_url)
        response = requests_post(url, json=payload)
        if not response.ok:
            self.log.error("Submission failed!")
            self.log.error(response.status_code)
            self.log.error(response.content)
            self.log.debug(payload)
            raise KnownPublishError(response.text)

        try:
            result = response.json()
        except JSONDecodeError:
            msg = "Broken response {}. ".format(response)
            msg += "Try restarting the Deadline Webservice."
            self.log.warning(msg, exc_info=True)
            raise KnownPublishError("Broken response from DL")

        # for submit publish job
        self._instance.data["deadlineSubmissionJob"] = result

        return result["_id"]
