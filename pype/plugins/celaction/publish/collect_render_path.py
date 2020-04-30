"""
Requires:
    context     -> anatomy
    context     -> anatomyData

Provides:
    instance    -> publishDir
    instance    -> resourcesDir
"""

import os
import copy

import pyblish.api
from avalon import api


class CollectRenderPath(pyblish.api.InstancePlugin):
    """Generate file and directory path where rendered images will be"""

    label = "Collect Render Path"
    order = pyblish.api.CollectorOrder + 0.495

    def process(self, instance):
        anatomy = instance.context.data["anatomy"]

        template_data = copy.deepcopy(instance.data["anatomyData"])

        # This is for cases of Deprecated anatomy without `folder`
        # TODO remove when all clients have solved this issue
        template_data.update({
            "frame": "FRAME_TEMP",
            "representation": "png"
        })

        anatomy_filled = anatomy.format(template_data)

        if "folder" in anatomy.templates["render"]:
            render_folder = anatomy_filled["render"]["folder"]
            render_file = anatomy_filled["render"]["file"]
        else:
            # solve deprecated situation when `folder` key is not underneath
            # `publish` anatomy
            project_name = api.Session["AVALON_PROJECT"]
            self.log.warning((
                "Deprecation warning: Anatomy does not have set `folder`"
                " key underneath `publish` (in global of for project `{}`)."
            ).format(project_name))

            file_path = anatomy_filled["render"]["path"]
            # Directory
            render_folder = os.path.dirname(file_path)
            render_file = os.path.basename(file_path)

        render_folder = os.path.normpath(render_folder)
        render_path = os.path.join(render_folder, render_file)

        instance.data["outputRenderPath"] = render_path

        self.log.debug("outputRenderPath: \"{}\"".format(render_path))
