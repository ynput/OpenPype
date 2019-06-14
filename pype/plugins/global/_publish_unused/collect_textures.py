import os
import re
import copy
from avalon import io
from pprint import pprint

import pyblish.api
from avalon import api


texture_extensions = ['.tif', '.tiff', '.jpg', '.jpeg', '.tx', '.png', '.tga',
                      '.psd', '.dpx', '.hdr', '.hdri', '.exr', '.sxr', '.psb']


class CollectTextures(pyblish.api.ContextPlugin):
    """
    Gather all texture files in working directory, traversing whole structure.
    """

    order = pyblish.api.CollectorOrder
    targets = ["texture"]
    label = "Textures"
    hosts = ["shell"]

    def process(self, context):

        if os.environ.get("PYPE_PUBLISH_PATHS"):
            paths = os.environ["PYPE_PUBLISH_PATHS"].split(os.pathsep)
        else:
            cwd = context.get("workspaceDir", os.getcwd())
            paths = [cwd]

        textures = []
        for path in paths:
            for dir, subdir, files in os.walk(path):
                textures.extend(
                    os.path.join(dir, x) for x in files
                    if os.path.splitext(x)[1].lower() in texture_extensions)

        self.log.info("Got {} texture files.".format(len(textures)))
        if len(textures) < 1:
            raise RuntimeError("no textures found.")

        asset_name = os.environ.get("AVALON_ASSET")
        family = 'texture'
        subset = 'Main'

        project = io.find_one({'type': 'project'})
        asset = io.find_one({
            'type': 'asset',
            'name': asset_name
        })

        context.data['project'] = project
        context.data['asset'] = asset

        for tex in textures:
            self.log.info("Processing: {}".format(tex))
            name, ext = os.path.splitext(tex)
            simple_name = os.path.splitext(os.path.basename(tex))[0]
            instance = context.create_instance(simple_name)

            instance.data.update({
                "subset": subset,
                "asset": asset_name,
                "label": simple_name,
                "name": simple_name,
                "family": family,
                "families": [family, 'ftrack'],
            })
            instance.data['destination_list'] = list()
            instance.data['representations'] = list()
            instance.data['source'] = 'pype command'

            texture_data = {}
            texture_data['anatomy_template'] = 'texture'
            texture_data["ext"] = ext
            texture_data["label"] = simple_name
            texture_data["name"] = "texture"
            texture_data["stagingDir"] = os.path.dirname(tex)
            texture_data["files"] = os.path.basename(tex)
            texture_data["thumbnail"] = False
            texture_data["preview"] = False

            instance.data["representations"].append(texture_data)
            self.log.info("collected instance: {}".format(instance.data))

        self.log.info("All collected.")
