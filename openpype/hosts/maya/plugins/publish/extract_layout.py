import math
import os
import json

from maya import cmds
from maya.api import OpenMaya as om

from openpype.client import get_representation_by_id
from openpype.pipeline import publish


class ExtractLayout(publish.Extractor):
    """Extract a layout."""

    label = "Extract Layout"
    hosts = ["maya"]
    families = ["layout"]
    project_container = "AVALON_CONTAINERS"
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        json_data = []
        # TODO representation queries can be refactored to be faster
        project_name = instance.context.data["projectName"]

        for asset in cmds.sets(str(instance), query=True):
            # Find the container
            project_container = self.project_container
            container_list = cmds.ls(project_container)
            if len(container_list) == 0:
                self.log.warning("Project container is not found!")
                self.log.warning("The asset(s) may not be properly loaded after published") # noqa
                continue

            grp_loaded_ass = instance.data.get("groupLoadedAssets", False)
            if grp_loaded_ass:
                asset_list = cmds.listRelatives(asset, children=True)
                for asset in asset_list:
                    grp_name = asset.split(':')[0]
            else:
                grp_name = asset.split(':')[0]
            containers = cmds.ls("{}*_CON".format(grp_name))
            if len(containers) == 0:
                self.log.warning("{} isn't from the loader".format(asset))
                self.log.warning("It may not be properly loaded after published") # noqa
                continue
            container = containers[0]

            representation_id = cmds.getAttr(
                "{}.representation".format(container))

            representation = get_representation_by_id(
                project_name,
                representation_id,
                fields=["parent", "context.family"]
            )

            self.log.info(representation)

            version_id = representation.get("parent")
            family = representation.get("context").get("family")

            json_element = {
                "family": family,
                "instance_name": cmds.getAttr(
                    "{}.namespace".format(container)),
                "representation": str(representation_id),
                "version": str(version_id)
            }

            loc = cmds.xform(asset, query=True, translation=True)
            rot = cmds.xform(asset, query=True, rotation=True, euler=True)
            scl = cmds.xform(asset, query=True, relative=True, scale=True)

            json_element["transform"] = {
                "translation": {
                    "x": loc[0],
                    "y": loc[1],
                    "z": loc[2]
                },
                "rotation": {
                    "x": math.radians(rot[0]),
                    "y": math.radians(rot[1]),
                    "z": math.radians(rot[2])
                },
                "scale": {
                    "x": scl[0],
                    "y": scl[1],
                    "z": scl[2]
                }
            }

            row_length = 4
            t_matrix_list = cmds.xform(asset, query=True, matrix=True)

            transform_mm = om.MMatrix(t_matrix_list)
            transform = om.MTransformationMatrix(transform_mm)

            t = transform.translation(om.MSpace.kWorld)
            t = om.MVector(t.x, t.z, -t.y)
            transform.setTranslation(t, om.MSpace.kWorld)
            transform.rotateBy(
                om.MEulerRotation(math.radians(-90), 0, 0), om.MSpace.kWorld)
            transform.scaleBy([1.0, 1.0, -1.0], om.MSpace.kObject)

            t_matrix_list = list(transform.asMatrix())

            t_matrix = []
            for i in range(0, len(t_matrix_list), row_length):
                t_matrix.append(t_matrix_list[i:i + row_length])

            json_element["transform_matrix"] = [
                list(row)
                for row in t_matrix
            ]

            basis_list = [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, -1, 0,
                0, 0, 0, 1
            ]

            basis_mm = om.MMatrix(basis_list)
            basis = om.MTransformationMatrix(basis_mm)

            b_matrix_list = list(basis.asMatrix())
            b_matrix = []

            for i in range(0, len(b_matrix_list), row_length):
                b_matrix.append(b_matrix_list[i:i + row_length])

            json_element["basis"] = []
            for row in b_matrix:
                json_element["basis"].append(list(row))

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
