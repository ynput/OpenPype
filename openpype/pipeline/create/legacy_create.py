"""Create workflow moved from avalon-core repository.

Renamed classes and functions
- 'Creator' -> 'LegacyCreator'
- 'create'  -> 'legacy_create'
"""

import os
import logging
import collections

from openpype.client import get_asset_by_id

from .subset_name import get_subset_name


class LegacyCreator(object):
    """Determine how assets are created"""
    label = None
    family = None
    defaults = None
    maintain_selection = True
    enabled = True

    dynamic_subset_keys = []

    log = logging.getLogger("LegacyCreator")
    log.propagate = True

    def __init__(self, name, asset, options=None, data=None):
        self.name = name  # For backwards compatibility
        self.options = options

        # Default data
        self.data = collections.OrderedDict()
        self.data["id"] = "pyblish.avalon.instance"
        self.data["family"] = self.family
        self.data["asset"] = asset
        self.data["subset"] = name
        self.data["active"] = True

        self.data.update(data or {})

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        """Apply OpenPype settings to a plugin class."""

        host_name = os.environ.get("AVALON_APP")
        plugin_type = "create"
        plugin_type_settings = (
            project_settings
            .get(host_name, {})
            .get(plugin_type, {})
        )
        global_type_settings = (
            project_settings
            .get("global", {})
            .get(plugin_type, {})
        )
        if not global_type_settings and not plugin_type_settings:
            return

        plugin_name = cls.__name__

        plugin_settings = None
        # Look for plugin settings in host specific settings
        if plugin_name in plugin_type_settings:
            plugin_settings = plugin_type_settings[plugin_name]

        # Look for plugin settings in global settings
        elif plugin_name in global_type_settings:
            plugin_settings = global_type_settings[plugin_name]

        if not plugin_settings:
            return

        print(">>> We have preset for {}".format(plugin_name))
        for option, value in plugin_settings.items():
            if option == "enabled" and value is False:
                print("  - is disabled by preset")
            else:
                print("  - setting `{}`: `{}`".format(option, value))
            setattr(cls, option, value)

    def process(self):
        pass

    @classmethod
    def get_dynamic_data(
        cls, variant, task_name, asset_id, project_name, host_name
    ):
        """Return dynamic data for current Creator plugin.

        By default return keys from `dynamic_subset_keys` attribute as mapping
        to keep formatted template unchanged.

        ```
        dynamic_subset_keys = ["my_key"]
        ---
        output = {
            "my_key": "{my_key}"
        }
        ```

        Dynamic keys may override default Creator keys (family, task, asset,
        ...) but do it wisely if you need.

        All of keys will be converted into 3 variants unchanged, capitalized
        and all upper letters. Because of that are all keys lowered.

        This method can be modified to prefill some values just keep in mind it
        is class method.

        Returns:
            dict: Fill data for subset name template.
        """
        dynamic_data = {}
        for key in cls.dynamic_subset_keys:
            key = key.lower()
            dynamic_data[key] = "{" + key + "}"
        return dynamic_data

    @classmethod
    def get_subset_name(
        cls, variant, task_name, asset_id, project_name, host_name=None
    ):
        """Return subset name created with entered arguments.

        Logic extracted from Creator tool. This method should give ability
        to get subset name without the tool.

        TODO: Maybe change `variant` variable.

        By default is output concatenated family with user text.

        Args:
            variant (str): What is entered by user in creator tool.
            task_name (str): Context's task name.
            asset_id (ObjectId): Mongo ID of context's asset.
            project_name (str): Context's project name.
            host_name (str): Name of host.

        Returns:
            str: Formatted subset name with entered arguments. Should match
                config's logic.
        """

        dynamic_data = cls.get_dynamic_data(
            variant, task_name, asset_id, project_name, host_name
        )

        asset_doc = get_asset_by_id(
            project_name, asset_id, fields=["data.tasks"]
        )

        return get_subset_name(
            cls.family,
            variant,
            task_name,
            asset_doc,
            project_name,
            host_name,
            dynamic_data=dynamic_data
        )


def legacy_create(Creator, name, asset, options=None, data=None, switch_to_main_thread=True):
    """Create a new instance

    Associate nodes with a subset and family. These nodes are later
    validated, according to their `family`, and integrated into the
    shared environment, relative their `subset`.

    Data relative each family, along with default data, are imprinted
    into the resulting objectSet. This data is later used by extractors
    and finally asset browsers to help identify the origin of the asset.

    Arguments:
        Creator (Creator): Class of creator
        name (str): Name of subset
        asset (str): Name of asset
        options (dict, optional): Additional options from GUI
        data (dict, optional): Additional data from GUI
        switch_to_main_thread (bool): Run process in main thread in case creator is executed from another

    Raises:
        NameError on `subset` already exists
        KeyError on invalid dynamic property
        RuntimeError on host error

    Returns:
        Name of instance

    """
    from openpype.pipeline import registered_host

    host = registered_host()
    plugin = Creator(name, asset, options, data)

    # Pick the correct process function
    process_func = plugin.process if switch_to_main_thread else plugin._process

    if plugin.maintain_selection is True:
        with host.maintained_selection():
            print("Running %s with maintained selection" % plugin)
            instance = process_func()
        return instance

    print("Running %s" % plugin)
    instance = process_func()
    return instance
