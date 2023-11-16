import pyblish.api
from openpype.lib.attribute_definitions import (
    TextDef,
    BoolDef
)

from openpype.pipeline.publish import OpenPypePyblishPluginMixin
from openpype.client.entities import (
    get_last_version_by_subset_name,
    get_representations
)


class CollectFramesFixDef(
    pyblish.api.InstancePlugin,
    OpenPypePyblishPluginMixin
):
    """Provides text field to insert frame(s) to be rerendered.

    Published files of last version of an instance subset are collected into
    instance.data["last_version_published_files"]. All these but frames
    mentioned in text field will be reused for new version.
    """
    order = pyblish.api.CollectorOrder + 0.495
    label = "Collect Frames to Fix"
    targets = ["local"]
    hosts = ["nuke"]
    families = ["render", "prerender"]

    rewrite_version_enable = False

    def process(self, instance):
        attribute_values = self.get_attr_values_from_data(instance.data)
        frames_to_fix = attribute_values.get("frames_to_fix")

        rewrite_version = attribute_values.get("rewrite_version")

        if not frames_to_fix:
            return

        instance.data["frames_to_fix"] = frames_to_fix

        subset_name = instance.data["subset"]
        asset_name = instance.data["asset"]

        project_entity = instance.data["projectEntity"]
        project_name = project_entity["name"]

        version = get_last_version_by_subset_name(
            project_name,
            subset_name,
            asset_name=asset_name
        )
        if not version:
            self.log.warning(
                "No last version found, re-render not possible"
            )
            return

        representations = get_representations(
            project_name, version_ids=[version["_id"]]
        )
        published_files = []
        for repre in representations:
            if repre["context"]["family"] not in self.families:
                continue

            for file_info in repre.get("files"):
                published_files.append(file_info["path"])

        instance.data["last_version_published_files"] = published_files
        self.log.debug("last_version_published_files::{}".format(
            instance.data["last_version_published_files"]))

        if self.rewrite_version_enable and rewrite_version:
            instance.data["version"] = version["name"]
            # limits triggering version validator
            instance.data.pop("latestVersion")

    @classmethod
    def get_attribute_defs(cls):
        attributes = [
            TextDef("frames_to_fix", label="Frames to fix",
                    placeholder="5,10-15",
                    regex="[0-9,-]+")
        ]

        if cls.rewrite_version_enable:
            attributes.append(
                BoolDef(
                    "rewrite_version",
                    label="Rewrite latest version",
                    default=False
                )
            )

        return attributes
