import os
import attr
from datetime import datetime

from openpype import AYON_SERVER_ENABLED
from openpype.pipeline import legacy_io, PublishXmlValidationError
from openpype.pipeline.context_tools import get_current_project_name
from openpype.tests.lib import is_in_tests
from openpype.lib import is_running_from_build

from openpype_modules.deadline import abstract_submit_deadline
from openpype_modules.deadline.abstract_submit_deadline import DeadlineJobInfo
from openpype.modules.deadline.utils import set_custom_deadline_name, DeadlineDefaultJobAttrs, get_deadline_job_profile

import pyblish.api

try:
    from maya import cmds
except ImportError:
    # Ignoring, we don't want misleading error logs on jobs log on deadline.
    # Because the farm publish function imports every publish file before filtering.
    pass


@attr.s
class MayaPluginInfo(object):
    Build = attr.ib(default=None)  # Don't force build
    StrictErrorChecking = attr.ib(default=True)

    SceneFile = attr.ib(default=None)  # Input scene
    Version = attr.ib(default=None)  # Mandatory for Deadline
    ProjectPath = attr.ib(default=None)

    ScriptJob = attr.ib(default=True)
    ScriptFilename = attr.ib(default=None)


class MayaSubmitRemotePublishDeadline(
        abstract_submit_deadline.AbstractSubmitDeadline, DeadlineDefaultJobAttrs):
    """Submit Maya scene to perform a local publish in Deadline.

    Publishing in Deadline can be helpful for scenes that publish very slow.
    This way it can process in the background on another machine without the
    Artist having to wait for the publish to finish on their local machine.

    Submission is done through the Deadline Web Service. DL then triggers
    `openpype/scripts/remote_publish.py`.

    Each publishable instance creates its own full publish job.

    Different from `ProcessSubmittedJobOnFarm` which creates publish job
    depending on metadata json containing context and instance data of
    rendered files.
    """

    label = "Submit Scene to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["maya"]
    families = ["publish.farm"]
    targets = ["local"]

    def process(self, instance):

        # Ensure no errors so far
        if not (all(result["success"]
                for result in instance.context.data["results"])):
            raise PublishXmlValidationError("Publish process has errors")

        if not instance.data["publish"]:
            self.log.warning("No active instances found. "
                             "Skipping submission..")
            return

        super(MayaSubmitRemotePublishDeadline, self).process(instance)

    def get_job_info(self):
        instance = self._instance
        context = instance.context

        project_name = instance.context.data["projectName"]
        scene = instance.context.data["currentFile"]
        scenename = os.path.basename(scene)

        project_name = get_current_project_name()
        project_settings = context.data["project_settings"]
        profile = get_deadline_job_profile(project_settings, self.hosts[0])

        job_name = set_custom_deadline_name(
            instance,
            scenename,
            "deadline_job_name"
        )
        batch_name = set_custom_deadline_name(
            instance,
            scenename,
            "deadline_batch_name"
        )

        if is_in_tests():
            batch_name += datetime.now().strftime("%d%m%Y%H%M%S")

        job_info = DeadlineJobInfo(Plugin="MayaBatch")
        job_info.BatchName = "Group: " + batch_name,
        job_info.Name = job_name
        job_info.UserName = context.data.get("user")
        job_info.Comment = context.data.get("comment", "")

        # Use setting for publish job on farm, no reason to have it separately
        deadline_publish_job_sett = project_settings["deadline"]["publish"]["ProcessSubmittedJobOnFarm"]  # noqa
        job_info.Department = deadline_publish_job_sett["department"]
        job_info.ChunkSize = deadline_publish_job_sett["chunk_size"]
        job_info.Priority = profile.get("priority", self.default_priority)
        job_info.Group = deadline_publish_job_sett["group"]
        job_info.Pool = profile.get("pool", self.default_pool)
        job_info.SecondaryPool = profile.get("pool_secondary", self.default_pool_secondary)
        job_info.MachineLimit = profile.get("limit_machine", self.default_limit_machine)
        job_info.LimitGroups = profile.get("limit_plugins", self.default_limits_plugin)

        # Include critical environment variables with submission + Session
        keys = [
            "FTRACK_API_USER",
            "FTRACK_API_KEY",
            "FTRACK_SERVER"
        ]

        # Add OpenPype version if we are running from build.
        if is_running_from_build():
            keys.append("OPENPYPE_VERSION")

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)

        # TODO replace legacy_io with context.data
        environment["AVALON_PROJECT"] = project_name
        environment["AVALON_ASSET"] = instance.context.data["asset"]
        environment["AVALON_TASK"] = instance.context.data["task"]
        environment["AVALON_APP_NAME"] = os.environ.get("AVALON_APP_NAME")
        environment["OPENPYPE_LOG_NO_COLORS"] = "1"
        environment["OPENPYPE_USERNAME"] = instance.context.data["user"]
        environment["OPENPYPE_PUBLISH_SUBSET"] = instance.data["subset"]
        environment["OPENPYPE_REMOTE_PUBLISH"] = "1"

        if AYON_SERVER_ENABLED:
            environment["AYON_REMOTE_PUBLISH"] = "1"
        else:
            environment["OPENPYPE_REMOTE_PUBLISH"] = "1"
        for key, value in environment.items():
            job_info.EnvironmentKeyValue[key] = value

    def get_plugin_info(self):

        scene = self._instance.context.data["currentFile"]

        plugin_info = MayaPluginInfo()
        plugin_info.SceneFile = scene
        plugin_info.ScriptFilename = "{OPENPYPE_REPOS_ROOT}/openpype/scripts/remote_publish.py"  # noqa
        plugin_info.Version = cmds.about(version=True)
        plugin_info.ProjectPath = cmds.workspace(query=True,
                                                 rootDirectory=True)

        return attr.asdict(plugin_info)
