"""Collector for filmboxfbx types.

Collectors act as a pre process for the validation stage.
It is used mainly to update instance.data

P.S.
    There are some collectors that run by default
    for all types.

This plugin is part of publish process guide.
"""
import pyblish.api


class CollectFilmboxfbxType(pyblish.api.InstancePlugin):
    """Collect data type for fbx instance."""

    hosts = ["houdini"]
    families = ["fbx", "staticMesh"]
    label = "Collect type of fbx"

    # Usually you will use this value as default
    order = pyblish.api.CollectorOrder

    # overrides InstancePlugin.process()
    def process(self, instance):

        if instance.data["creator_identifier"] == "io.openpype.creators.houdini.unrealstaticmesh":  # noqa: E501
            # such a condition can be used to differentiate between
            #  instances by identifier becuase sometimes instances
            #  may have the same family but different identifier
            #  e.g. bgeo and alembic
            instance.data["families"] += ["fbx"]

        # Update instance.data with ouptut_node
        out_node = self.get_output_node(instance)

        if out_node:
            instance.data["output_node"] = out_node

        # Disclaimer : As a convntin we use collect_output_node.py
        #   to Update instance.data with ouptut_node of different types
        #   however, this collector is used for demonstration

    def get_output_node(self, instance):
        """Getting output_node Logic."""

        import hou

        # get output node
        node = hou.node(instance.data["instance_node"])
        out_node = node.parm("startnode").evalAsNode()

        if not out_node:
            self.log.warning("No output node collected.")
            return

        self.log.debug("Output node: %s" % out_node.path())
        return out_node
