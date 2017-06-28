import os

from maya import cmds

import avalon.maya
import colorbleed.api

import cb.utils.maya.context as context


class ExtractFurYeti(colorbleed.api.Extractor):
    """Extract as Yeti nodes"""

    label = "Yeti Nodes"
    hosts = ["maya"]
    families = ["colorbleed.groom"]

    def process(self, instance):

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.ma".format(instance.name)
        path = os.path.join(dir_path, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        # Get only the shape contents we need in such a way that we avoid
        # taking along intermediateObjects
        members = instance.data("setMembers")
        members = cmds.ls(members,
                          dag=True,
                          shapes=True,
                          type="pgYetiMaya",
                          noIntermediate=True,
                          long=True)

        # Remap cache files names and ensure fileMode is set to load from cache
        resource_remap = dict()
        # required tags to be a yeti resource
        required_tags = ["maya", "yeti", "attribute"]
        resources = instance.data.get("resources", [])
        for resource in resources:
            resource_tags = resource.get("tags", [])
            if all(tag in resource_tags for tag in required_tags):
                attribute = resource['attribute']
                destination = resource['destination']
                resource_remap[attribute] = destination

        # Perform extraction
        with avalon.maya.maintained_selection():
            with context.attribute_values(resource_remap):
                cmds.select(members, r=True, noExpand=True)
                cmds.file(path,
                          force=True,
                          typ="mayaAscii",
                          exportSelected=True,
                          preserveReferences=False,
                          constructionHistory=False,
                          shader=False)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, path))
