# -*- coding: utf-8 -*-
"""Collect active SyncSketch server config."""
import pyblish.api


class CollectActiveServerConfig(pyblish.api.ContextPlugin):
    """Collect active SyncSketch server config from settings."""

    order = pyblish.api.CollectorOrder
    label = "Active SyncSketch Server"

    single = False

    def process(self, context):
        try:
            syncsketch_addon = (
                context.data.get("openPypeModules")["syncsketch"])
        except AttributeError:
            self.log.error("Cannot get Ayon SyncSketch addon.")
            raise AssertionError("Ayon SyncSketch addon not found.")

        # get first active syncsketch server config from settings
        server_config = (
            syncsketch_addon.get_syncsketch_project_active_config(
                context.data["project_settings"]
            )
        )

        self.log.debug(
            "Active SyncSketch server config: {}".format(server_config)
        )
        context.data["syncsketchServerConfig"] = server_config
