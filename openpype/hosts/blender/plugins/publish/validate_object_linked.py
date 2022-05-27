import os
import platform
import subprocess
from typing import List
from bson.objectid import ObjectId

import bpy
import pyblish.api

from openpype.pipeline import (
    legacy_io,
    update_container,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api.plugin import AssetLoader
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.hosts.blender.api.action import SelectInvalidAction
from openpype.hosts.blender.utility_scripts import update_workfile_data


SYSTEM = platform.system().lower()
BLENDER_BIN_PATH = bpy.app.binary_path
UPDATE_SCRIPT_PATH = os.path.abspath(update_workfile_data.__file__)


class UpdateContainer(pyblish.api.Action):
    """Select invalid objects in Blender when a publish plug-in failed."""

    label = "Update With Last Representations"
    on = "failed"
    icon = "refresh"

    def process(self, context, plugin):

        data_type = []
        if legacy_io.Session.get("AVALON_TASK") == "Rigging":
            data_type = ["VGROUP_WEIGHTS"]

        out_to_date_collections = set()
        for result in context.data["results"]:
            if result["error"]:
                instance = result["instance"]
                out_to_date_collections.update(
                    instance.data.get("out_to_date_collections", [])
                )

        for collection in out_to_date_collections:
            self.log.info(f"Updating {collection.name} ..")
            with AssetLoader.maintained_local_data(collection, data_type):
                update_container(collection[AVALON_PROPERTY], -1)


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


class ValidateContainerLibrary(pyblish.api.InstancePlugin):
    """Validate that containers are linked with valid library."""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["rig"]
    category = "geometry"
    label = "Validate Container Library"
    actions = [SelectInvalidAction]
    optional = False

    @staticmethod
    def get_out_to_date(instance) -> List:
        invalid = []

        for obj in set(instance):
            if (
                isinstance(obj, bpy.types.Collection)
                and not obj.library
                and not obj.override_library
                and obj.get(AVALON_PROPERTY)
                and obj[AVALON_PROPERTY].get("id") == AVALON_CONTAINER_ID
            ):
                if not AssetLoader.is_updated(obj):
                    invalid.append(obj)

        return invalid

    @staticmethod
    def get_local_data(instance) -> List:
        invalid = []

        for obj in set(instance):
            if (
                isinstance(obj, bpy.types.Collection)
                and obj.get(AVALON_PROPERTY)
                and obj[AVALON_PROPERTY].get("id") == AVALON_CONTAINER_ID
            ):
                for o in obj.all_objects:
                    if (
                        (not o.library and not o.override_library)
                        or (not o.data.library and not o.data.override_library)
                    ):
                        invalid.append(o)
        return invalid

    @classmethod
    def get_invalid(cls, instance) -> List:
        invalid = []

        invalid += cls.get_out_to_date(instance)
        invalid += cls.get_local_data(instance)

        return invalid

    def process(self, instance):
        invalid = self.get_out_to_date(instance)
        if invalid:
            instance.data["out_to_date_collections"] = invalid
            self.actions.append(UpdateContainer)
            raise RuntimeError(
                f"Containers are out to date: {invalid} "
                f"See Action of this Validate"
            )

        invalid = self.get_local_data(instance)
        if invalid:
            instance.data["local_collections"] = invalid
            self.actions.append(ExtractAndPublishNotLinked)
            raise RuntimeError(
                f"Containers have local data: {invalid} "
                f"See Action of this Validate"
            )
