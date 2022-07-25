from pyblish import api
from openpype.pipeline import legacy_io


class CollectAssetBuilds(api.ContextPlugin):
    """Collect asset from tags.

    Tag is expected to have name of the asset and metadata:
        {
            "family": "assetbuild"
        }
    """

    # Run just after CollectClip
    order = api.CollectorOrder + 0.02
    label = "Collect AssetBuilds"
    hosts = ["hiero"]

    def process(self, context):
        asset_builds = {}
        for asset in legacy_io.find({"type": "asset"}):
            if asset["data"]["entityType"] == "AssetBuild":
                self.log.debug("Found \"{}\" in database.".format(asset))
                asset_builds[asset["name"]] = asset

        for instance in context:
            if instance.data["family"] != "clip":
                continue

            # Exclude non-tagged instances.
            tagged = False
            asset_names = []

            for tag in instance.data["tags"]:
                t_metadata = dict(tag.metadata())
                t_family = t_metadata.get("tag.family", "")

                if t_family.lower() == "assetbuild":
                    asset_names.append(tag["name"])
                    tagged = True

            if not tagged:
                self.log.debug(
                    "Skipping \"{}\" because its not tagged with "
                    "\"assetbuild\"".format(instance)
                )
                continue

            # Collect asset builds.
            data = {"assetbuilds": []}
            for name in asset_names:
                data["assetbuilds"].append(
                    asset_builds[name]
                )
            self.log.debug(
                "Found asset builds: {}".format(data["assetbuilds"])
            )

            instance.data.update(data)
