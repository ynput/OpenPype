from bson.objectid import ObjectId

import pyblish.api
from avalon import api, io


class CollectSceneLoadedVersions(pyblish.api.ContextPlugin):

    order = pyblish.api.CollectorOrder + 0.0001
    label = "Collect Versions Loaded in Scene"
    hosts = [
        "aftereffects",
        "blender",
        "celaction",
        "fusion",
        "harmony",
        "hiero",
        "houdini",
        "maya",
        "nuke",
        "photoshop",
        "resolve",
        "tvpaint"
    ]

    def process(self, context):
        host = api.registered_host()
        if host is None:
            self.log.warn("No registered host.")
            return

        if not hasattr(host, "ls"):
            host_name = host.__name__
            self.log.warn("Host %r doesn't have ls() implemented." % host_name)
            return

        loaded_versions = []
        _containers = list(host.ls())
        _repr_ids = [ObjectId(c["representation"]) for c in _containers]
        version_by_repr = {
            str(doc["_id"]): doc["parent"] for doc in
            io.find({"_id": {"$in": _repr_ids}}, projection={"parent": 1})
        }

        for con in _containers:
            # NOTE:
            # may have more then one representation that are same version
            version = {
                "subsetName": con["name"],
                "representation": ObjectId(con["representation"]),
                "version": version_by_repr[con["representation"]],  # _id
            }
            loaded_versions.append(version)

        context.data["loadedVersions"] = loaded_versions
