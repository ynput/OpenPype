import os
import shutil
import tempfile

import maya.cmds as cmds
import xgenm

from Qt import QtWidgets

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

    def write_xgen_file(self, file_path, data):
        lines = []
        with open(file_path, "r") as f:
            for key, value in data.items():
                for line in [line.rstrip() for line in f]:
                    if line.startswith("\t" + key):
                        line = "\t{}\t\t{}".format(key, value)
                    lines.append(line)

        with open(file_path, "w") as f:
            f.write("\n".join(lines))

    def setup_xgen_palette_file(self, maya_filepath, namespace, name):
        # Setup xgen palette file.
        project_path = os.path.dirname(current_file())

        # Copy the xgen palette file from published version.
        _, maya_extension = os.path.splitext(maya_filepath)
        source = maya_filepath.replace(maya_extension, ".xgen")
        xgen_file = os.path.join(
            project_path,
            "{basename}__{namespace}__{name}.xgen".format(
                basename=os.path.splitext(os.path.basename(current_file()))[0],
                namespace=namespace,
                name=name
            )
        ).replace("\\", "/")
        self.log.info("Copying {} to {}".format(source, xgen_file))
        shutil.copy(source, xgen_file)

        # Modify xgDataPath and xgProjectPath to have current workspace first
        # and published version directory second. This ensure that any newly
        # created xgen files are created in the current workspace.
        resources_path = os.path.join(os.path.dirname(source), "resources")

        with open(xgen_file, "r") as f:
            for line in [line.rstrip() for line in f]:
                if line.startswith("\txgDataPath"):
                    data_path = line.split("\t")[-1]

        data = {
            "xgDataPath": (
                "${{PROJECT}}xgen/collections/{}__ns__{}/{}{}".format(
                    namespace,
                    name,
                    os.pathsep,
                    data_path.replace(
                        "${PROJECT}xgen", resources_path.replace("\\", "/")
                    )
                )
            ),
            "xgProjectPath": project_path.replace("\\", "/")
        }
        self.write_xgen_file(xgen_file, data)

        xgd_file = xgen_file.replace(".xgen", ".xgd")

        return xgen_file, xgd_file

    def process_reference(self, context, name, namespace, options):
        # Validate workfile has a path.
        if current_file() is None:
            QtWidgets.QMessageBox.warning(
                None,
                "",
                "Current workfile has not been saved. Please save the workfile"
                " before loading an Xgen."
            )
            return

        maya_filepath = self.prepare_root_value(
            self.fname, context["project"]["name"]
        )

        xgen_file, xgd_file = self.setup_xgen_palette_file(
            maya_filepath, namespace, "collection"
        )

        # Making temporary copy of xgen file from published so we can
        # modify the paths.
        temp_xgen_file = os.path.join(tempfile.gettempdir(), "temp.xgen")
        _, maya_extension = os.path.splitext(maya_filepath)
        source = maya_filepath.replace(maya_extension, ".xgen")
        shutil.copy(source, temp_xgen_file)

        resources_path = os.path.join(os.path.dirname(source), "resources")
        with open(xgen_file, "r") as f:
            for line in [line.rstrip() for line in f]:
                if line.startswith("\txgDataPath"):
                    data_path = line.split("\t")[-1]
        data = {
            "xgDataPath": data_path.replace(
                "${PROJECT}xgen", resources_path.replace("\\", "/")
            )
        }
        self.write_xgen_file(temp_xgen_file, data)

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

            xgen_palette = xgenm.importPalette(
                temp_xgen_file.replace("\\", "/"), [], nameSpace=namespace
            )
            os.remove(temp_xgen_file)

            self.set_palette_attributes(xgen_palette, xgen_file, xgd_file)

            # This create an expression attribute of float. If we did not add
            # any changes to collection, then Xgen does not create an xgd file
            # on save. This gives errors when launching the workfile again due
            # to trying to find the xgd file.
            xgenm.addCustomAttr(
                "custom_float_ignore", xgen_palette.replace("|", "")
            )

            shapes = cmds.ls(nodes, shapes=True, long=True)

            new_nodes = (list(set(nodes) - set(shapes)) + [xgen_palette])

            self[:] = new_nodes

        return new_nodes

    def set_palette_attributes(self, xgen_palette, xgen_file, xgd_file):
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

    def update(self, container, representation):
        """Workflow for updating Xgen.

        - Copy and potentially overwrite the workspace .xgen file.
        - Export changes to delta file.
        - Set collection attributes to not include delta files.
        - Update xgen maya file reference.
        - Apply the delta file changes.
        - Reset collection attributes to include delta files.

        We have to do this workflow because when using referencing of the xgen
        collection, Maya implicitly imports the Xgen data from the xgen file so
        we dont have any control over when adding the delta file changes.

        There is an implicit increment of the xgen and delta files, due to
        using the workfile basename.
        """

        container_node = container["objectName"]
        members = get_container_members(container_node)
        xgen_palette = cmds.ls(members, type="xgmPalette", long=True)[0]
        reference_node = get_reference_node(members, self.log)
        namespace = cmds.referenceQuery(reference_node, namespace=True)[1:]

        xgen_file, xgd_file = self.setup_xgen_palette_file(
            get_representation_path(representation),
            namespace,
            representation["data"]["xgenName"]
        )

        # Export current changes to apply later.
        xgenm.createDelta(xgen_palette.replace("|", ""), xgd_file)

        self.set_palette_attributes(xgen_palette, xgen_file, xgd_file)

        attribute_data = {
            "{}.xgFileName".format(xgen_palette): os.path.basename(xgen_file),
            "{}.xgBaseFile".format(xgen_palette): "",
            "{}.xgExportAsDelta".format(xgen_palette): False
        }
        with attribute_values(attribute_data):
            super().update(container, representation)

            xgenm.applyDelta(xgen_palette.replace("|", ""), xgd_file)
