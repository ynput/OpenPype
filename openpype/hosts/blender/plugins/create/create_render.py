"""Create render."""
import bpy

from openpype.pipeline import get_current_task_name
from openpype.hosts.blender.api import plugin, lib
from openpype.hosts.blender.api.render_lib import prepare_rendering
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateRenderlayer(plugin.Creator):
    """Single baked camera"""

    name = "renderingMain"
    label = "Render"
    family = "render"
    icon = "eye"

    def process(self):
        # Get Instance Container or create it if it does not exist
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        if not instances:
            instances = bpy.data.collections.new(name=AVALON_INSTANCES)
            bpy.context.scene.collection.children.link(instances)

        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)
        asset_group = bpy.data.collections.new(name=name)

        try:
            instances.children.link(asset_group)
            self.data['task'] = get_current_task_name()
            lib.imprint(asset_group, self.data)

            prepare_rendering(asset_group)
        except Exception:
            # Remove the instance if there was an error
            bpy.data.collections.remove(asset_group)
            raise

        # TODO: this is undesiderable, but it's the only way to be sure that
        # the file is saved before the render starts.
        # Blender, by design, doesn't set the file as dirty if modifications
        # happen by script. So, when creating the instance and setting the
        # render settings, the file is not marked as dirty. This means that
        # there is the risk of sending to deadline a file without the right
        # settings. Even the validator to check that the file is saved will
        # detect the file as saved, even if it isn't. The only solution for
        # now it is to force the file to be saved.
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

        return asset_group
