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
from .lib import imprint, read, lsattr


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

    Deprecated:
        This creator is deprecated and will be removed in future version.

    """
    defaults = ['Main']

    def __init__(self, *args, **kwargs):
        super(Creator, self).__init__(*args, **kwargs)
        self.nodes = []

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


class HoudiniCreatorBase(object):
    @staticmethod
    def cache_subsets(shared_data):
        """Cache instances for Creators to shared data.

        Create `houdini_cached_subsets` key when needed in shared data and
        fill it with all collected instances from the scene under its
        respective creator identifiers.

        If legacy instances are detected in the scene, create
        `houdini_cached_legacy_subsets` there and fill it with
        all legacy subsets under family as a key.

        Args:
            Dict[str, Any]: Shared data.

        Return:
            Dict[str, Any]: Shared data dictionary.

        """
        if shared_data.get("houdini_cached_subsets") is None:
            shared_data["houdini_cached_subsets"] = {}
            if shared_data.get("houdini_cached_legacy_subsets") is None:
                shared_data["houdini_cached_legacy_subsets"] = {}
            cached_instances = lsattr("id", "pyblish.avalon.instance")
            for i in cached_instances:
                if not i.parm("creator_identifier"):
                    # we have legacy instance
                    family = i.parm("family").eval()
                    if family not in shared_data[
                            "houdini_cached_legacy_subsets"]:
                        shared_data["houdini_cached_legacy_subsets"][
                            family] = [i]
                    else:
                        shared_data[
                            "houdini_cached_legacy_subsets"][family].append(i)
                    continue

                creator_id = i.parm("creator_identifier").eval()
                if creator_id not in shared_data["houdini_cached_subsets"]:
                    shared_data["houdini_cached_subsets"][creator_id] = [i]
                else:
                    shared_data[
                        "houdini_cached_subsets"][creator_id].append(i)  # noqa
        return shared_data

    @staticmethod
    def create_instance_node(
            node_name, parent,
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


@six.add_metaclass(ABCMeta)
class HoudiniCreator(NewCreator, HoudiniCreatorBase):
    """Base class for most of the Houdini creator plugins."""
    selected_nodes = []

    def create(self, subset_name, instance_data, pre_create_data):
        try:
            if pre_create_data.get("use_selection"):
                self.selected_nodes = hou.selectedNodes()

            # Get the node type and remove it from the data, not needed
            node_type = instance_data.pop("node_type", None)
            if node_type is None:
                node_type = "geometry"

            instance_node = self.create_instance_node(
                subset_name, "/out", node_type)

            self.customize_node_look(instance_node)

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

    def lock_parameters(self, node, parameters):
        """Lock list of specified parameters on the node.

        Args:
            node (hou.Node): Houdini node to lock parameters on.
            parameters (list of str): List of parameter names.

        """
        for name in parameters:
            try:
                parm = node.parm(name)
                parm.lock(True)
            except AttributeError:
                self.log.debug("missing lock pattern {}".format(name))

    def collect_instances(self):
        # cache instances  if missing
        self.cache_subsets(self.collection_shared_data)
        for instance in self.collection_shared_data[
                "houdini_cached_subsets"].get(self.identifier, []):
            created_instance = CreatedInstance.from_existing(
                read(instance), self
            )
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            instance_node = hou.node(created_inst.get("instance_node"))

            new_values = {
                key: new_value
                for key, (_old_value, new_value) in _changes.items()
            }
            imprint(
                instance_node,
                new_values,
                update=True
            )

    def remove_instances(self, instances):
        """Remove specified instance from the scene.

        This is only removing `id` parameter so instance is no longer
        instance, because it might contain valuable data for artist.

        """
        for instance in instances:
            instance_node = hou.node(instance.data.get("instance_node"))
            if instance_node:
                instance_node.destroy()

            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection", label="Use selection")
        ]

    @staticmethod
    def customize_node_look(
            node, color=None,
            shape="chevron_down"):
        """Set custom look for instance nodes.

        Args:
            node (hou.Node): Node to set look.
            color (hou.Color, Optional): Color of the node.
            shape (str, Optional): Shape name of the node.

        Returns:
            None

        """
        if not color:
            color = hou.Color((0.616, 0.871, 0.769))
        node.setUserData('nodeshape', shape)
        node.setColor(color)
