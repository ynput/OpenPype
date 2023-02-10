import re
import uuid

from openpype.pipeline import (
    LegacyCreator,
    LoaderPlugin,
    registered_host,
)

from .lib import get_layers_data
from .pipeline import get_current_workfile_context


class Creator(LegacyCreator):
    def __init__(self, *args, **kwargs):
        super(Creator, self).__init__(*args, **kwargs)
        # Add unified identifier created with `uuid` module
        self.data["uuid"] = str(uuid.uuid4())

    @classmethod
    def get_dynamic_data(cls, *args, **kwargs):
        dynamic_data = super(Creator, cls).get_dynamic_data(*args, **kwargs)

        # Change asset and name by current workfile context
        workfile_context = get_current_workfile_context()
        asset_name = workfile_context.get("asset")
        task_name = workfile_context.get("task")
        if "asset" not in dynamic_data and asset_name:
            dynamic_data["asset"] = asset_name

        if "task" not in dynamic_data and task_name:
            dynamic_data["task"] = task_name
        return dynamic_data

    def write_instances(self, data):
        self.log.debug(
            "Storing instance data to workfile. {}".format(str(data))
        )
        host = registered_host()
        return host.write_instances(data)

    def process(self):
        host = registered_host()
        data = host.list_instances()
        data.append(self.data)
        self.write_instances(data)


class Loader(LoaderPlugin):
    hosts = ["tvpaint"]

    @staticmethod
    def get_members_from_container(container):
        if "members" not in container and "objectName" in container:
            # Backwards compatibility
            layer_ids_str = container.get("objectName")
            return [
                int(layer_id) for layer_id in layer_ids_str.split("|")
            ]
        return container["members"]

    def get_unique_layer_name(self, asset_name, name):
        """Layer name with counter as suffix.

        Find higher 3 digit suffix from all layer names in scene matching regex
        `{asset_name}_{name}_{suffix}`. Higher 3 digit suffix is used
        as base for next number if scene does not contain layer matching regex
        `0` is used ase base.

        Args:
            asset_name (str): Name of subset's parent asset document.
            name (str): Name of loaded subset.

        Returns:
            (str): `{asset_name}_{name}_{higher suffix + 1}`
        """
        layer_name_base = "{}_{}".format(asset_name, name)

        counter_regex = re.compile(r"_(\d{3})$")

        higher_counter = 0
        for layer in get_layers_data():
            layer_name = layer["name"]
            if not layer_name.startswith(layer_name_base):
                continue
            number_subpart = layer_name[len(layer_name_base):]
            groups = counter_regex.findall(number_subpart)
            if len(groups) != 1:
                continue

            counter = int(groups[0])
            if counter > higher_counter:
                higher_counter = counter
                continue

        return "{}_{:0>3d}".format(layer_name_base, higher_counter + 1)
