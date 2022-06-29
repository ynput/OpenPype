"""Create an animation asset."""

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.lib import get_selection


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"
    color_tag = "COLOR_01"

    def _use_selection(self, container):
        selected_objects = set(get_selection())
        # Get rig collections from selected objects.
        selected_collections = set()
        for obj in list(selected_objects):
            for collection in obj.users_collection:
                if plugin.is_container(collection, "rig"):
                    selected_collections.add(collection)
                    selected_objects.remove(obj)

        plugin.link_to_collection(selected_collections, container)
        plugin.link_to_collection(selected_objects, container)

    def _process(self):
        # Get Instance Container
        container = super()._process()

        if (self.options or {}).get("asset_groups"):
            asset_groups = set(self.options["asset_groups"])
            plugin.link_to_collection(asset_groups, container)

        return container
