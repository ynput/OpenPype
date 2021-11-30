import pyblish.api
import openpype.api

from maya import cmds

import openpype.hosts.maya.api.action


class ValidateAssemblyModelTransforms(pyblish.api.InstancePlugin):
    """Verify only root nodes of the loaded asset have transformations.

    Note: This check is temporary and is subject to change.

    Example outliner:
    <> means referenced
    ===================================================================

    setdress_GRP|
        props_GRP|
            barrel_01_:modelDefault|        [can have transforms]
                <> barrel_01_:barrel_GRP    [CAN'T have transforms]

            fence_01_:modelDefault|         [can have transforms]
                <> fence_01_:fence_GRP      [CAN'T have transforms]

    """

    order = pyblish.api.ValidatorOrder + 0.49
    label = "Assembly Model Transforms"
    families = ["assembly"]
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               openpype.api.RepairAction]

    prompt_message = ("You are about to reset the matrix to the default values."
                      " This can alter the look of your scene. "
                      "Are you sure you want to continue?")

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found {} invalid transforms of assembly "
                               "items".format(len(invalid)))

    @classmethod
    def get_invalid(cls, instance):

        from openpype.hosts.maya.api import lib

        # Get all transforms in the loaded containers
        container_roots = cmds.listRelatives(instance.data["hierarchy"],
                                             children=True,
                                             type="transform",
                                             fullPath=True)

        transforms_in_container = cmds.listRelatives(container_roots,
                                                     allDescendents=True,
                                                     type="transform",
                                                     fullPath=True)

        # Extra check due to the container roots still being passed through
        transforms_in_container = [i for i in transforms_in_container if i
                                   not in container_roots]

        # Ensure all are identity matrix
        invalid = []
        for transform in transforms_in_container:
            node_matrix = cmds.xform(transform,
                                     query=True,
                                     matrix=True,
                                     objectSpace=True)
            if not lib.matrix_equals(node_matrix, lib.DEFAULT_MATRIX):
                invalid.append(transform)

        return invalid

    @classmethod
    def repair(cls, instance):
        """Reset matrix for illegally transformed nodes

        We want to ensure the user knows the reset will alter the look of
        the current scene because the transformations were done on asset
        nodes instead of the asset top node.

        Args:
            instance:

        Returns:
            None

        """

        from Qt import QtWidgets
        from openpype.hosts.maya.api import lib

        # Store namespace in variable, cosmetics thingy
        messagebox = QtWidgets.QMessageBox
        mode = messagebox.StandardButton.Ok | messagebox.StandardButton.Cancel
        choice = messagebox.warning(None,
                                    "Matrix reset",
                                    cls.prompt_message,
                                    mode)

        invalid = cls.get_invalid(instance)
        if not invalid:
            cls.log.info("No invalid nodes")
            return

        if choice:
            cmds.xform(invalid, matrix=lib.DEFAULT_MATRIX, objectSpace=True)
