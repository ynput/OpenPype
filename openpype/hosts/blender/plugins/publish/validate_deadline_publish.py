import os

import bpy

import pyblish.api
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.hosts.blender.api.render_lib import prepare_rendering


class ValidateDeadlinePublish(pyblish.api.InstancePlugin,
                              OptionalPyblishPluginMixin):
    """Validates Render File Directory is
    not the same in every submission
    """

    order = ValidateContentsOrder
    families = ["render"]
    hosts = ["blender"]
    label = "Validate Render Output for Deadline"
    optional = True
    actions = [RepairAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        tree = bpy.context.scene.node_tree
        output_type = "CompositorNodeOutputFile"
        output_node = None
        # Remove all output nodes that inlcude "AYON" in the name.
        # There should be only one.
        for node in tree.nodes:
            if node.bl_idname == output_type and "AYON" in node.name:
                output_node = node
                break
        if not output_node:
            raise PublishValidationError(
                "No output node found in the compositor tree."
            )
        filepath = bpy.data.filepath
        file = os.path.basename(filepath)
        filename, ext = os.path.splitext(file)
        if filename not in output_node.base_path:
            raise PublishValidationError(
                "Render output folder doesn't match the blender scene name! "
                "Use Repair action to fix the folder file path."
            )

    @classmethod
    def repair(cls, instance):
        container = instance.data["transientData"]["instance_node"]
        prepare_rendering(container)
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
        cls.log.debug("Reset the render output folder...")
