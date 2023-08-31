"""Collector for filmboxfbx types.

Collectors act as a pre process for the validation stage.
It is used mainly to update instance.data

P.S.
    There are some collectors that run by default
    for all types.

This plugin is part of publish process guide.
"""
import pyblish.api


class CollectFilmboxfbxType(pyblish.api.InstancePlugin):
    """Collect data type for fbx instance."""

    hosts = ["houdini"]
    families = ["staticMesh"]
    label = "Collect type of fbx"

    # Usually you will use this value as default
    order = pyblish.api.CollectorOrder

    # overrides InstancePlugin.process()
    def process(self, instance):

        if instance.data["creator_identifier"] == "io.openpype.creators.houdini.unrealstaticmesh.fbx":  # noqa: E501
            # such a condition can be used to differentiate between
            #  instances by identifier because sometimes instances
            #  may have the same family but different identifier
            #  e.g. bgeo and alembic
            instance.data["families"] += ["fbx"]
