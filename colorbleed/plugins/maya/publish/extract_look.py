import os
import json

from maya import cmds

import avalon.maya
import colorbleed.api

import cb.utils.maya.context as context


class ExtractLook(colorbleed.api.Extractor):
    """Extract Look (Maya Ascii + JSON)

    Only extracts the sets (shadingEngines and alike) alongside a .json file
    that stores it relationships for the sets and "attribute" data for the
    instance members.

    """

    label = "Look (Maya ASCII + JSON)"
    hosts = ["maya"]
    families = ["colorbleed.look"]

    def process(self, instance):

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        maya_fname = "{0}.ma".format(instance.name)
        json_fname = "{0}.json".format(instance.name)

        maya_path = os.path.join(dir_path, maya_fname)
        json_path = os.path.join(dir_path, json_fname)

        self.log.info("Performing extraction..")

        # Remove all members of the sets so they are not included in the
        # exported file by accident
        self.log.info("Extract sets (Maya ASCII)..")
        lookdata = instance.data["lookData"]
        sets = lookdata["sets"]

        # Define the texture file node remapping
        resource_remap = dict()
        # required tags to be a look resource
        required_tags = ["maya", "attribute", "look"]
        resources = instance.data.get("resources", [])
        for resource in resources:
            resource_tags = resource.get("tags", [])
            if all(tag in resource_tags for tag in required_tags):
                node = resource['node']
                destination = resource['destination']
                resource_remap["{}.fileTextureName".format(node)] = destination

        # Extract in corect render layer
        layer = instance.data.get("renderlayer", "defaultRenderLayer")
        with context.renderlayer(layer):
            # TODO: Ensure membership edits don't become renderlayer overrides
            with context.empty_sets(sets):
                with context.attribute_values(resource_remap):
                    with avalon.maya.maintained_selection():
                        cmds.select(sets, noExpand=True)
                        cmds.file(maya_path,
                                  force=True,
                                  typ="mayaAscii",
                                  exportSelected=True,
                                  preserveReferences=False,
                                  channels=True,
                                  constraints=True,
                                  expressions=True,
                                  constructionHistory=True)

        # Write the JSON data
        self.log.info("Extract json..")
        data = {"attributes": lookdata["attributes"],
                "sets": lookdata["relationships"]}
        with open(json_path, "w") as f:
            json.dump(data, f)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          maya_path))
