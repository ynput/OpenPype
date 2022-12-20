import os
import shutil

import maya.cmds as cmds
import xgenm

import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api.lib import (
    maintained_selection, get_container_members
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
                "{}.xgFileName".format(xgen_palette),
                os.path.basename(xgen_file),
                type="string"
            )

            shapes = cmds.ls(nodes, shapes=True, long=True)

            new_nodes = (list(set(nodes) - set(shapes)))

            self[:] = new_nodes

        return new_nodes

    def update(self, container, representation):
        super().update(container, representation)

        # Get reference node from container members
        node = container["objectName"]
        members = get_container_members(node)
        reference_node = get_reference_node(members, self.log)
        namespace = cmds.referenceQuery(reference_node, namespace=True)[1:]

        xgen_file = self.setup_xgen_palette_file(
            get_representation_path(representation),
            namespace,
            representation["data"]["xgenName"]
        )

        xgen_palette = cmds.ls(members, type="xgmPalette", long=True)[0]
        cmds.setAttr(
            "{}.xgFileName".format(xgen_palette),
            os.path.basename(xgen_file),
            type="string"
        )

        # Reload reference to update the xgen.
        cmds.file(loadReference=reference_node, force=True)
