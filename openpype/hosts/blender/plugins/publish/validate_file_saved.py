import bpy

import pyblish.api


class ValidateFileSaved(pyblish.api.InstancePlugin):
    """Validate that the workfile has been saved."""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    label = "Validate File Saved"
    optional = False
    exclude_families = []

    def process(self, instance):
        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return
        if bpy.data.is_dirty:
            raise RuntimeError("Workfile is not saved.")
