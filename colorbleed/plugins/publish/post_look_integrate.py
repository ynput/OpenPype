import json
import os


import colorbleed.maya.lib as lib

import pyblish.api


class IntegrateAsset(pyblish.api.InstancePlugin):
    """Remap source paths for lookdev and textures

    """

    label = "Remap source paths"
    order = pyblish.api.IntegratorOrder + 0.15
    families = ["colorbleed.lookdev",
                "colorbleed.texture"]

    def process(self, instance):

        family = instance.data['family']
        resources = instance.data['resources']
        version_folder = instance.data['versionFolder']

        if family == "colorbleed.texture":
            try:
                lib.remap_resource_nodes(resources, folder=version_folder)
            except Exception as e:
                self.log.error(e)

        if family == "colorbleed.lookdev":
            try:
                tmp_dir = lib.maya_temp_folder()
                resource_file = os.path.join(tmp_dir, "resources.json")
                with open(resource_file, "r") as f:
                    resources = json.load(f)
                lib.remap_resource_nodes(resources)
            except Exception as e:
                self.log.error(e)
