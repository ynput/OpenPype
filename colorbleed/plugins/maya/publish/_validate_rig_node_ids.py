from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateRigNodeIds(pyblish.api.InstancePlugin):
    """Validate nodes in instance have colorbleed id attributes

    To fix this use the action to select the invalid nodes. Identify these
    are nodes created locally to the rig; if they are not they should've gotten
    their ID elsewhere! This is important, because then you should NOT fix it
    in your scene but earlier in the pipeline. If these invalid nodes are local
    to your rig then you should generate ids for them.

    For Dummies:
        For the pipeline it's important in further stages to identify exactly
        "what nodes is what node". Basically it saying: Hey! It's me! To
        accompany that each node stores an ID, like its own passport. This
        validator will tell you if there are nodes that have no such
        passport (ID).

    Warning:
        This does NOT validate the IDs are unique in the instance.

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.rig',
                'colorbleed.rigcontrols',
                "colorbleed.rigpointcache"]
    hosts = ['maya']
    label = 'Rig Id Attributes'
    actions = [colorbleed.api.SelectInvalidAction]

    # includes: yeti grooms and v-ray fur, etc.
    TYPES = ("transform", "mesh", "nurbsCurve", "geometryShape")

    @staticmethod
    def get_invalid(instance):

        # filter to nodes of specific types
        dag = cmds.ls(instance, noIntermediate=True,
                      long=True, type=ValidateRigNodeIds.TYPES)

        # Ensure all nodes have a cbId
        invalid = list()
        for node in dag:
            # todo: refactor `mbId` when attribute is updated
            uuid = cmds.attributeQuery("mbId", node=node, exists=True)
            if not uuid:
                invalid.append(node)

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Nodes found without "
                               "asset IDs: {0}".format(invalid))
