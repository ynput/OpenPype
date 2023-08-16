import maya.cmds as cmds

from openpype.settings import get_current_project_settings
import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api import lib


class YetiRigLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """This loader will load Yeti rig."""

    families = ["yetiRig"]
    representations = ["ma"]

    label = "Load Yeti Rig"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process_reference(
        self, context, name=None, namespace=None, options=None
    ):
        path = self.filepath_from_context(context)

        attach_to_root = options.get("attach_to_root", True)
        group_name = options["group_name"]

        # no group shall be created
        if not attach_to_root:
            group_name = namespace

        with lib.maintained_selection():
            file_url = self.prepare_root_value(
                path, context["project"]["name"]
            )
            nodes = cmds.file(
                file_url,
                namespace=namespace,
                reference=True,
                returnNewNodes=True,
                groupReference=attach_to_root,
                groupName=group_name
            )

        settings = get_current_project_settings()
        colors = settings["maya"]["load"]["colors"]
        c = colors.get("yetiRig")
        if c is not None:
            cmds.setAttr(group_name + ".useOutlinerColor", 1)
            cmds.setAttr(
                group_name + ".outlinerColor",
                (float(c[0]) / 255), (float(c[1]) / 255), (float(c[2]) / 255)
            )
        self[:] = nodes

        return nodes
