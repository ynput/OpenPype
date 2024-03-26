import pyblish.api

from openpype.client import get_representations
from openpype.pipeline import registered_host


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
        "tvpaint",
        "equalizer",
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
        containers = list(host.ls())
        repre_ids = {
            container["representation"]
            for container in containers
        }

        project_name = context.data["projectName"]
        repre_docs = get_representations(
            project_name,
            representation_ids=repre_ids,
            fields=["_id", "parent"]
        )
        repre_doc_by_str_id = {
            str(doc["_id"]): doc
            for doc in repre_docs
        }

        # QUESTION should we add same representation id when loaded multiple
        #   times?
        for con in containers:
            repre_id = con["representation"]
            repre_doc = repre_doc_by_str_id.get(repre_id)
            if repre_doc is None:
                self.log.warning((
                    "Skipping container,"
                    " did not find representation document. {}"
                ).format(str(con)))
                continue

            # NOTE:
            # may have more then one representation that are same version
            version = {
                "subsetName": con["name"],
                "representation": repre_doc["_id"],
                "version": repre_doc["parent"],
            }
            loaded_versions.append(version)

        context.data["loadedVersions"] = loaded_versions
