import os
import json

from maya import cmds

from bson.objectid import ObjectId

from openpype.pipeline import legacy_io
import openpype.api


class ExtractLayout(openpype.api.Extractor):
    """Extract a layout."""

    label = "Extract Layout"
    hosts = ["maya"]
    families = ["layout"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        json_data = []

        for asset in cmds.sets(str(instance), query=True):
            # Find the container
            grp_name = asset.split(':')[0]
            containers = cmds.ls(f"{grp_name}*_CON")

            assert len(containers) == 1, \
                f"More than one container found for {asset}"

            container = containers[0]

            representation_id = cmds.getAttr(f"{container}.representation")

            representation = legacy_io.find_one(
                {
                    "type": "representation",
                    "_id": ObjectId(representation_id)
                }, projection={"parent": True, "context.family": True})

            self.log.info(representation)

            version_id = representation.get("parent")
            family = representation.get("context").get("family")

            json_element = {
                "family": family,
                "instance_name": cmds.getAttr(f"{container}.name"),
                "representation": str(representation_id),
                "version": str(version_id)
            }

            loc = cmds.xform(asset, query=True, translation=True)
            rot = cmds.xform(asset, query=True, rotation=True)
            scl = cmds.xform(asset, query=True, relative=True, scale=True)

            json_element["transform"] = {
                "translation": {
                    "x": loc[0],
                    "y": loc[1],
                    "z": loc[2]
                },
                "rotation": {
                    "x": rot[0],
                    "y": rot[1],
                    "z": rot[2]
                },
                "scale": {
                    "x": scl[0],
                    "y": scl[1],
                    "z": scl[2]
                }
            }

            json_data.append(json_element)

        json_filename = "{}.json".format(instance.name)
        json_path = os.path.join(stagingdir, json_filename)

        with open(json_path, "w+") as file:
            json.dump(json_data, fp=file, indent=2)

        json_representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(json_representation)

        self.log.info("Extracted instance '%s' to: %s",
                      instance.name, json_representation)
