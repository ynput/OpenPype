import bpy

import pyblish.api

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError
)


class SaveWorkfileAction(pyblish.api.Action):
    """Save Workfile."""
    label = "Save Workfile"
    on = "failed"
    icon = "save"

    def process(self, context, plugin):
        bpy.ops.wm.avalon_workfiles()


class ValidateFileSaved(pyblish.api.InstancePlugin,
                        OptionalPyblishPluginMixin):
    """Validate that the workfile has been saved."""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    label = "Validate File Saved"
    optional = False
    exclude_families = []
    actions = [SaveWorkfileAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        if not instance.context.data["currentFile"]:
            # File has not been saved at all and has no filename
            raise PublishValidationError(
                "Current file is empty. Save the file before continuing."
            )

        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return
        if bpy.data.is_dirty:
            raise PublishValidationError("Workfile has unsaved changes.")
