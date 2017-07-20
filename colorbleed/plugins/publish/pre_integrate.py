import os
import logging
import shutil

import maya.cmds as cmds

import pyblish.api

log = logging.getLogger(__name__)


class PostIntegrateAsset(pyblish.api.InstancePlugin):
    """Resolve any dependency issies

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.
    """

    label = "Post Intergrate Asset"
    order = pyblish.api.IntegratorOrder + 0.1
    families = ["colorbleed.lookdev", "colorbleed.texture"]

    def process(self, instance):

        # get needed variables
        version_folder = instance.data["versionFolder"]
        family = instance.data["family"]
        resources = instance.data("resources", [])

        self.log.info("Running post process for {}".format(instance.name))

        if family == "colorbleed.texture":
            texture_folder = os.path.join(version_folder, "textures")
            self.remap_resource_nodes(resources, folder=texture_folder)

        elif family == "colorbleed.lookdev":
            self.remap_resource_nodes(resources)

        # self.log.info("Removing temporary files and folders ...")
        # if passed:
        #     stagingdir = instance.data["stagingDir"]
        #     shutil.rmtree(stagingdir)

    def remap_resource_nodes(self, resources, folder=None):

        self.log.info("Updating resource nodes ...")
        for resource in resources:
            source = resource["source"]
            if folder:
                fname = os.path.basename(source)
                fpath = os.path.join(folder, fname)
            else:
                fpath = source

            node_attr = resource["attribute"]
            print("UPDATING {} -> {}".format(node_attr, fpath))
            cmds.setAttr(node_attr, fpath, type="string")

        self.log.info("Saving file ...")

        cmds.file(save=True, type="mayaAscii")

    def remap_yeti_resource_nodes(self, node,):
        pass
