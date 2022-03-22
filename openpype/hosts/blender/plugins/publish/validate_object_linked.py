import os
import bpy
import platform
import subprocess
from avalon import io, api
import openpype.api

from openpype.lib import version_up
from openpype.hosts.blender.api.workio import save_file
from openpype.hosts.blender.api.pipeline import (
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api.plugin import is_local_collection


import pyblish.api
import openpype.hosts.blender.api.action
from typing import List
from openpype.api import get_errored_instances_from_context


class ExtractAndPublishNotLinked(pyblish.api.Action):
    """Select invalid objects in Blender when a publish plug-in failed."""

    label = "Extract And Publish Not Linked"
    on = "failed"
    icon = "search"

    def process(self, context, plugin):
        scene = bpy.data.scenes["Scene"]
        # Get the local instances
        local_instances_list = list()
        for collection in bpy.data.collections:
            if True or collection.override_library is not None:

                if collection.get(AVALON_PROPERTY):
                    avalon_dict = collection.get(AVALON_PROPERTY)
                    if (
                        avalon_dict.get("id") == AVALON_CONTAINER_ID
                        and avalon_dict.get("family") == "model"
                    ):
                        if is_local_collection(collection):
                            local_instances_list.append(collection)

        for collection in local_instances_list:
            representation = io.find_one(
                {"_id": io.ObjectId(collection[AVALON_PROPERTY]["parent"])}
            )

            work_path = context.data["projectEntity"]["config"]["roots"][
                "work"
            ]["windows"]
            # script_path = os.path.abspath(
            #     openpype.hosts.blender.plugins.publish.extract_local_instance_standalone.__file__
            # )
            script_path = "D:/Users/Dimitri/Documents/Dev_dimitri/OpenPype/openpype/hosts/blender/plugins/publish/extract_local_instance_standalone.py"
            filepath = str(representation["data"]["source"]).replace(
                "{root[work]}", work_path
            )
            output = version_up(filepath)
            blender_binary_path = bpy.app.binary_path
            command = r'"%s" --python "%s" -- %s %s %s ' % (
                blender_binary_path,
                script_path,
                bpy.data.filepath,
                output,
                collection.name,
            )
            self.log.info(command)
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            self.log.info(p)
            p.stdout.close()
            p.wait()
            api.update(collection[AVALON_PROPERTY], -1)


class ValidateObjectLinked(pyblish.api.InstancePlugin):
    """Validate that the objects are linked."""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["rig"]
    category = "geometry"
    label = "Validate Object Link"
    actions = [ExtractAndPublishNotLinked]
    optional = True

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []

        scene = bpy.data.scenes["Scene"]

        # Get the local instances
        local_instances_list = list()
        for collection in bpy.data.collections:
            if True or collection.override_library is not None:

                if collection.get("avalon"):
                    avalon_dict = collection.get("avalon")
                    if (
                        avalon_dict.get("id") == AVALON_CONTAINER_ID
                        and avalon_dict.get("family") == "model"
                    ):
                        if is_local_collection(collection):
                            local_instances_list.append(collection)
                            invalid.append(collection)
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                f"Container found in instance is not linked: {invalid}"
            )
