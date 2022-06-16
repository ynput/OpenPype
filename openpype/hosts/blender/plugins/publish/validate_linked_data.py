import os
import subprocess
from typing import List
from bson.objectid import ObjectId

import bpy
import pyblish.api

from openpype.pipeline import legacy_io, update_container
from openpype.api import ValidateContentsOrder
from openpype.hosts.blender.api.pipeline import SCRIPTS_PATH, AVALON_PROPERTY
from openpype.hosts.blender.api.plugin import is_container
from openpype.hosts.blender.api.action import SelectInvalidAction


BLENDER_BIN_PATH = bpy.app.binary_path
UPDATE_SCRIPT_PATH = os.path.join(SCRIPTS_PATH, "update_workfile_data.py")


class ExtractAndPublishNotLinked(pyblish.api.Action):
    """Select invalid objects in Blender when a publish plug-in failed."""

    label = "Extract And Publish Not Linked"
    on = "failed"
    icon = "reply"

    def process(self, context, plugin):

        local_collections = set()
        for result in context.data["results"]:
            if result["error"]:
                instance = result["instance"]
                local_collections.update(
                    instance.data.get("local_collections", [])
                )

        for collection in local_collections:
            container = collection[AVALON_PROPERTY]
            # Get blender source workfile path for representation.
            representation = legacy_io.find_one(
                {"_id": ObjectId(container["representation"])}
            )
            parent = legacy_io.find_one(
                {"_id": ObjectId(representation["parent"])}
            )
            work_filepath = str(parent["data"]["source"]).replace(
                "{root[work]}",
                representation["context"]["root"]["work"],
            )
            # Subprocess blender command.
            command = [
                f'"{BLENDER_BIN_PATH}"',
                "--background",
                "--python-use-system-env",
                "--python",
                f'"{UPDATE_SCRIPT_PATH}"',
                "--",
                f'"{work_filepath}"',
                f'"{bpy.data.filepath}"',
                f'"{collection.name}"',
                "--publish",
            ]
            self.log.debug(" ".join(command))
            self.log.info(f"Extract {collection.name} ..")
            p = subprocess.Popen(
                " ".join(command),
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
            for stdout_line in iter(p.stdout.readline, ""):
                if stdout_line.strip():
                    print(stdout_line.rstrip())
            p.stdout.close()
            returncode = p.wait()
            if returncode:
                raise subprocess.CalledProcessError(returncode, command)

            self.log.info(f"Updating {collection.name} ..")
            update_container(container, -1)


class ValidateLinkedData(pyblish.api.InstancePlugin):
    """Validate that containers are linked with valid library."""

    order = ValidateContentsOrder - 0.01
    hosts = ["blender"]
    families = ["rig"]
    category = "geometry"
    label = "Validate Linked Data"
    actions = [SelectInvalidAction, ExtractAndPublishNotLinked]
    optional = True

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []

        for member in set(instance):
            if (
                is_container(member, "model")
                and isinstance(member, bpy.types.Collection)
            ):
                for obj in member.all_objects:
                    if (
                        not obj.library
                        and not obj.override_library
                    ) or (
                        not obj.data.library
                        and not obj.data.override_library
                    ):
                        invalid.append(member)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            instance.data["local_collections"] = invalid
            raise RuntimeError(
                f"following linked containers have local data: {invalid} "
                "See Action of this Validate"
            )
