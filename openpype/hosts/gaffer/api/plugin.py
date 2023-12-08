import json
from openpype.hosts.gaffer.api.pipeline import imprint, JSON_PREFIX


def read(node):
    """Read all 'user' custom data on the node"""
    if "user" not in node:
        # No user attributes
        return {}
    return {
        plug.getName(): plug.getValue() for plug in node["user"]
    }


class CreatorImprintReadMixin:
    """Mixin providing _read and _imprint methods to be used by Creators.
    """

    attr_prefix = "openpype_"

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

        openpype_data["instance_id"] = node.fullName()

        return openpype_data

    def _imprint(self, node, data):
        # Instance id is the node's unique full name so we don't need to
        # imprint as data. This makes it so that duplicating a node will
        # correctly detect it as a new unique instance.
        data.pop("instance_id", None)

        # Prefix all keys
        openpype_data = {}
        for key, value in data.items():
            key = f"{self.attr_prefix}{key}"
            openpype_data[key] = value

        imprint(node, openpype_data.items())
