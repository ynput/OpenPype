# -*- coding: utf-8 -*-
"""Validate presence of footage items in composition
Requires:
"""
import os

import pyblish.api

from openpype.pipeline import (
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)
from openpype.hosts.aftereffects.api import get_stub


class ValidateFootageItems(OptionalPyblishPluginMixin,
                           pyblish.api.InstancePlugin):
    """
        Validates if FootageItems contained in composition exist.

    AE fails silently and doesn't render anything if footage item file is
    missing. This validator tries to check existence of the files.
    It will not protect from missing frame in multiframes though
    (as AE api doesn't provide this information and it cannot be told how many
    frames should be there easily). Missing frame is replaced by placeholder.
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Footage Items"
    families = ["render.farm", "render.local", "render"]
    hosts = ["aftereffects"]
    optional = True

    def process(self, instance):
        """Plugin entry point."""
        # Skip the instance if is not active by data on the instance
        if not self.is_active(instance.data):
            return

        comp_id = instance.data["comp_id"]
        for footage_item in get_stub().get_items(comps=False, folders=False,
                                                 footages=True):
            self.log.info(footage_item)
            if comp_id not in footage_item.containing_comps:
                continue

            path = footage_item.path
            if path and not os.path.exists(path):
                msg = f"File {path} not found."
                formatting = {"name": footage_item.name, "path": path}
                raise PublishXmlValidationError(self, msg,
                                                formatting_data=formatting)
