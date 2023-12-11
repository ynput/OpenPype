import json
from abc import abstractmethod

from openpype.pipeline import (
    Creator as NewCreator,
    CreatedInstance,
)

from openpype.hosts.gaffer.api import (
    get_root,
)
from openpype.hosts.gaffer.api.pipeline import imprint, JSON_PREFIX

import Gaffer


def read(node):
    """Read all 'user' custom data on the node"""
    if "user" not in node:
        # No user attributes
        return {}
    return {
        plug.getName(): plug.getValue() for plug in node["user"]
    }


class CreatorImprintReadMixin:
    """Mixin providing _read and _imprint methods to be used by Creators."""

    attr_prefix = "openpype_"

    def _read(self, node: Gaffer.Node) -> dict:
        all_user_data = read(node)

        # Consider only data with the special attribute prefix
        # and strip off the prefix as for the resulting data
        prefix_len = len(self.attr_prefix)
        openpype_data = {}
        for key, value in all_user_data.items():
            if not key.startswith(self.attr_prefix):
                continue

            if isinstance(value, str) and value.startswith(JSON_PREFIX):
                value = value[len(JSON_PREFIX):]  # strip off JSON prefix
                value = json.loads(value)

            key = key[prefix_len:]      # strip off prefix
            openpype_data[key] = value

        openpype_data["instance_id"] = node.fullName()

        return openpype_data

    def _imprint(self, node: Gaffer.Node, data: dict):
        # Instance id is the node's unique full name so we don't need to
        # imprint as data. This makes it so that duplicating a node will
        # correctly detect it as a new unique instance.
        data.pop("instance_id", None)

        # Prefix all keys
        openpype_data = {}
        for key, value in data.items():
            key = f"{self.attr_prefix}{key}"
            openpype_data[key] = value

        imprint(node, openpype_data)


class GafferCreatorBase(NewCreator, CreatorImprintReadMixin):
    """Base class for single node Creators in Gaffer.

    Child classes must implement `_create_node` to define the node to be
    Created. Aside of that everything should already be handled by the base
    class but can be overridden for special cases.

    """
    default_variants = ["Main"]

    @abstractmethod
    def _create_node(self,
                     subset_name: str,
                     pre_create_data: dict) -> Gaffer.Node:
        """Create the relevant node type for the instance.

        This only gets called on Create, update is handled automatically by
        updating imprinted data on this node.

        Arguments:
            subset_name (str): The subset name to be created. Usually used for
                the node's name.
            pre_create_data (dict): The `pre_create_data` of the `create` call
                of this Creator.

        Returns:
            Gaffer.Node: The created node.

        """
        pass

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data.update({
            "id": "pyblish.avalon.instance",
            "subset": subset_name
        })

        script = get_root()
        assert script, "Must have a gaffer scene script as root"

        # Create a box node for publishing
        node = self._create_node(subset_name, pre_create_data)
        script.addChild(node)

        # Register the CreatedInstance
        instance = CreatedInstance(
            family=self.family,
            subset_name=subset_name,
            data=instance_data,
            creator=self,
        )
        data = instance.data_to_store()
        self._imprint(node, data)

        # Insert the transient data
        instance.transient_data["node"] = node

        self._add_instance_to_context(instance)

        return instance

    def collect_instances(self):

        script = get_root()
        assert script, "Must have a gaffer scene script as root"
        for node in script.children(Gaffer.Node):
            data = self._read(node)
            if data.get("creator_identifier") != self.identifier:
                continue

            # Add instance
            created_instance = CreatedInstance.from_existing(data, self)

            # Collect transient data
            created_instance.transient_data["node"] = node

            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            new_data = created_inst.data_to_store()
            box = created_inst.transient_data["node"]
            self._imprint(box, new_data)

    def remove_instances(self, instances):
        for instance in instances:
            # Remove the tool from the scene

            node = instance.transient_data["node"]
            if node:
                parent = node.parent()
                parent.removeChild(node)
                del node

            # Remove the collected CreatedInstance to remove from UI directly
            self._remove_instance_from_context(instance)
