import os
import shutil

import maya.cmds as cmds
import pymel.core as pm

import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api.lib import maintained_selection
from openpype.hosts.maya.api import current_file


class XgenLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Load Xgen as reference"""

    families = ["xgen"]
    representations = ["ma", "mb"]

    label = "Reference Xgen"
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, options):
        maya_filepath = self.prepare_root_value(
            self.fname, context["project"]["name"]
        )
        project_path = os.path.dirname(current_file())

        # Setup xgen palette file.
        # Copy the xgen palette file from published version.
        _, maya_extension = os.path.splitext(maya_filepath)
        source = maya_filepath.replace(maya_extension, ".xgen")
        destination = os.path.join(
            project_path,
            "{basename}__{namespace}__{name}.xgen".format(
                basename=os.path.splitext(os.path.basename(current_file()))[0],
                namespace=namespace,
                name=context["representation"]["data"]["xgenName"]
            )
        )
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

            shapes = cmds.ls(nodes, shapes=True, long=True)

            new_nodes = (list(set(nodes) - set(shapes)))

            self[:] = new_nodes

        return new_nodes

    def update(self, container, representation):
        pass
