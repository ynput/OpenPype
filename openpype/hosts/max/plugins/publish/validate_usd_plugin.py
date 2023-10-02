# -*- coding: utf-8 -*-
"""Validator for USD plugin."""
from pyblish.api import InstancePlugin, ValidatorOrder
from pymxs import runtime as rt

from openpype.pipeline import (
    OptionalPyblishPluginMixin,
    PublishValidationError
)


def get_plugins() -> list:
    """Get plugin list from 3ds max."""
    manager = rt.PluginManager
    count = manager.pluginDllCount
    plugin_info_list = []
    for p in range(1, count + 1):
        plugin_info = manager.pluginDllName(p)
        plugin_info_list.append(plugin_info)

    return plugin_info_list


class ValidateUSDPlugin(OptionalPyblishPluginMixin,
                        InstancePlugin):
    """Validates if USD plugin is installed or loaded in 3ds max."""

    order = ValidatorOrder - 0.01
    families = ["model"]
    hosts = ["max"]
    label = "Validate USD Plugin loaded"
    optional = True

    def process(self, instance):
        """Plugin entry point."""

        for sc in ValidateUSDPlugin.__subclasses__():
            self.log.info(sc)

        if not self.is_active(instance.data):
            return

        plugin_info = get_plugins()
        usd_import = "usdimport.dli"
        if usd_import not in plugin_info:
            raise PublishValidationError(f"USD Plugin {usd_import} not found")
        usd_export = "usdexport.dle"
        if usd_export not in plugin_info:
            raise PublishValidationError(f"USD Plugin {usd_export} not found")
