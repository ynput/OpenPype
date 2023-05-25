# -*- coding: utf-8 -*-
from pathlib import Path

import unreal

from openpype.pipeline import CreatorError
from openpype.hosts.unreal.api.plugin import (
    UnrealAssetCreator,
)


class CreateUAsset(UnrealAssetCreator):
    """Create UAsset."""

    identifier = "io.ayon.creators.unreal.uasset"
    label = "UAsset"
    family = "uasset"
    icon = "cube"

    def create(self, subset_name, instance_data, pre_create_data):
        if pre_create_data.get("use_selection"):
            ar = unreal.AssetRegistryHelpers.get_asset_registry()

            sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
            selection = [a.get_path_name() for a in sel_objects]

            if len(selection) != 1:
                raise CreatorError("Please select only one object.")

            obj = selection[0]

            asset = ar.get_asset_by_object_path(obj).get_asset()
            sys_path = unreal.SystemLibrary.get_system_path(asset)

            if not sys_path:
                raise CreatorError(
                    f"{Path(obj).name} is not on the disk. Likely it needs to"
                    "be saved first.")

            if Path(sys_path).suffix != ".uasset":
                raise CreatorError(f"{Path(sys_path).name} is not a UAsset.")

        super(CreateUAsset, self).create(
            subset_name,
            instance_data,
            pre_create_data)
