"""Load a camera asset in Blender."""

from contextlib import contextmanager

from openpype.hosts.blender.api import plugin


class BlendCameraLoader(plugin.AssetLoader):
    """Load a camera from a .blend file.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["camera"]
    representations = ["blend"]

    label = "Link Camera"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_05"

    def _process(self, libpath, asset_group):
        self._load_blend(libpath, asset_group)

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
