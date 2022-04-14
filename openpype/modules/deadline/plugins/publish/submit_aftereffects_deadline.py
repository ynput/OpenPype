import os
import attr
import getpass
import pyblish.api

from openpype.lib import env_value_to_bool
from openpype.lib.delivery import collect_frames
from openpype.pipeline import legacy_io
from openpype_modules.deadline import abstract_submit_deadline
from openpype_modules.deadline.abstract_submit_deadline import DeadlineJobInfo


@attr.s
class DeadlinePluginInfo():
    Comp = attr.ib(default=None)
    SceneFile = attr.ib(default=None)
    OutputFilePath = attr.ib(default=None)
    Output = attr.ib(default=None)
    StartupDirectory = attr.ib(default=None)
    Arguments = attr.ib(default=None)
    ProjectPath = attr.ib(default=None)
    AWSAssetFile0 = attr.ib(default=None)
    Version = attr.ib(default=None)
    MultiProcess = attr.ib(default=None)


class AfterEffectsSubmitDeadline(
    abstract_submit_deadline.AbstractSubmitDeadline
):

    label = "Submit AE to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["aftereffects"]
    families = ["render.farm"]  # cannot be "render' as that is integrated
    use_published = True

    priority = 50
    chunk_size = 1000000
    primary_pool = None
    secondary_pool = None
    group = None
    department = None
    multiprocess = True

    def get_job_info(self):
        dln_job_info = DeadlineJobInfo(Plugin="AfterEffects")

        context = self._instance.context

        dln_job_info.Name = self._instance.data["name"]
        dln_job_info.BatchName = os.path.basename(self._instance.
                                                  data["source"])
        dln_job_info.Plugin = "AfterEffects"
        dln_job_info.UserName = context.data.get(
            "deadlineUser", getpass.getuser())
        if self._instance.data["frameEnd"] > self._instance.data["frameStart"]:
            # Deadline requires integers in frame range
            frame_range = "{}-{}".format(
                int(round(self._instance.data["frameStart"])),
                int(round(self._instance.data["frameEnd"])))
            dln_job_info.Frames = frame_range

        dln_job_info.Priority = self.priority
        dln_job_info.Pool = self.primary_pool
        dln_job_info.SecondaryPool = self.secondary_pool
        dln_job_info.Group = self.group
        dln_job_info.Department = self.department
        dln_job_info.ChunkSize = self.chunk_size
        dln_job_info.OutputFilename = \
            os.path.basename(self._instance.data["expectedFiles"][0])
        dln_job_info.OutputDirectory = \
            os.path.dirname(self._instance.data["expectedFiles"][0])
        dln_job_info.JobDelay = "00:00:00"

        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
            "OPENPYPE_DEV",
            "OPENPYPE_LOG_NO_COLORS"
        ]
        # Add mongo url if it's enabled
        if self._instance.context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)
        for key in keys:
            val = environment.get(key)
            if val:
                dln_job_info.EnvironmentKeyValue = "{key}={value}".format(
                     key=key,
                     value=val)
        # to recognize job from PYPE for turning Event On/Off
        dln_job_info.EnvironmentKeyValue = "OPENPYPE_RENDER_JOB=1"

        return dln_job_info

    def get_plugin_info(self):
        deadline_plugin_info = DeadlinePluginInfo()

        render_path = self._instance.data["expectedFiles"][0]

        file_name, frame = list(collect_frames([render_path]).items())[0]
        if frame:
            # replace frame ('000001') with Deadline's required '[#######]'
            # expects filename in format project_asset_subset_version.FRAME.ext
            render_dir = os.path.dirname(render_path)
            file_name = os.path.basename(render_path)
            hashed = '[{}]'.format(len(frame) * "#")
            file_name = file_name.replace(frame, hashed)
            render_path = os.path.join(render_dir, file_name)

        deadline_plugin_info.Comp = self._instance.data["comp_name"]
        deadline_plugin_info.Version = self._instance.data["app_version"]
        # must be here because of DL AE plugin
        # added override of multiprocess by env var, if shouldn't be used for
        # some app variant use MULTIPROCESS:false in Settings, default is True
        env_multi = env_value_to_bool("MULTIPROCESS", default=True)
        deadline_plugin_info.MultiProcess = env_multi and self.multiprocess
        deadline_plugin_info.SceneFile = self.scene_path
        deadline_plugin_info.Output = render_path.replace("\\", "/")

        return attr.asdict(deadline_plugin_info)

    def from_published_scene(self):
        """ Do not overwrite expected files.

            Use published is set to True, so rendering will be triggered
            from published scene (in 'publish' folder). Default implementation
            of abstract class renames expected (eg. rendered) files accordingly
            which is not needed here.
        """
        return super().from_published_scene(False)
