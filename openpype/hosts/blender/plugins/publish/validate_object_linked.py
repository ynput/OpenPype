import bpy
import subprocess
from bson.objectid import ObjectId
import os
import platform

import pyblish.api
from typing import List

from openpype.pipeline import (
    legacy_io,
    update_container,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.utility_scripts import update_container_data


SYSTEM = platform.system().lower()
BLENDER_BIN_PATH = bpy.app.binary_path
UPDATE_SCRIPT_PATH = os.path.abspath(update_container_data.__file__)


class ExtractAndPublishNotLinked(pyblish.api.Action):
    """Select invalid objects in Blender when a publish plug-in failed."""

    label = "Extract And Publish Not Linked"
    on = "failed"
    icon = "search"

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
            ]
            self.log.debug(" ".join(command))
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

        for obj in set(instance):
            if isinstance(obj, bpy.types.Collection):
                metadata = obj.get(AVALON_PROPERTY)
                if (
                    metadata and
                    metadata.get("id") == AVALON_CONTAINER_ID and
                    metadata.get("family") == "model"
                ):
                    for o in obj.all_objects:
                        if not o.library and not o.override_library:
                            invalid.append(obj)
                            break
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            instance.data["local_collections"] = invalid
            raise RuntimeError(
                f"Container contain local parts: {invalid} "
                f"See Action of this Validate"
            )
