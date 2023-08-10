# -*- coding: utf-8 -*-
"""Submitting render job to Deadline."""

import os
import getpass
import attr
from datetime import datetime

import bpy

from openpype.lib import is_running_from_build
from openpype.pipeline import legacy_io
from openpype.pipeline.farm.tools import iter_expected_files
from openpype.tests.lib import is_in_tests

from openpype_modules.deadline import abstract_submit_deadline
from openpype_modules.deadline.abstract_submit_deadline import DeadlineJobInfo


def _validate_deadline_bool_value(instance, attribute, value):
    if not isinstance(value, (str, bool)):
        raise TypeError(f"Attribute {attribute} must be str or bool.")
    if value not in {"1", "0", True, False}:
        raise ValueError(
            f"Value of {attribute} must be one of '0', '1', True, False")


@attr.s
class BlenderPluginInfo():
    SceneFile = attr.ib(default=None)   # Input
    Version = attr.ib(default=None)  # Mandatory for Deadline


class BlenderSubmitDeadline(abstract_submit_deadline.AbstractSubmitDeadline):
    label = "Submit Render to Deadline"
    hosts = ["blender"]
    families = ["renderlayer"]

    priority = 50

    jobInfo = {}
    pluginInfo = {}
    group = None

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
        job_info.Comment = context.data.get("comment")
        job_info.Priority = instance.data.get("priority", self.priority)

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

        job_info.Priority = attr_values.get("priority")
        job_info.ChunkSize = attr_values.get("chunkSize")

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
        job_info.EnvironmentKeyValue["OPENPYPE_RENDER_JOB"] = "1"
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
        instance = self._instance
        context = instance.context

        plugin_info = BlenderPluginInfo(
            SceneFile=self.scene_path,
            Version=bpy.app.version_string,
        )

        plugin_payload = attr.asdict(plugin_info)

        # Patching with pluginInfo from settings
        for key, value in self.pluginInfo.items():
            plugin_payload[key] = value

        return plugin_payload

    def process(self, instance):
        output_dir = "C:/tmp"
        instance.data["outputDir"] = output_dir

        super(BlenderSubmitDeadline, self).process(instance)

        # TODO: Avoid the need for this logic here, needed for submit publish
        # Store output dir for unified publisher (filesequence)
        # output_dir = os.path.dirname(instance.data["expectedFiles"][0])
