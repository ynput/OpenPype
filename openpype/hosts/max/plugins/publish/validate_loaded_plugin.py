# -*- coding: utf-8 -*-
"""Validator for Loaded Plugin."""
from pyblish.api import ContextPlugin, ValidatorOrder
from pymxs import runtime as rt

from openpype.pipeline.publish import (
    RepairContextAction,
    OptionalPyblishPluginMixin,
    PublishValidationError
)
from openpype.hosts.max.api.lib import get_plugins


class ValidateLoadedPlugin(OptionalPyblishPluginMixin,
                           ContextPlugin):
    """Validates if the specific plugin is loaded in 3ds max.
    Studio Admin(s) can add the plugins they want to check in validation
    via studio defined project settings"""

    order = ValidatorOrder
    hosts = ["max"]
    label = "Validate Loaded Plugins"
    optional = True
    actions = [RepairContextAction]

    def get_invalid(self, context):
        """Plugin entry point."""
        if not self.is_active(context.data):
            self.log.debug("Skipping Validate Loaded Plugin...")
            return

        required_plugins = (
            context.data["project_settings"]["max"]["publish"]
                        ["ValidateLoadedPlugin"]["plugins_for_check"]
        )

        if not required_plugins:
            return

        invalid = []

        # get all DLL loaded plugins in Max and their plugin index
        available_plugins = {
            plugin_name.lower(): index for index, plugin_name in enumerate(
                get_plugins())
        }

        for plugin in required_plugins:
            plugin_name = plugin.lower()

            plugin_index = available_plugins.get(plugin_name)

            if plugin_index is None:
                invalid.append(
                    f"Plugin {plugin} not exists in 3dsMax Plugin List."
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
                "Required plugins fails to load.\n\n"
                f"{bullet_point_invalid_statement}\n\n"
                "You can use repair action to load the plugin."
            )
            raise PublishValidationError(
                report, title="Required Plugins unloaded")

    @classmethod
    def repair(cls, context):
        # get all DLL loaded plugins in Max and their plugin index
        available_plugins = {
            plugin_name.lower(): index for index, plugin_name in enumerate(
                get_plugins())
        }
        required_plugins = (
            context.data["project_settings"]["max"]["publish"]
                        ["ValidateLoadedPlugin"]["plugins_for_check"]
        )
        for plugin in required_plugins:
            plugin_name = plugin.lower()
            plugin_index = available_plugins.get(plugin_name)

            if plugin_index is None:
                cls.log.warning(f"Can't enable missing plugin: {plugin}")
                continue

            if not rt.pluginManager.isPluginDllLoaded(plugin_index):
                rt.pluginManager.loadPluginDll(plugin_index)
