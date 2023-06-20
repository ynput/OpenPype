import os
import copy
import tempfile

from maya import cmds
import xgenm

from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import (
    maintained_selection, attribute_values, write_xgen_file, delete_after
)
from openpype.lib import StringTemplate


class ExtractXgen(publish.Extractor):
    """Extract Xgen

    Workflow:
    - Duplicate nodes used for patches.
    - Export palette and import onto duplicate nodes.
    - Export/Publish duplicate nodes and palette.
    - Export duplicate palette to .xgen file and add to publish.
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

        xgen_path = os.path.join(
            self.staging_dir(instance), xgen_filename
        ).replace("\\", "/")
        type = "mayaAscii" if self.scene_type == "ma" else "mayaBinary"

        # Duplicate xgen setup.
        with delete_after() as delete_bin:
            duplicate_nodes = []
            # Collect nodes to export.
            for _, connections in instance.data["xgenConnections"].items():
                transform_name = connections["transform"].split(".")[0]

                # Duplicate_transform subd patch geometry.
                duplicate_transform = cmds.duplicate(transform_name)[0]
                delete_bin.append(duplicate_transform)

                # Discard the children.
                shapes = cmds.listRelatives(duplicate_transform, shapes=True)
                children = cmds.listRelatives(
                    duplicate_transform, children=True
                )
                cmds.delete(set(children) - set(shapes))

                if cmds.listRelatives(duplicate_transform, parent=True):
                    duplicate_transform = cmds.parent(
                        duplicate_transform, world=True
                    )[0]

                duplicate_nodes.append(duplicate_transform)

            # Export temp xgen palette files.
            temp_xgen_path = os.path.join(
                tempfile.gettempdir(), "temp.xgen"
            ).replace("\\", "/")
            xgenm.exportPalette(
                instance.data["xgmPalette"].replace("|", ""), temp_xgen_path
            )
            self.log.info("Extracted to {}".format(temp_xgen_path))

            # Import xgen onto the duplicate.
            with maintained_selection():
                cmds.select(duplicate_nodes)
                palette = xgenm.importPalette(temp_xgen_path, [])

            delete_bin.append(palette)

            # Copy shading assignments.
            nodes = (
                instance.data["xgmDescriptions"] +
                instance.data["xgmSubdPatches"]
            )
            for node in nodes:
                target_node = node.split(":")[-1]
                shading_engine = cmds.listConnections(
                    node, type="shadingEngine"
                )[0]
                cmds.sets(target_node, edit=True, forceElement=shading_engine)

            # Export duplicated palettes.
            xgenm.exportPalette(palette, xgen_path)

            # Export Maya file.
            attribute_data = {"{}.xgFileName".format(palette): xgen_filename}
            with attribute_values(attribute_data):
                with maintained_selection():
                    cmds.select(duplicate_nodes + [palette])
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

        if os.path.exists(temp_xgen_path):
            os.remove(temp_xgen_path)

        data = {
            "xgDataPath": os.path.join(
                instance.data["resourcesDir"],
                "collections",
                palette.replace(":", "__ns__")
            ).replace("\\", "/"),
            "xgProjectPath": os.path.dirname(
                instance.data["resourcesDir"]
            ).replace("\\", "/")
        }
        write_xgen_file(data, xgen_path)

        # Adding representations.
        representation = {
            "name": "xgen",
            "ext": "xgen",
            "files": xgen_filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        representation = {
            "name": self.scene_type,
            "ext": self.scene_type,
            "files": maya_filename,
            "stagingDir": staging_dir
        }
        instance.data["representations"].append(representation)
