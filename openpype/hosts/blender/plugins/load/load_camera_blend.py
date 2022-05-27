"""Load a camera asset in Blender."""

from typing import Dict
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

    def _process(self, libpath, asset_group, *args, **kwargs):
        return self._load_blend(libpath, asset_group)

    def process_asset(
        self, context: dict, *args, **kwargs
    ) -> bpy.types.Collection:
        """Asset loading Process"""
        asset_group = super().process_asset(context, *args, **kwargs)
        asset_group.color_tag = self.color_tag
        return asset_group

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        self._update_process(container, representation)

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
