
from typing import List

import pyblish.api

from openpype.api import ValidateContentsOrder
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.action import UpdateContainer


class ValidateAssetsVersion(pyblish.api.InstancePlugin):
    """Validate that asset containers are up to date."""

    order = ValidateContentsOrder - 0.011
    hosts = ["blender"]
    families = ["model", "rig", "layout", "animation", "setdress"]
    category = "geometry"
    label = "Assets Version"
    actions = [UpdateContainer]
    optional = True

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []

        for obj in set(instance):
            if (
                plugin.is_container(obj)
                and not obj.library
                and not obj.override_library
            ):
                if not plugin.is_container_up_to_date(obj):
                    invalid.append(obj)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            instance.data["out_to_date_collections"] = invalid
            raise RuntimeError(
                f"following linked containers are out to date: {invalid} "
                "See Action of this Validate"
            )
