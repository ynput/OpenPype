import pyblish.api
import maya.cmds as cmds
import colorbleed.api
import pyblish_maya

import cb.utils.maya.dag as dag


class ValidateLayoutContent(pyblish.api.InstancePlugin):
    """Validates that layout contains at least a gpuCache or mesh shape node

    Also validates that (at the current frame that this is tested at) at least
    a single shape is visible.

    Without any shape nodes the layout would simply cache 'nothing' visually
    and would seem redundant.

    Note: Theoretically this validation does disable the possibility to just
        cache some "transforms" to be used elsewhere. As such currently the
        'layout' family is only intended to be used for visual shapes.

    """

    order = colorbleed.api.ValidateContentsOrder
    label = 'Layout Content'
    families = ['colorbleed.layout']

    def process(self, instance):

        placeholder = instance.data.get("placeholder", False)

        # Ensure any meshes or gpuCaches in instance
        if not cmds.ls(instance, type=("mesh", "gpuCache", "nurbsCurve"), long=True):
            raise RuntimeError("Layout has no mesh, gpuCache or nurbsCurve children: "
                               "{0}".format(instance))

        # Ensure at least any extract nodes readily available after filtering
        with pyblish_maya.maintained_selection():

            import cbra.utils.maya.layout as layout

            nodes = instance.data['setMembers']
            cmds.select(nodes, r=1, hierarchy=True)
            hierarchy = cmds.ls(sl=True, long=True)
            extract_nodes = layout.filter_nodes(hierarchy)

            if not extract_nodes:
                self.log.info("Set members: {0}".format(nodes))
                self.log.info("Hierarchy: {0}".format(hierarchy))
                raise RuntimeError("No nodes to extract after "
                                   "filtering: {0}".format(extract_nodes))

        # If no meshes in layout the gpuCache command will crash as such
        # we consider this invalid, unless "placeholder" is set to True
        meshes = cmds.ls(cmds.ls(extract_nodes,
                                 dag=True,
                                 leaf=True,
                                 shapes=True,
                                 noIntermediate=True,
                                 long=True),
                         type=("mesh", "gpuCache"),
                         long=True)
        if not meshes and not placeholder:
            raise RuntimeError("No meshes in layout. "
                               "Set placeholder to True on instance to allow "
                               "extraction without meshes")

        # Ensure at least one MESH shape is visible
        extract_shapes = cmds.ls(extract_nodes,
                                 shapes=True,
                                 long=True)

        if not placeholder:
            # We validate that at least one shape is visible to avoid erroneous
            # extractions of invisible-only content.
            for shape in extract_shapes:
                if dag.is_visible(shape,
                                  displayLayer=False,
                                  intermediateObject=True,
                                  visibility=True,
                                  parentHidden=True):
                    break
            else:
                raise RuntimeError("No extract shape is visible. "
                                   "Layout requires at least one "
                                   "shape to be visible.")

