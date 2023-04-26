# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from pymxs import runtime as rt


class ValidateUSDPlugin(pyblish.api.InstancePlugin):
    """Validates if USD plugin is installed or loaded in Max
    """

    order = pyblish.api.ValidatorOrder - 0.01
    families = ["model"]
    hosts = ["max"]
    label = "USD Plugin"

    def process(self, instance):
        plugin_mgr = rt.pluginManager
        plugin_count = plugin_mgr.pluginDllCount
        plugin_info = self.get_plugins(plugin_mgr,
                                       plugin_count)
        usd_import = "usdimport.dli"
        if usd_import not in plugin_info:
            raise PublishValidationError("USD Plugin {}"
                                         " not found".format(usd_import))
        usd_export = "usdexport.dle"
        if usd_export not in plugin_info:
            raise PublishValidationError("USD Plugin {}"
                                         " not found".format(usd_export))

    def get_plugins(self, manager, count):
        plugin_info_list = list()
        for p in range(1, count + 1):
            plugin_info = manager.pluginDllName(p)
            plugin_info_list.append(plugin_info)

        return plugin_info_list
