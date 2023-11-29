# -*- coding: utf-8 -*-
"""Submitting render job to Deadline."""

import os
import getpass
import attr
from datetime import datetime

from openpype.lib import (
    is_running_from_build,
    BoolDef,
    NumberDef,
    TextDef,
)
from openpype.pipeline import legacy_io
from openpype.pipeline.publish import OpenPypePyblishPluginMixin
from openpype.pipeline.farm.tools import iter_expected_files
from openpype.tests.lib import is_in_tests

from openpype_modules.deadline import abstract_submit_deadline
from openpype_modules.deadline.abstract_submit_deadline import DeadlineJobInfo


@attr.s
class BlenderPluginInfo():
    SceneFile = attr.ib(default=None)   # Input
    Version = attr.ib(default=None)  # Mandatory for Deadline
    SaveFile = attr.ib(default=True)


class BlenderSubmitDeadline(abstract_submit_deadline.AbstractSubmitDeadline,
                            OpenPypePyblishPluginMixin):
    label = "Submit Render to Deadline"
    hosts = ["blender"]
    families = ["render"]

    use_published = True
    priority = 50
    chunk_size = 1
    jobInfo = {}
    pluginInfo = {}
    group = None
    job_delay = "00:00:00:00"

    def get_job_info(self):
        job_info = DeadlineJobInfo(Plugin="Blender")

        job_info.update(self.jobInfo)

        instance = self._instance
        context = instance.context

        # Always use the original work file name for the Job name even when
        # rendering is done from the published Work File. The original work
        # file name is clearer because it can also have subversion strings,
        # etc. which are stripped for the published file.
        src_filepath = context.data["currentFile"]
        src_filename = os.path.basename(src_filepath)

        if is_in_tests():
            src_filename += datetime.now().strftime("%d%m%Y%H%M%S")

        job_info.Name = f"{src_filename} - {instance.name}"
        job_info.BatchName = src_filename
        instance.data.get("blenderRenderPlugin", "Blender")
        job_info.UserName = context.data.get("deadlineUser", getpass.getuser())

        # Deadline requires integers in frame range
        frames = "{start}-{end}x{step}".format(
            start=int(instance.data["frameStartHandle"]),
            end=int(instance.data["frameEndHandle"]),
            step=int(instance.data["byFrameStep"]),
        )
        job_info.Frames = frames

        job_info.Pool = instance.data.get("primaryPool")
        job_info.SecondaryPool = instance.data.get("secondaryPool")
        job_info.Comment = instance.data.get("comment")

        if self.group != "none" and self.group:
            job_info.Group = self.group

        attr_values = self.get_attr_values_from_data(instance.data)
        render_globals = instance.data.setdefault("renderGlobals", {})
        machine_list = attr_values.get("machineList", "")
        if machine_list:
            if attr_values.get("whitelist", True):
                machine_list_key = "Whitelist"
            else:
                machine_list_key = "Blacklist"
            render_globals[machine_list_key] = machine_list

        job_info.ChunkSize = attr_values.get("chunkSize", self.chunk_size)
        job_info.Priority = attr_values.get("priority", self.priority)
        job_info.ScheduledType = "Once"
        job_info.JobDelay = attr_values.get("job_delay", self.job_delay)

        # Add options from RenderGlobals
        render_globals = instance.data.get("renderGlobals", {})
        job_info.update(render_globals)

        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "OPENPYPE_SG_USER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
            "OPENPYPE_DEV"
            "IS_TEST"
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
            if not value:
                continue
            job_info.EnvironmentKeyValue[key] = value

        # to recognize job from PYPE for turning Event On/Off
        job_info.add_render_job_env_var()
        job_info.EnvironmentKeyValue["OPENPYPE_LOG_NO_COLORS"] = "1"

        # Adding file dependencies.
        if self.asset_dependencies:
            dependencies = instance.context.data["fileDependencies"]
            for dependency in dependencies:
                job_info.AssetDependency += dependency

        # Add list of expected files to job
        # ---------------------------------
        exp = instance.data.get("expectedFiles")
        for filepath in iter_expected_files(exp):
            job_info.OutputDirectory += os.path.dirname(filepath)
            job_info.OutputFilename += os.path.basename(filepath)

        return job_info

    def get_plugin_info(self):
        # Not all hosts can import this module.
        import bpy

        plugin_info = BlenderPluginInfo(
            SceneFile=self.scene_path,
            Version=bpy.app.version_string,
            SaveFile=True,
        )

        plugin_payload = attr.asdict(plugin_info)

        # Patching with pluginInfo from settings
        for key, value in self.pluginInfo.items():
            plugin_payload[key] = value

        return plugin_payload

    def process_submission(self):
        instance = self._instance

        expected_files = instance.data["expectedFiles"]
        if not expected_files:
            raise RuntimeError("No Render Elements found!")

        first_file = next(iter_expected_files(expected_files))
        output_dir = os.path.dirname(first_file)
        instance.data["outputDir"] = output_dir
        instance.data["toBeRenderedOn"] = "deadline"

        payload = self.assemble_payload()
        return self.submit(payload)

    def from_published_scene(self):
        """
        This is needed to set the correct path for the json metadata. Because
        the rendering path is set in the blend file during the collection,
        and the path is adjusted to use the published scene, this ensures that
        the metadata and the rendered files are in the same location.
        """
        return super().from_published_scene(False)

    @classmethod
    def get_attribute_defs(cls):
        defs = super(BlenderSubmitDeadline, cls).get_attribute_defs()
        defs.extend([
            BoolDef("use_published",
                    default=cls.use_published,
                    label="Use Published Scene"),

            NumberDef("priority",
                      minimum=1,
                      maximum=250,
                      decimals=0,
                      default=cls.priority,
                      label="Priority"),

            NumberDef("chunkSize",
                      minimum=1,
                      maximum=50,
                      decimals=0,
                      default=cls.chunk_size,
                      label="Frame Per Task"),

            TextDef("group",
                    default=cls.group,
                    label="Group Name"),

            TextDef("job_delay",
                    default=cls.job_delay,
                    label="Job Delay",
                    placeholder="dd:hh:mm:ss",
                    tooltip="Delay the job by the specified amount of time. "
                            "Timecode: dd:hh:mm:ss."),
        ])

        return defs
