"""Load a layout in Blender."""

import json
from pathlib import Path

from openpype.pipeline import (
    discover_loader_plugins,
    load_container,
    loaders_from_representation,
)
from openpype.hosts.blender.api import plugin


class JsonLayoutLoader(plugin.AssetLoader):
    """Load layout from a .json file."""

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout"
    icon = "download"
    color = "orange"
    color_tag = "COLOR_02"
    order = 4

    def _get_loader(self, loaders, family):
        name = ""
        if family == "rig":
            name = "LinkRigLoader"
        elif family == "model":
            name = "LinkModelLoader"
        else:
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

    def _load_process(self, libpath, container_name):  # TODO
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
        # creator_plugin = get_legacy_creator_by_name("CreateCamera")
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
