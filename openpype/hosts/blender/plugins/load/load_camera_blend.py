"""Load a camera asset in Blender."""

from typing import Dict, List, Optional
from contextlib import contextmanager

import bpy

from openpype.hosts.blender.api import plugin


class BlendCameraLoader(plugin.AssetLoader):
    """Load a camera from a .blend file.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["camera"]
    representations = ["blend"]

    label = "Link Camera (Blend)"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_05"

    def process_asset(
        self, context: dict, name: str, namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Optional[List]:
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        asset_name = plugin.asset_name(asset, subset)

        asset_group = bpy.data.collections.new(asset_name)
        asset_group.color_tag = self.color_tag
        plugin.get_main_collection().children.link(asset_group)

        objects = self._load_blend(libpath, asset_group)

        self._update_metadata(
            asset_group, context, name, namespace, asset_name, libpath
        )

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        self._update_blend(container, representation)

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)

    @contextmanager
    def maintained_actions(self, container):
        """Maintain action during context."""
        # We always want the action from linked camera blend file.
        # So this overload do maintain nothing to force current action to be
        # overrided from linked file.
        # TODO (kaamaurice): Add a Pyblish Validator + Action to allow user to
        # update the camera action from an opened animation blend file.
        try:
            yield
        finally:
            pass
