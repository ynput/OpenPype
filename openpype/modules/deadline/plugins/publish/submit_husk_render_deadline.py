import hou

import os
import attr
import getpass
from datetime import datetime
import pyblish.api

from openpype.pipeline import legacy_io
from openpype.tests.lib import is_in_tests
from openpype_modules.deadline import abstract_submit_deadline
from openpype_modules.deadline.abstract_submit_deadline import DeadlineJobInfo
from openpype.lib import is_running_from_build


@attr.s
class DeadlinePluginInfo():
    ScriptFile = attr.ib(default=None)
    Arguments = attr.ib(default=None)
    OutputDriver = attr.ib(default=None)
    Version = attr.ib(default=None)
    IgnoreInputs = attr.ib(default=True)


class HuskSubmitDeadline(abstract_submit_deadline.AbstractSubmitDeadline):
    """Submit Solaris USD Render ROPs to Deadline.

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable AVALON_DEADLINE.

    Target "local":
        Even though this does *not* render locally this is seen as
        a 'local' submission as it is the regular way of submitting
        a Houdini render locally.

    """

    label = "Submit Husk Render to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["houdini"]
    families = ["husk_rop"]
    targets = ["local"]
    use_published = True

    def get_job_info(self):
        job_info = DeadlineJobInfo(Plugin="HuskVFXTricks")

        instance = self._instance
        context = instance.context

        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)

        job_info.Name = "{} - {}".format(filename, instance.name)
        job_info.BatchName = filename
        job_info.Plugin = "HuskVFXTricks"
        job_info.UserName = context.data.get(
            "deadlineUser", getpass.getuser())

        if is_in_tests():
            job_info.BatchName += datetime.now().strftime("%d%m%Y%H%M%S")

        # Deadline requires integers in frame range
        frames = "{start}-{end}x{step}".format(
            start=int(instance.data["frameStart"]),
            end=int(instance.data["frameEnd"]),
            step=int(instance.data["byFrameStep"]),
        )
        job_info.Frames = frames

        job_info.Pool = instance.data.get("primaryPool")
        job_info.SecondaryPool = instance.data.get("secondaryPool")
        job_info.ChunkSize = instance.data.get("chunkSize", 10)
        job_info.Comment = context.data.get("comment")

        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
        ]


        # Add OpenPype version if we are running from build.
        if is_running_from_build():
            keys.append("OPENPYPE_VERSION")

        # Add mongo url if it's enabled
        if self._instance.context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)
        for key in keys:
            value = environment.get(key)
            if value:
                job_info.EnvironmentKeyValue[key] = value

        # to recognize render jobs
        job_info.add_render_job_env_var()

        for i, filepath in enumerate(instance.data["files"]):
            dirname = os.path.dirname(filepath)
            fname = os.path.basename(filepath)
            job_info.OutputDirectory += dirname.replace("\\", "/")
            job_info.OutputFilename += fname

        return job_info

    def get_plugin_info(self):

        instance = self._instance
        context = instance.context

        # Output driver to render
        driver = hou.node(instance.data["instance_node"])
        hou_major_minor = hou.applicationVersionString().rsplit(".", 1)[0]

# Arguments=husk.exe -R HdVRayRendererPlugin -f <STARTFRAME> -n 0 -i 1 -Va3 -o 
# //172.16.22.40/000000_Pipeline_RND/60_PRODUCTION/work/render/shots/SEQ_TEST/SEQ_SH01/lighting/testPSB/SEQ_SH01_lighting_testPSB.v002.001/SEQ_SH01_lighting_testPSB.v002.001.%04d.exr 
# --make-output-path --exrmode 0 --snapshot 60 --snapshot-suffix "" //172.16.22.40/000000_Pipeline_RND/60_PRODUCTION/work/render/shots/SEQ_TEST/SEQ_SH01/lighting/testPSB/SEQ_SH01_lighting_testPSB.v002.001/usd/SEQ_SH01_lighting_testPSB.v002.001.usd 
# -e <ENDFRAME> -log //172.16.22.40/000000_Pipeline_RND/60_PRODUCTION/work/render/shots/SEQ_TEST/SEQ_SH01/lighting/testPSB/SEQ_SH01_lighting_testPSB.v002.001/log
# ScriptFile=R:\HSITE\WORKGROUPS\houdini19.5\VFXTricks\scripts\run_husk.py


        plugin_info = DeadlinePluginInfo(
            Arguments="husk.exe -R HdVRayRendererPlugin -f <STARTFRAME> -n 0 -i 1 -Va3 -o --make-output-path --exrmode 0 --snapshot 60 --snapshot-suffix "" //172.16.22.40/000000_Pipeline_RND/60_PRODUCTION/work/render/shots/SEQ_TEST/SEQ_SH01/lighting/testPSB/SEQ_SH01_lighting_testPSB.v002.001/usd/SEQ_SH01_lighting_testPSB.v002.001.usd -e <ENDFRAME> -log //172.16.22.40/000000_Pipeline_RND/60_PRODUCTION/work/render/shots/SEQ_TEST/SEQ_SH01/lighting/testPSB/SEQ_SH01_lighting_testPSB.v002.001/log",
            ScriptFile="R:/HSITE/WORKGROUPS/houdini19.5/VFXTricks/scripts/run_husk.py",
            OutputDriver=driver.path(),
            Version=hou_major_minor,
            IgnoreInputs=True
        )

        return attr.asdict(plugin_info)

    def process(self, instance):
        super(HuskSubmitDeadline, self).process(instance)

        # TODO: Avoid the need for this logic here, needed for submit publish
        # Store output dir for unified publisher (filesequence)
        output_dir = os.path.dirname(instance.data["files"][0])
        instance.data["outputDir"] = output_dir
