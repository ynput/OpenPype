# -*- coding: utf-8 -*-
from openpype.pipeline import CreatorError
from openpype.hosts.unreal.api.pipeline import (
    send_request,
)
from openpype.hosts.unreal.api.plugin import (
    UnrealAssetCreator,
)


class CreateCamera(UnrealAssetCreator):
    """Create Camera."""

    identifier = "io.ayon.creators.unreal.camera"
    label = "Camera"
    family = "camera"
    icon = "fa.camera"

    def create(self, subset_name, instance_data, pre_create_data):
        if pre_create_data.get("use_selection"):
            selection = send_request("get_selected_assets")

            if len(selection) != 1:
                raise CreatorError("Please select only one object.")

        # Add the current level path to the metadata
        instance_data["level"] = send_request("get_editor_world")

        super(CreateCamera, self).create(
            subset_name,
            instance_data,
            pre_create_data)
