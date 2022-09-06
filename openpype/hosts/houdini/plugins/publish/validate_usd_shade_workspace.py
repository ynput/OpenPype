import pyblish.api
from openpype.pipeline.publish import ValidateContentsOrder

import hou


class ValidateUsdShadeWorkspace(pyblish.api.InstancePlugin):
    """Validate USD Shading Workspace is correct version.

    There have been some issues with outdated/erroneous Shading Workspaces
    so this is to confirm everything is set as it should.

    """

    order = ValidateContentsOrder
    hosts = ["houdini"]
    families = ["usdShade"]
    label = "USD Shade Workspace"

    def process(self, instance):

        rop = instance.data["members"][0]
        workspace = rop.parent()

        definition = workspace.type().definition()
        name = definition.nodeType().name()
        library = definition.libraryFilePath()

        all_definitions = hou.hda.definitionsInFile(library)
        node_type, version = name.rsplit(":", 1)
        version = float(version)

        highest = version
        for other_definition in all_definitions:
            other_name = other_definition.nodeType().name()
            other_node_type, other_version = other_name.rsplit(":", 1)
            other_version = float(other_version)

            if node_type != other_node_type:
                continue

            # Get highest version
            highest = max(highest, other_version)

        if version != highest:
            raise RuntimeError(
                "Shading Workspace is not the latest version."
                " Found %s. Latest is %s." % (version, highest)
            )

        # There were some issues with the editable node not having the right
        # configured path. So for now let's assure that is correct to.from
        value = (
            'avalon://`chs("../asset_name")`/'
            'usdShade`chs("../model_variantname1")`.usd'
        )
        rop_value = rop.parm("lopoutput").rawValue()
        if rop_value != value:
            raise RuntimeError(
                "Shading Workspace has invalid 'lopoutput'"
                " parameter value. The Shading Workspace"
                " needs to be reset to its default values."
            )
