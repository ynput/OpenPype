"""Create an animation asset."""

from openpype.hosts.blender.api import plugin, lib


class CreateAnimation(plugin.BaseCreator):
    """Animation output for character rigs."""

    identifier = "io.openpype.creators.blender.animation"
    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"

    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        """Run the creator on Blender main thread."""
        # Run parent create method
        collection = super().create(
            subset_name, instance_data, pre_create_data
        )

        if pre_create_data.get("use_selection"):
            selected = lib.get_selection()
            for obj in selected:
                collection.objects.link(obj)
        elif pre_create_data.get("asset_group"):
            obj = (self.options or {}).get("asset_group")
            collection.objects.link(obj)

        return collection
