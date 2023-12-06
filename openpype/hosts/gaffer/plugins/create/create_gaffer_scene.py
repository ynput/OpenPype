import json

from openpype.hosts.gaffer.api import (
    get_root,
)
from openpype.hosts.gaffer.api.pipeline import imprint, JSON_PREFIX
from openpype.hosts.gaffer.api.lib import make_box

from openpype.pipeline import (
    Creator as NewCreator,
    CreatedInstance,
)

import Gaffer


def read(node):
    """Read all 'user' custom data on the node"""
    if "user" not in node:
        # No user attributes
        return {}

    user = node["user"]
    for key in user:
        print(key, type(key), dir(key))

    return {
        plug.getName(): plug.getValue() for plug in user
    }


class CreateGafferScene(NewCreator):
    identifier = "io.openpype.creators.gaffer."
    label = "Gaffer Scene"
    family = "gafferScene"
    default_variants = ["Main"]
    description = "Export selected as .gfr for single gaffer node"
    icon = "gears"

    attr_prefix = "openpype_"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data.update({
            "id": "pyblish.avalon.instance",
            "subset": subset_name
        })

        script = get_root()
        assert script, "Must have a gaffer scene script as root"

        # Create a box node for publishing
        box = make_box(subset_name)
        script.addChild(box)

        # Register the CreatedInstance
        instance = CreatedInstance(
            family=self.family,
            subset_name=subset_name,
            data=instance_data,
            creator=self,
        )
        data = instance.data_to_store()
        self._imprint(box, data)

        # Insert the transient data
        instance.transient_data["node"] = box

        self._add_instance_to_context(instance)

        return instance

    def collect_instances(self):

        script = get_root()
        assert script, "Must have a gaffer scene script as root"
        for box in script.children(Gaffer.Box):
            data = self._read(box)
            if data.get("creator_identifier") != self.identifier:
                continue

            # Add instance
            created_instance = CreatedInstance.from_existing(data, self)

            # Collect transient data
            created_instance.transient_data["node"] = box

            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            new_data = created_inst.data_to_store()
            box = created_inst.transient_data["node"]
            self._imprint(box, new_data)

    def remove_instances(self, instances):
        for instance in instances:
            # Remove the tool from the scene

            box = instance.transient_data["node"]
            if box:
                parent = box.parent()
                parent.removeChild(box)
                del box

            # Remove the collected CreatedInstance to remove from UI directly
            self._remove_instance_from_context(instance)

    def _read(self, node):
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

        return openpype_data

    def _imprint(self, node, data):

        # TODO: Use node path as uniques
        # Instance id is the node's unique path so we don't need to imprint
        # as data
        # data.pop("instance_id", None)

        # Prefix all keys
        openpype_data = {}
        for key, value in data.items():
            key = f"{self.attr_prefix}{key}"
            openpype_data[key] = value

        imprint(node, openpype_data.items())
