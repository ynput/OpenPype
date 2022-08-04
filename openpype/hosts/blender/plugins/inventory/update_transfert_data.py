from openpype.pipeline import InventoryAction, legacy_io, update_container

import bpy

from openpype.hosts.blender.api.pipeline import MODEL_DOWNSTREAM
from openpype.hosts.blender.api.ops import _process_app_events
from openpype.hosts.blender.api.plugin import (
    ContainerMaintainer,
    get_children_recursive,
)


class UpdateTransfertData(InventoryAction):

    label = "Update with local data transfert"
    icon = "angle-double-up"
    color = "#bbdd00"

    @staticmethod
    def is_compatible(container):
        return (
            container.get("loader") in ("LinkModelLoader", "AppendModelLoader")
            and legacy_io.Session.get("AVALON_TASK") in MODEL_DOWNSTREAM
        )

    def process(self, containers):

        current_task = legacy_io.Session.get("AVALON_TASK")
        collections = get_children_recursive(bpy.context.scene.collection)

        maintained_params = []
        if current_task == "Rigging":
            maintained_params.append(
                ["local_data", {"data_types": ["VGROUP_WEIGHTS"]}]
            )

        for container in containers:

            object_name = container["objectName"]
            container_collection = None
            for collection in collections:
                if collection.name == object_name:
                    container_collection = collection
                    break
            else:
                container_collection = bpy.data.collections.get(object_name)

            if not container_collection:
                continue

            with ContainerMaintainer(container_collection, maintained_params):
                mti = update_container(container, -1)
                # NOTE (kaamaurice): I try mti.wait() but seems to stop the
                # bpy.app.timers
                while not mti.done:
                    _process_app_events()
