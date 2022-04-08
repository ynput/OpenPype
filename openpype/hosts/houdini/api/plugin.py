# -*- coding: utf-8 -*-
"""Houdini specific Avalon/Pyblish plugin definitions."""
import sys
import six
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty
)
import six
import hou
from openpype.pipeline import (
    CreatorError,
    LegacyCreator,
    Creator as NewCreator
)
from .lib import imprint


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
    _nodes = []

    def collect_instances(self):
        pass

    def update_instances(self, update_list):
        pass

    def remove_instances(self, instances):
        pass