"""Create review."""

from openpype.hosts.blender.api import plugin, lib


class CreateReview(plugin.BaseCreator):
    """Single baked camera."""

    identifier = "io.openpype.creators.blender.review"
    name = "reviewDefault"
    label = "Review"
    family = "review"
    icon = "video-camera"

    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        """Run the creator on Blender main thread."""
        # Run parent create method
        collection = super().create(
            subset_name, instance_data, pre_create_data
        )

        if pre_create_data.get("useSelection"):
            selected = lib.get_selection()
            for obj in selected:
                collection.objects.link(obj)
        elif pre_create_data.get("asset_group"):
            obj = (self.options or {}).get("asset_group")
            collection.objects.link(obj)

        return collection
