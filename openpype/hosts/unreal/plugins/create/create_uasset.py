# -*- coding: utf-8 -*-
from pathlib import Path

from openpype.pipeline import CreatorError
from openpype.hosts.unreal.api.pipeline import (
    send_request,
)
from openpype.hosts.unreal.api.plugin import (
    UnrealAssetCreator,
)


class CreateUAsset(UnrealAssetCreator):
    """Create UAsset."""

    identifier = "io.ayon.creators.unreal.uasset"
    label = "UAsset"
    family = "uasset"
    icon = "cube"

    extension = ".uasset"

    def create(self, subset_name, instance_data, pre_create_data):
        if pre_create_data.get("use_selection"):
            selection = send_request("get_selected_assets")

            if len(selection) != 1:
                raise CreatorError("Please select only one object.")

            obj = selection[0]

            sys_path = send_request(
                "get_system_path", params={"asset_path": obj})

            if not sys_path:
                raise CreatorError(
                    f"{Path(obj).name} is not on the disk. Likely it needs to"
                    "be saved first.")

            if Path(sys_path).suffix != self.extension:
                raise CreatorError(
                    f"{Path(sys_path).name} is not a {self.label}.")

        super(CreateUAsset, self).create(
            subset_name,
            instance_data,
            pre_create_data)


class CreateUMap(CreateUAsset):
    """Create Level."""

    identifier = "io.ayon.creators.unreal.umap"
    label = "Level"
    family = "uasset"
    extension = ".umap"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data["families"] = ["umap"]

        super(CreateUMap, self).create(
            subset_name,
            instance_data,
            pre_create_data)
