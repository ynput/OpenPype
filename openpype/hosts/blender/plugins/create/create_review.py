"""Create review."""

from openpype.pipeline import CreatedInstance
from openpype.hosts.blender.api import plugin, lib, ops


class CreateReview(plugin.BaseCreator):
    """Single baked camera"""

    identifier = "io.openpype.creators.blender.review"
    name = "reviewDefault"
    label = "Review"
    family = "review"
    icon = "video-camera"

    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        """ Run the creator on Blender main thread"""
        self._add_instance_to_context(
            CreatedInstance(self.family, subset_name, instance_data, self)
        )

        mti = ops.MainThreadItem(
            self._process, subset_name, instance_data, pre_create_data
        )
        ops.execute_in_main_thread(mti)

    def _process(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
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
