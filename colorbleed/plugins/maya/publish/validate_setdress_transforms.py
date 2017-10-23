import pyblish.api
import colorbleed.api


class ValidateSetDressModelTransforms(pyblish.api.InstancePlugin):
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
    label = "Setdress Model Transforms"
    families = ["colorbleed.setdress"]
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found %s invalid transforms of setdress items")

    @classmethod
    def get_invalid(cls, instance):

        import colorbleed.maya.lib as lib
        from maya import cmds

        invalid = []

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
        for transform in transforms_in_container:
            node_matrix = cmds.xform(transform,
                                     query=True,
                                     matrix=True,
                                     objectSpace=True)
            if not lib.matrix_equals(node_matrix, lib.DEFAULT_MATRIX):
                print transform
                invalid.append(transform)

        return invalid
