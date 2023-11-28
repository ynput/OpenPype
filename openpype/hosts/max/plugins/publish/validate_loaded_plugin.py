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
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["max"]
    label = "Validate Loaded Plugins"
    optional = True
    actions = [RepairAction]

    family_plugins_mapping = {}

    @classmethod
    def get_invalid(cls, instance):
        """Plugin entry point."""
        family_plugins_mapping = cls.family_plugins_mapping
        if not family_plugins_mapping:
            return

        invalid = []
        # Find all plug-in requirements for current instance
        instance_families = {instance.data["family"]}
        instance_families.update(instance.data.get("families", []))
        cls.log.debug("Checking plug-in validation "
                      f"for instance families: {instance_families}")
        all_required_plugins = set()

        for mapping in family_plugins_mapping:
            # Check for matching families
            if not mapping:
                return

            match_families = {fam.strip() for fam in mapping["families"]}
            has_match = "*" in match_families or match_families.intersection(
                instance_families)

            if not has_match:
                continue

            cls.log.debug(
                f"Found plug-in family requirements: {match_families}")
            required_plugins = [
                # match lowercase and format with os.environ to allow
                # plugin names defined by max version, e.g. {3DSMAX_VERSION}
                plugin.format(**os.environ).lower()
                for plugin in mapping["plugins"]
                # ignore empty fields in settings
                if plugin.strip()
            ]

            all_required_plugins.update(required_plugins)

        if not all_required_plugins:
            # Instance has no plug-in requirements
            return

        # get all DLL loaded plugins in Max and their plugin index
        available_plugins = {
            plugin_name.lower(): index for index, plugin_name in enumerate(
                get_plugins())
        }
        # validate the required plug-ins
        for plugin in sorted(all_required_plugins):
            plugin_index = available_plugins.get(plugin)
            if plugin_index is None:
                debug_msg = (
                    f"Plugin {plugin} does not exist"
                    " in 3dsMax Plugin List."
                )
                invalid.append((plugin, debug_msg))
                continue
            if not rt.pluginManager.isPluginDllLoaded(plugin_index):
                debug_msg = f"Plugin {plugin} not loaded."
                invalid.append((plugin, debug_msg))
        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            self.log.debug("Skipping Validate Loaded Plugin...")
            return
        invalid = self.get_invalid(instance)
        if invalid:
            bullet_point_invalid_statement = "\n".join(
                "- {}".format(message) for _, message in invalid
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
        invalid = cls.get_invalid(instance)
        if not invalid:
            return

        # get all DLL loaded plugins in Max and their plugin index
        available_plugins = {
            plugin_name.lower(): index for index, plugin_name in enumerate(
                get_plugins())
        }

        for invalid_plugin, _ in invalid:
            plugin_index = available_plugins.get(invalid_plugin)

            if plugin_index is None:
                cls.log.warning(
                    f"Can't enable missing plugin: {invalid_plugin}")
                continue

            if not rt.pluginManager.isPluginDllLoaded(plugin_index):
                rt.pluginManager.loadPluginDll(plugin_index)
