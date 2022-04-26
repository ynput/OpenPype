"""Create a model asset."""

from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import plugin, lib, ops


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
        asset_group = bpy.data.objects.new(name=name, object_data=None)
        asset_group.empty_display_type = 'SINGLE_ARROW'
        instances.objects.link(asset_group)
        self.data['task'] = legacy_io.Session.get('AVALON_TASK')
        lib.imprint(asset_group, self.data)

        # Create the container
        container = plugin.create_container(name)
        if container is None:
            raise RuntimeError(f"This instance already exists: {name}")

        # Add custom property on the instance container with the data
        self.data["task"] = api.Session.get("AVALON_TASK")
        lib.imprint(container, self.data)

        # Add selected objects to container
        if (self.options or {}).get("useSelection"):
            # if has no selected object ask for adding all scene content
            selected = lib.get_selection()
            plugin.link_to_collection(selected, container)

        return container
