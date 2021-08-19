"""
Requires:
    environment     -> SAPUBLISH_INPATH
    environment     -> SAPUBLISH_OUTPATH

Provides:
    context         -> returnJsonPath (str)
    context         -> project
    context         -> asset
    instance        -> destination_list (list)
    instance        -> representations (list)
    instance        -> source (list)
    instance        -> representations
"""

import os
import json
import copy

import pyblish.api
from avalon import io

from openpype.hosts.testhost import api


class CollectContextDataTestHost(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.
    """

    label = "Collect Context - Test Host"
    order = pyblish.api.CollectorOrder - 0.49
    hosts = ["testhost"]

    def process(self, context):
        # get json paths from os and load them
        io.install()

        for instance_data in api.list_instances():
            # create instance
            self.create_instance(context, instance_data)

    def create_instance(self, context, in_data):
        subset = in_data["subset"]
        # If instance data already contain families then use it
        instance_families = in_data.get("families") or []

        instance = context.create_instance(subset)
        instance.data.update(
            {
                "subset": subset,
                "asset": in_data["asset"],
                "label": subset,
                "name": subset,
                "family": in_data["family"],
                "families": instance_families
            }
        )
        self.log.info("collected instance: {}".format(instance.data))
        self.log.info("parsing data: {}".format(in_data))

        instance.data["representations"] = list()
        instance.data["source"] = "testhost"
