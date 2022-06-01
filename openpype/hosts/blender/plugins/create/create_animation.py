"""Create an animation asset."""

from openpype.hosts.blender.api import plugin


class CreateAnimation(plugin.Creator):
    """Animation output for character rigs"""

    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"
    color_tag = "COLOR_01"

    def _process(self):
        # Get Instance Container
        container = super()._process()

        if (self.options or {}).get("asset_groups"):
            for asset_group in self.options["asset_groups"]:
                container.children.link(asset_group)

        return container
