"""Create a model asset."""

from avalon import api
from openpype.hosts.blender.api import plugin, lib, ops

from openpype.hosts.blender.api.pluginplus import (
    link_objects_to_collection,
    create_container,
)


class CreateModel(plugin.Creator):
    """Polygonal static geometry"""

    name = "modelMain"
    label = "Model"
    family = "model"
    icon = "cube"

    def process(self):
        """Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):

        # Get info from data and create name value
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)

        # Create the container
        container = create_container(name)
        if container is None:
            return

        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # Add selected objects to container
        if (self.options or {}).get("useSelection"):
            # if has no selected object ask for adding all scene content
            selected = lib.get_selection()
            link_objects_to_collection(selected, container)

        return container
