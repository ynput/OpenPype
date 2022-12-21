import os
import shutil

import maya.cmds as cmds
import xgenm

import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api.lib import (
    maintained_selection, get_container_members, attribute_values
)
from openpype.hosts.maya.api import current_file
from openpype.hosts.maya.api.plugin import get_reference_node
from openpype.pipeline import get_representation_path


class XgenLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Load Xgen as reference"""

    families = ["xgen"]
    representations = ["ma", "mb"]

    label = "Reference Xgen"
    icon = "code-fork"
    color = "orange"

    def setup_xgen_palette_file(self, maya_filepath, namespace, name):
        # Setup xgen palette file.
        project_path = os.path.dirname(current_file())

        # Copy the xgen palette file from published version.
        _, maya_extension = os.path.splitext(maya_filepath)
        source = maya_filepath.replace(maya_extension, ".xgen")
        destination = os.path.join(
            project_path,
            "{basename}__{namespace}__{name}.xgen".format(
                basename=os.path.splitext(os.path.basename(current_file()))[0],
                namespace=namespace,
                name=name
            )
        ).replace("\\", "/")
        self.log.info("Copying {} to {}".format(source, destination))
        shutil.copy(source, destination)

        # Modify xgDataPath and xgProjectPath to have current workspace first
        # and published version directory second. This ensure that any newly
        # created xgen files are created in the current workspace.
        resources_path = os.path.join(os.path.dirname(source), "resources")
        lines = []
        with open(destination, "r") as f:
            for line in [line.rstrip() for line in f]:
                if line.startswith("\txgDataPath"):
                    data_path = line.split("\t")[-1]
                    line = "\txgDataPath\t\t{}{}{}".format(
                        data_path,
                        os.pathsep,
                        data_path.replace(
                            "${PROJECT}xgen", resources_path.replace("\\", "/")
                        )
                    )

                if line.startswith("\txgProjectPath"):
                    line = "\txgProjectPath\t\t{}/".format(
                        project_path.replace("\\", "/")
                    )

                lines.append(line)

        with open(destination, "w") as f:
            f.write("\n".join(lines))

        return destination

    def process_reference(self, context, name, namespace, options):
        maya_filepath = self.prepare_root_value(
            self.fname, context["project"]["name"]
        )

        name = context["representation"]["data"]["xgenName"]
        xgen_file = self.setup_xgen_palette_file(
            maya_filepath, namespace, name
        )
        xgd_file = xgen_file.replace(".xgen", ".xgd")

        # Create a placeholder xgen delta file. This create an expression
        # attribute of float. If we did not add any changes to the delta file,
        # then Xgen deletes the xgd file on save to clean up (?). This gives
        # errors when launching the workfile again due to trying to find the
        # xgd file.
        #change author, date and version path
        xgd_template = """
# XGen Delta File
#
# Version:  C:/Program Files/Autodesk/Maya2022/plug-ins/xgen/
# Author:   tokejepsen
# Date:     Tue Dec 20 09:03:29 2022

FileVersion 18

Palette    custom_float_ignore    0

"""
        with open(xgd_file, "w") as f:
            f.write(xgd_template)

        # Reference xgen. Xgen does not like being referenced in under a group.
        new_nodes = []

        with maintained_selection():
            nodes = cmds.file(
                maya_filepath,
                namespace=namespace,
                sharedReferenceFile=False,
                reference=True,
                returnNewNodes=True
            )

            xgen_palette = cmds.ls(nodes, type="xgmPalette", long=True)[0]
            cmds.setAttr(
                "{}.xgBaseFile".format(xgen_palette),
                os.path.basename(xgen_file),
                type="string"
            )
            cmds.setAttr(
                "{}.xgFileName".format(xgen_palette),
                os.path.basename(xgd_file),
                type="string"
            )
            cmds.setAttr("{}.xgExportAsDelta".format(xgen_palette), True)

            shapes = cmds.ls(nodes, shapes=True, long=True)

            new_nodes = (list(set(nodes) - set(shapes)))

            self[:] = new_nodes

        return new_nodes

    def update(self, container, representation):
        """Workflow for updating Xgen.

        - Copy and overwrite the workspace .xgen file.
        - Set collection attributes to not include delta files.
        - Update xgen maya file reference.
        - Apply the delta file changes.
        - Reset collection attributes to include delta files.

        We have to do this workflow because when using referencing of the xgen
        collection, Maya implicitly imports the Xgen data from the xgen file so
        we dont have any control over added the delta file changes.
        """

        container_node = container["objectName"]
        members = get_container_members(container_node)
        reference_node = get_reference_node(members, self.log)
        namespace = cmds.referenceQuery(reference_node, namespace=True)[1:]

        xgen_file = self.setup_xgen_palette_file(
            get_representation_path(representation),
            namespace,
            representation["data"]["xgenName"]
        )
        xgd_file = xgen_file.replace(".xgen", ".xgd")

        xgen_palette = cmds.ls(members, type="xgmPalette", long=True)[0]

        attribute_data = {
            "{}.xgFileName".format(xgen_palette): os.path.basename(xgen_file),
            "{}.xgBaseFile".format(xgen_palette): "",
            "{}.xgExportAsDelta".format(xgen_palette): False
        }
        with attribute_values(attribute_data):
            super().update(container, representation)

            xgenm.applyDelta(xgen_palette.replace("|", ""), xgd_file)
