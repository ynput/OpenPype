# -*- coding: utf-8 -*-
"""Validator for Loaded Plugin."""
import os
import pyblish.api
from pymxs import runtime as rt

from openpype.pipeline.publish import (
    RepairAction,
    OptionalPyblishPluginMixin,
    PublishValidationError
)
from openpype.hosts.max.api.lib import get_plugins


class ValidateLoadedPlugin(OptionalPyblishPluginMixin,
                           pyblish.api.InstancePlugin):
    """Validates if the specific plugin is loaded in 3ds max.
    Studio Admin(s) can add the plugins they want to check in validation
    via studio defined project settings
    If families = ["*"], all the required plugins would be validated
    If families

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["max"]
    label = "Validate Loaded Plugins"
    optional = True
    actions = [RepairAction]

    family_plugins_mapping = {}

    def get_invalid(self, instance):
        """Plugin entry point."""
        if not self.is_active(instance.data):
            self.log.debug("Skipping Validate Loaded Plugin...")
            return

        required_plugins = self.family_plugins_mapping
        if not required_plugins:
            return

        invalid = []

        # get all DLL loaded plugins in Max and their plugin index
        available_plugins = {
            plugin_name.lower(): index for index, plugin_name in enumerate(
                get_plugins())
        }

        # Build instance families lookup
        instance_families = {instance.data["family"]}
        instance_families.update(instance.data.get("families", []))
        self.log.debug("Checking plug-in validation "
                       f"for instance families: {instance_families}")
        for family in required_plugins:
            # Check for matching families
            match_families = {fam.strip() for fam in
                              family.split(",") if fam.strip()}
            self.log.debug(f"Plug-in family requirements: {match_families}")
            has_match = "*" in match_families or match_families.intersection(
                instance_families)

            if not has_match:
                continue
            plugins = [plugin for plugin in
                       required_plugins[family]["plugins"]]
            for plugin in plugins:
                if not plugin:
                    return
                # make sure the validation applied for
                # plugins with different Max version
                plugin_name = plugin.format(**os.environ).lower()
                plugin_index = available_plugins.get(plugin_name)

                if plugin_index is None:
                    invalid.append(
                        f"Plugin {plugin} does not exist"
                        " in 3dsMax Plugin List."
                    )
                    continue

                if not rt.pluginManager.isPluginDllLoaded(plugin_index):
                    invalid.append(f"Plugin {plugin} not loaded.")

        return invalid

    def process(self, instance):
        invalid_plugins = self.get_invalid(instance)
        if invalid_plugins:
            bullet_point_invalid_statement = "\n".join(
                "- {}".format(invalid) for invalid in invalid_plugins
            )
            report = (
                "Required plugins are not loaded.\n\n"
                f"{bullet_point_invalid_statement}\n\n"
                "You can use repair action to load the plugin."
            )
            raise PublishValidationError(
                report, title="Missing Required Plugins")

    @classmethod
    def repair(cls, instance):
        # get all DLL loaded plugins in Max and their plugin index
        available_plugins = {
            plugin_name.lower(): index for index, plugin_name in enumerate(
                get_plugins())
        }
        required_plugins = cls.family_plugins_mapping
        instance_families = {instance.data["family"]}
        instance_families.update(instance.data.get("families", []))
        cls.log.debug("Checking plug-in validation "
                      f"for instance families: {instance_families}")
        for family in required_plugins:
            match_families = {fam.strip() for fam in
                              family.split(",") if fam.strip()}
            cls.log.debug(f"Plug-in family requirements: {match_families}")
            has_match = "*" in match_families or match_families.intersection(
                instance_families)

            if not has_match:
                continue

            plugins = [plugin for plugin in family["plugins"]]
            for plugin in plugins:
                if not plugin:
                    return
                plugin_name = plugin.format(**os.environ).lower()
                plugin_index = available_plugins.get(plugin_name)

                if plugin_index is None:
                    cls.log.warning(f"Can't enable missing plugin: {plugin}")
                    continue

                if not rt.pluginManager.isPluginDllLoaded(plugin_index):
                    rt.pluginManager.loadPluginDll(plugin_index)
