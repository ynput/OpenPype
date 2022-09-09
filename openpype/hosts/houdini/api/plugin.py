# -*- coding: utf-8 -*-
"""Houdini specific Avalon/Pyblish plugin definitions."""
import sys
from abc import (
    ABCMeta
)
import six
import hou
from openpype.pipeline import (
    CreatorError,
    LegacyCreator,
    Creator as NewCreator,
    CreatedInstance
)
from openpype.lib import BoolDef
from openpype.hosts.houdini.api import list_instances, remove_instance
from .lib import imprint, read


class OpenPypeCreatorError(CreatorError):
    pass


class Creator(LegacyCreator):
    """Creator plugin to create instances in Houdini

    To support the wide range of node types for render output (Alembic, VDB,
    Mantra) the Creator needs a node type to create the correct instance

    By default, if none is given, is `geometry`. An example of accepted node
    types: geometry, alembic, ifd (mantra)

    Please check the Houdini documentation for more node types.

    Tip: to find the exact node type to create press the `i` left of the node
    when hovering over a node. The information is visible under the name of
    the node.

    """
    defaults = ['Main']

    def __init__(self, *args, **kwargs):
        super(Creator, self).__init__(*args, **kwargs)
        self.nodes = list()

    def process(self):
        """This is the base functionality to create instances in Houdini

        The selected nodes are stored in self to be used in an override method.
        This is currently necessary in order to support the multiple output
        types in Houdini which can only be rendered through their own node.

        Default node type if none is given is `geometry`

        It also makes it easier to apply custom settings per instance type

        Example of override method for Alembic:

            def process(self):
                instance =  super(CreateEpicNode, self, process()
                # Set paramaters for Alembic node
                instance.setParms(
                    {"sop_path": "$HIP/%s.abc" % self.nodes[0]}
                )

        Returns:
            hou.Node

        """
        try:
            if (self.options or {}).get("useSelection"):
                self.nodes = hou.selectedNodes()

            # Get the node type and remove it from the data, not needed
            node_type = self.data.pop("node_type", None)
            if node_type is None:
                node_type = "geometry"

            # Get out node
            out = hou.node("/out")
            instance = out.createNode(node_type, node_name=self.name)
            instance.moveToGoodPosition()

            imprint(instance, self.data)

            self._process(instance)

        except hou.Error as er:
            six.reraise(
                OpenPypeCreatorError,
                OpenPypeCreatorError("Creator error: {}".format(er)),
                sys.exc_info()[2])


@six.add_metaclass(ABCMeta)
class HoudiniCreator(NewCreator):
    selected_nodes = []

    def _create_instance_node(
            self, node_name, parent,
            node_type="geometry"):
        # type: (str, str, str) -> hou.Node
        """Create node representing instance.

        Arguments:
            node_name (str): Name of the new node.
            parent (str): Name of the parent node.
            node_type (str, optional): Type of the node.

        Returns:
            hou.Node: Newly created instance node.

        """
        parent_node = hou.node(parent)
        instance_node = parent_node.createNode(
            node_type, node_name=node_name)
        instance_node.moveToGoodPosition()
        return instance_node

    def create(self, subset_name, instance_data, pre_create_data):
        try:
            if pre_create_data.get("use_selection"):
                self.selected_nodes = hou.selectedNodes()

            # Get the node type and remove it from the data, not needed
            node_type = instance_data.pop("node_type", None)
            if node_type is None:
                node_type = "geometry"

            instance_node = self._create_instance_node(
                subset_name, "/out", node_type, pre_create_data)

            # wondering if we'll ever need more than one member here
            # in Houdini
            instance_data["members"] = [instance_node.path()]
            instance_data["instance_node"] = instance_node.path()

            instance = CreatedInstance(
                self.family,
                subset_name,
                instance_data,
                self)
            self._add_instance_to_context(instance)
            imprint(instance_node, instance.data_to_store())
            return instance

        except hou.Error as er:
            six.reraise(
                OpenPypeCreatorError,
                OpenPypeCreatorError("Creator error: {}".format(er)),
                sys.exc_info()[2])

    def collect_instances(self):
        for instance in list_instances(creator_id=self.identifier):
            created_instance = CreatedInstance.from_existing(
                read(instance), self
            )
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            instance_node = hou.node(created_inst.get("instance_node"))
            current_data = read(instance_node)

            imprint(
                instance_node,
                {
                    key: value[1] for key, value in _changes.items()
                    if current_data.get(key) != value[1]
                },
                update=True
            )

    def remove_instances(self, instances):
        for instance in instances:
            remove_instance(instance)
            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection", label="Use selection")
        ]
