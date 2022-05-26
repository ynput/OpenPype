# -*- coding: utf-8 -*-
"""Collect instances that should be processed and published on DL.

"""
import os

import pyblish.api
from openpype.pipeline import PublishValidationError


class CollectDeadlinePublishableInstances(pyblish.api.InstancePlugin):
    """Collect instances that should be processed and published on DL.

    Some long running publishes (not just renders) could be offloaded to DL,
    this plugin compares theirs name against env variable, marks only
    publishable by farm.

    Triggered only when running only in headless mode, eg on a farm.
    """

    order = pyblish.api.CollectorOrder + 0.499
    label = "Collect Deadline Publishable Instance"
    targets = ["remote"]

    def process(self, instance):
        self.log.debug("CollectDeadlinePublishableInstances")
        publish_inst = os.environ.get("OPENPYPE_PUBLISH_SUBSET", '')
        if not publish_inst:
            raise PublishValidationError("OPENPYPE_PUBLISH_SUBSET env var "
                                         "required for remote publishing")

        subset_name = instance.data["subset"]
        if subset_name == publish_inst:
            self.log.debug("Publish {}".format(subset_name))
            instance.data["publish"] = True
            instance.data["farm"] = False
            instance.data["families"].remove("deadline")
        else:
            self.log.debug("Skipping {}".format(subset_name))
            instance.data["publish"] = False
