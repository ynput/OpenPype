"""Collector for pointcache types.

This will add additional family to pointcache instance based on
the creator_identifier parameter.
"""
import pyblish.api


class CollectPointcacheType(pyblish.api.InstancePlugin):
    """Collect data type for pointcache instance."""

    order = pyblish.api.CollectorOrder
    hosts = ["houdini"]
    families = ["pointcache"]
    label = "Collect type of pointcache"

    def process(self, instance):
        if instance.data["creator_identifier"] == "io.openpype.creators.houdini.bgeo":  # noqa: E501
            instance.data["families"] += ["bgeo"]
        elif instance.data["creator_identifier"] == "io.openpype.creators.houdini.alembic":  # noqa: E501
            instance.data["families"] += ["abc"]
