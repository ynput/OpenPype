from pype.lib import abstract_submit_deadline, DeadlineJobInfo
from abc import ABCMeta, abstractmethod
import pyblish.api
import os
import attr
import six

@attr.s
class DeadlinePluginInfo():
    SceneFile = attr.ib(default=None)
    OutputFilePath = attr.ib(default=None)
    StartupDirectory = attr.ib(default=None)
    Arguments = attr.ib(default=None)
    ProjectPath = attr.ib(default=None)
    SceneFile = attr.ib(default=None)
    AWSAssetFile0 = attr.ib(default=None)


@six.add_metaclass(ABCMeta)
class AfterEffectsSubmitDeadline(abstract_submit_deadline.AbstractSubmitDeadline):

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["aftereffects"]
    families = ["render.farm"]

    def get_job_info(self):
        deadline_job_info = DeadlineJobInfo()
        context = self._instance["context"]

        print("self._instance::{}".format(self._instance))
        print("context::{}".format(context))
        deadline_job_info.Name = "TestName"
        deadline_job_info.Plugin = "AfterEffects"
        deadline_job_info.UserName = "Test User"  # context
        deadline_job_info.Department = "Test department"
        deadline_job_info.Priority = 50
        deadline_job_info.Group = "Test group"
        deadline_job_info.Pool = "Test pool"
        frame_range = "{}-{}".format(self._instance.data["frameStart"],
                                     self._instance.data["frameEnd"])
        deadline_job_info.Frames = frame_range
        deadline_job_info.Comment = "Test comment"  # context
        deadline_job_info.OutputFilename = "c:/projects/test.txt"
        deadline_job_info.ScheduledType = "Once"
        deadline_job_info.JobDelay = "00:00:00"

        print("deadline_job_info::{}".format(deadline_job_info))

        return deadline_job_info

    def get_plugin_info(self):
        deadline_plugin_info = DeadlinePluginInfo()
        context = self._instance["context"]
        script_path = context.data["currentFile"]

        render_path = self._instance.data['path']
        render_dir = os.path.normpath(os.path.dirname(render_path))

        #renderer_path = "C:\\Program Files\\Adobe\\Adobe After Effects 2020\\Support Files\\aerender.exe"

        args = [
            "-s <STARTFRAME>",
            "-e <ENDFRAME>",
            f"-project <QUOTE>{script_path}<QUOTE>",
            f"-output <QUOTE>{render_dir}<QUOTE>"
            "-comp \"Comp\""
        ]

        deadline_plugin_info.SceneFile = script_path
        deadline_plugin_info.OutputFilePath = render_dir.replace("\\", "/")

        deadline_plugin_info.StartupDirectory = ""
        deadline_plugin_info.Arguments = " ".join(args)

        deadline_plugin_info.ProjectPath = script_path
        deadline_plugin_info.AWSAssetFile0 = render_path

        print("deadline_plugin_info::{}".format(deadline_plugin_info))

        return deadline_plugin_info
