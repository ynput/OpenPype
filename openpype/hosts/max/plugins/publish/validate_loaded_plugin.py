# -*- coding: utf-8 -*-
"""Validator for USD plugin."""
from pyblish.api import InstancePlugin, ValidatorOrder
from pymxs import runtime as rt

from openpype.pipeline.publish import (
    RepairAction,
    OptionalPyblishPluginMixin,
    PublishValidationError
)
from openpype.hosts.max.api.lib import get_plugins


class ValidateLoadedPlugin(OptionalPyblishPluginMixin,
                           InstancePlugin):
    """Validates if the specific plugin is loaded in 3ds max.
    User can add the plugins they want to check through"""

    order = ValidatorOrder
    hosts = ["max"]
    label = "Validate Loaded Plugin"
    optional = True
    actions = [RepairAction]

    def get_invalid(self, instance):
        """Plugin entry point."""
        invalid = []
        # display all DLL loaded plugins in Max
        plugin_info = get_plugins()
        project_settings = instance.context.data[
            "project_settings"]["max"]["publish"]
        target_plugins = project_settings[
            "ValidateLoadedPlugin"]["plugins_for_check"]
        for plugin in target_plugins:
            if plugin.lower() not in plugin_info:
                invalid.append(
                    f"Plugin {plugin} not exists in 3dsMax Plugin List.")
            for i, _ in enumerate(plugin_info):
                if plugin.lower() == rt.pluginManager.pluginDllName(i):
                    if not rt.pluginManager.isPluginDllLoaded(i):
                        invalid.append(
                            f"Plugin {plugin} not loaded.")
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
            raise PublishValidationError(report, title="Required Plugins unloaded")

    @classmethod
    def repair(cls, instance):
        plugin_info = get_plugins()
        project_settings = instance.context.data[
            "project_settings"]["max"]["publish"]
        target_plugins = project_settings[
            "ValidateLoadedPlugin"]["plugins_for_check"]
        for plugin in target_plugins:
            for i, _ in enumerate(plugin_info):
                if plugin == rt.pluginManager.pluginDllName(i):
                    if not rt.pluginManager.isPluginDllLoaded(i):
                        rt.pluginManager.loadPluginDll(i)
