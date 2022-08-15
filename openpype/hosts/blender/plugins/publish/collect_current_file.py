import os
import bpy

import pyblish.api
from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import workio


class SaveWorkfiledAction(pyblish.api.Action):
    """Save Workfile."""
    label = "Save Workfile"
    on = "failed"
    icon = "save"

    def process(self, context, plugin):
        current_file = workio.current_file()
        if current_file:
            workio.save_file(current_file)
        else:
            bpy.ops.wm.avalon_workfiles()


class CollectBlenderCurrentFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.5
    label = "Blender Current File"
    hosts = ["blender"]
    actions = [SaveWorkfiledAction]

    def process(self, context):
        """Inject the current working file"""
        current_file = workio.current_file()
        has_unsaved_changes = workio.has_unsaved_changes()

        context.data["currentFile"] = current_file

        assert current_file, (
            "Current file is empty. Save the file before continuing."
        )

        assert not has_unsaved_changes, (
            "Current file has unsaved changes. "
            "Save the file before continuing."
        )

        folder, file = os.path.split(current_file)
        filename, ext = os.path.splitext(file)

        task = legacy_io.Session["AVALON_TASK"]

        data = {}

        # create instance
        instance = context.create_instance(name=filename)
        subset = "workfile" + task.capitalize()

        data.update({
            "subset": subset,
            "asset": os.getenv("AVALON_ASSET", None),
            "label": subset,
            "publish": True,
            "family": "workfile",
            "families": ["workfile"],
            "setMembers": [current_file],
            "frameStart": bpy.context.scene.frame_start,
            "frameEnd": bpy.context.scene.frame_end,
        })

        data["representations"] = [{
            "name": ext.lstrip("."),
            "ext": ext.lstrip("."),
            "files": file,
            "stagingDir": folder,
        }]

        instance.data.update(data)

        self.log.info("Collected instance: {}".format(file))
        self.log.info("Scene path: {}".format(current_file))
        self.log.info("staging Dir: {}".format(folder))
        self.log.info("subset: {}".format(subset))
