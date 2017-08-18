import os
import json

from maya import cmds

import pyblish.api
import avalon.maya
import colorbleed.api

from cb.utils.maya import context


class ExtractLook(colorbleed.api.Extractor):
    """Extract Look (Maya Ascii + JSON)

    Only extracts the sets (shadingEngines and alike) alongside a .json file
    that stores it relationships for the sets and "attribute" data for the
    instance members.

    """

    label = "Extract Look (Maya ASCII + JSON)"
    hosts = ["maya"]
    families = ["colorbleed.lookdev"]
    order = pyblish.api.ExtractorOrder + 0.2

    def process(self, instance):

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        maya_fname = "{0}.ma".format(instance.name)
        json_fname = "{0}.json".format(instance.name)

        # Make texture dump folder
        maya_path = os.path.join(dir_path, maya_fname)
        json_path = os.path.join(dir_path, json_fname)

        self.log.info("Performing extraction..")

        # Remove all members of the sets so they are not included in the
        # exported file by accident
        self.log.info("Extract sets (Maya ASCII) ...")
        lookdata = instance.data["lookData"]
        sets = lookdata["relationships"].keys()

        resources = instance.data["resources"]
        remap = {}
        for resource in resources:
            attr = resource['attribute']
            remap[attr] = resource['destination']

        self.log.info("Finished remapping destinations ...")

        # Extract in correct render layer
        layer = instance.data.get("renderlayer", "defaultRenderLayer")
        with context.renderlayer(layer):
            # TODO: Ensure membership edits don't become renderlayer overrides
            with context.empty_sets(sets):
                with context.attribute_values(remap):
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
                "relationships": lookdata["relationships"]}

        with open(json_path, "w") as f:
            json.dump(data, f)

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(maya_fname)
        instance.data["files"].append(json_fname)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          maya_path))
