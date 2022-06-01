"""Load a layout in Blender."""

import json
from pathlib import Path
from typing import Dict, Optional

import bpy

from openpype.pipeline import (
    discover_loader_plugins,
    load_container,
    loaders_from_representation,
)
from openpype.hosts.blender.api import plugin


class JsonLayoutLoader(plugin.AssetLoader):
    """Load layout published from Unreal."""

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_02"

    def _get_loader(self, loaders, family):
        name = ""
        if family == 'rig':
            name = "BlendRigLoader"
        elif family == 'model':
            name = "BlendModelLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    def _process(self, libpath, asset_group, context=None):
        plugin.deselect_all()

        with open(libpath, "r") as fp:
            data = json.load(fp)

        all_loaders = discover_loader_plugins()

        for element in data:
            reference = element.get("reference")
            family = element.get("family")

            loaders = loaders_from_representation(all_loaders, reference)
            loader = self._get_loader(loaders, family)

            if not loader:
                continue

            options = {
                "parent": asset_group,
                "transform": element.get("transform"),
            }

            if element.get("animation"):
                options["animation_file"] = "{}.{}".format(
                    Path(libpath).with_suffix(""),
                    element.get("animation"),
                )

            # This should return the loaded asset, but the load call will be
            # added to the queue to run in the Blender main thread, so
            # at this time it will not return anything. The assets will be
            # loaded in the next Blender cycle, so we use the options to
            # set the transform, parent and assign the action, if there is one.
            load_container(
                loader,
                reference,
                namespace=element.get("namespace"),
                options=options
            )

        # Camera creation when loading a layout is not necessary for now,
        # but the code is worth keeping in case we need it in the future.
        # # Create the camera asset and the camera instance
        # creator_plugin = lib.get_creator_by_name("CreateCamera")
        # if not creator_plugin:
        #     raise ValueError("Creator plugin \"CreateCamera\" was "
        #                      "not found.")

        # legacy_create(
        #     creator_plugin,
        #     name="camera",
        #     # name=f"{unique_number}_{subset}_animation",
        #     asset=asset,
        #     options={"useSelection": False}
        #     # data={"dependencies": str(context["representation"]["_id"])}
        # )

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> bpy.types.Collection:
        """Asset loading Process"""
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        unique_number = plugin.get_unique_number(asset, subset)
        group_name = plugin.asset_name(asset, subset, unique_number)
        namespace = namespace or asset

        asset_group = bpy.data.collections.new(group_name)
        asset_group.color_tag = self.color_tag
        plugin.get_main_collection().children.link(asset_group)

        self._process(libpath, asset_group, context)

        self._update_metadata(
            asset_group,
            context,
            name,
            namespace or f"{asset}_{unique_number}",
            plugin.asset_name(asset, subset),
            libpath
        )

        self[:] = list(asset_group.all_objects)
        return asset_group

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        self._update_process(container, representation)

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)
