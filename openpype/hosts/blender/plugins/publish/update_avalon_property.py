import pyblish.api
import bpy
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.workio import save_file
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
    AVALON_CONTAINER_ID,
)
from avalon import io


class UpdateAvalonProperty(pyblish.api.InstancePlugin):
    """Update Avalon Property with representation"""

    order = pyblish.api.IntegratorOrder + 0.05
    label = "Update Avalon Property"
    optional = False
    hosts = ["blender"]
    families = ["animation", "model", "rig", "action", "layout"]

    def process(self, instance):

        from openpype.lib import version_up

        libpath = ""
        # Get representation from the db
        representation = io.find_one(
            {
                "context.asset": instance.data["anatomyData"]["asset"],
                "context.family": instance.data["anatomyData"]["family"],
                "context.version": int(instance.data["anatomyData"]["version"]),
                "context.ext": "blend",
            }
        )
        # Get the avalon container in the scene
        container_collection = None
        instances = plugin.get_instances_list()
        for data_collection in instances:
            if data_collection.override_library is None:
                container_collection = data_collection

        # Set the avalon property with the representation data
        container_collection[AVALON_PROPERTY] = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            # "original_container_name": self.original_container_name,
            "name": str(representation["context"]["asset"]),
            "namespace": str(representation["context"]["asset"]),
            "loader": str(self.__class__.__name__),
            "representation": str(representation["_id"]),
            "libpath": str(representation["data"]["path"]),
            "asset_name": str(representation["context"]["asset"]),
            "parent": str(representation["parent"]),
            "family": str(representation["context"]["family"]),
            "objectName": container_collection.name,
        }
        # Get the filepath of the publish
        filepath = str(representation["data"]["path"])

        # Get the filepath of the publish
        save_file(filepath, copy=False)

        # Overwrite the publish file
        self.log.info(" %s updated.", filepath)
