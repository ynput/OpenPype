from bson.objectid import ObjectId

import pyblish.api

from openpype.pipeline import (
    registered_host,
    legacy_io,
)


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
        host = registered_host()
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
        repre_docs = legacy_io.find(
            {"_id": {"$in": _repr_ids}},
            projection={"_id": 1, "parent": 1}
        )
        version_by_repr = {
            str(doc["_id"]): doc["parent"]
            for doc in repre_docs
        }

        # QUESTION should we add same representation id when loaded multiple
        #   times?
        for con in _containers:
            repre_id = con["representation"]
            version_id = version_by_repr.get(repre_id)
            if version_id is None:
                self.log.warning((
                    "Skipping container,"
                    " did not find representation document. {}"
                ).format(str(con)))
                continue

            # NOTE:
            # may have more then one representation that are same version
            version = {
                "subsetName": con["name"],
                "representation": ObjectId(repre_id),
                "version": version_id,
            }
            loaded_versions.append(version)

        context.data["loadedVersions"] = loaded_versions
