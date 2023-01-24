import os
import copy

from maya import cmds
import xgenm

from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import maintained_selection
from openpype.lib import StringTemplate


class ExtractXgenCache(publish.Extractor):
    """Extract Xgen

    Workflow:
    - Duplicate nodes used for patches.
    - Export palette and import onto duplicate nodes.
    - Export/Publish duplicate nodes and palette.
    - Publish all xgen files as resources.
    """

    label = "Extract Xgen"
    hosts = ["maya"]
    families = ["xgen"]
    scene_type = "ma"

    def process(self, instance):
        if "representations" not in instance.data:
            instance.data["representations"] = []

        staging_dir = self.staging_dir(instance)
        maya_filename = "{}.{}".format(instance.data["name"], self.scene_type)
        maya_filepath = os.path.join(staging_dir, maya_filename)

        # Get published xgen file name.
        template_data = copy.deepcopy(instance.data["anatomyData"])
        template_data.update({"ext": "xgen"})
        templates = instance.context.data["anatomy"].templates["publish"]
        xgen_filename = StringTemplate(templates["file"]).format(template_data)
        name = instance.data["xgmPalette"].replace(":", "__").replace("|", "")
        xgen_filename = xgen_filename.replace(".xgen", "__" + name + ".xgen")

        # Export xgen palette files.
        xgen_path = os.path.join(staging_dir, xgen_filename).replace("\\", "/")
        xgenm.exportPalette(
            instance.data["xgmPalette"].replace("|", ""), xgen_path
        )
        self.log.info("Extracted to {}".format(xgen_path))

        representation = {
            "name": name,
            "ext": "xgen",
            "files": xgen_filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        # Collect nodes to export.
        duplicate_nodes = []
        for node, connections in instance.data["xgenConnections"].items():
            transform_name = connections["transform"].split(".")[0]

            # Duplicate_transform subd patch geometry.
            duplicate_transform = cmds.duplicate(transform_name)[0]

            # Discard the children.
            shapes = cmds.listRelatives(duplicate_transform, shapes=True)
            children = cmds.listRelatives(duplicate_transform, children=True)
            cmds.delete(set(children) - set(shapes))

            duplicate_transform = cmds.parent(
                duplicate_transform, world=True
            )[0]

            duplicate_nodes.append(duplicate_transform)

        # Export Maya file.
        type = "mayaAscii" if self.scene_type == "ma" else "mayaBinary"
        with maintained_selection():
            cmds.select(duplicate_nodes)
            cmds.file(
                maya_filepath,
                force=True,
                type=type,
                exportSelected=True,
                preserveReferences=False,
                constructionHistory=True,
                shader=True,
                constraints=True,
                expressions=True
            )

        self.log.info("Extracted to {}".format(maya_filepath))

        representation = {
            "name": self.scene_type,
            "ext": self.scene_type,
            "files": maya_filename,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)

        cmds.delete(duplicate_nodes)

        # Collect all files under palette root as resources.
        data_path = xgenm.getAttr(
            "xgDataPath", instance.data["xgmPalette"].replace("|", "")
        ).split(os.pathsep)[0]
        data_path = data_path.replace(
            "${PROJECT}",
            xgenm.getAttr(
                "xgProjectPath", instance.data["xgmPalette"].replace("|", "")
            )
        )
        transfers = []
        for root, _, files in os.walk(data_path):
            for file in files:
                source = os.path.join(root, file).replace("\\", "/")
                destination = os.path.join(
                    instance.data["resourcesDir"],
                    "collections",
                    os.path.basename(data_path),
                    source.replace(data_path, "")[1:]
                )
                transfers.append((source, destination.replace("\\", "/")))

        instance.data["transfers"] = transfers
