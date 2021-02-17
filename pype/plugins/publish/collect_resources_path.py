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


class CollectResourcesPath(pyblish.api.InstancePlugin):
    """Generate directory path where the files and resources will be stored"""

    label = "Collect Resources Path"
    order = pyblish.api.CollectorOrder + 0.495
    families = ["workfile",
                "pointcache",
                "camera",
                "animation",
                "model",
                "mayaAscii",
                "setdress",
                "layout",
                "ass",
                "vdbcache",
                "scene",
                "vrayproxy",
                "render",
                "prerender",
                "imagesequence",
                "rendersetup",
                "rig",
                "plate",
                "look",
                "lut",
                "yetiRig",
                "yeticache",
                "nukenodes",
                "gizmo",
                "source",
                "matchmove",
                "image",
                "source",
                "assembly",
                "fbx",
                "textures",
                "action",
                "background"
                ]

    def process(self, instance):
        anatomy = instance.context.data["anatomy"]

        template_data = copy.deepcopy(instance.data["anatomyData"])

        # This is for cases of Deprecated anatomy without `folder`
        # TODO remove when all clients have solved this issue
        template_data.update({
            "frame": "FRAME_TEMP",
            "representation": "TEMP"
        })

        anatomy_filled = anatomy.format(template_data)

        if "folder" in anatomy.templates["publish"]:
            publish_folder = anatomy_filled["publish"]["folder"]
        else:
            # solve deprecated situation when `folder` key is not underneath
            # `publish` anatomy
            project_name = api.Session["AVALON_PROJECT"]
            self.log.warning((
                "Deprecation warning: Anatomy does not have set `folder`"
                " key underneath `publish` (in global of for project `{}`)."
            ).format(project_name))

            file_path = anatomy_filled["publish"]["path"]
            # Directory
            publish_folder = os.path.dirname(file_path)

        publish_folder = os.path.normpath(publish_folder)
        resources_folder = os.path.join(publish_folder, "resources")

        instance.data["publishDir"] = publish_folder
        instance.data["resourcesDir"] = resources_folder

        self.log.debug("publishDir: \"{}\"".format(publish_folder))
        self.log.debug("resourcesDir: \"{}\"".format(resources_folder))
