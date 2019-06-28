from pyblish import api
from avalon import io


class CollectAssetBuilds(api.InstancePlugin):
    """Collect asset from tags.

    Tag is expected to have name of the asset and metadata:
        {
            "family": "asset"
        }
    """

    # Run just before CollectShot
    order = api.CollectorOrder + 0.102
    label = "Collect AssetBuilds"
    hosts = ["nukestudio"]
    families = ["clip"]

    def process(self, instance):
        # Exclude non-tagged instances.
        tagged = False
        asset_names = []
        for tag in instance.data["tags"]:
            family = dict(tag["metadata"]).get("tag.family", "")
            if family.lower() == "assetbuild":
                asset_names.append(tag["name"])
                tagged = True

        if not tagged:
            self.log.debug(
                "Skipping \"{}\" because its not tagged with "
                "\"assetbuild\"".format(instance)
            )
            return

        # Collect asset builds.
        data = {"assetBuilds": []}
        for name in asset_names:
            data["assetBuilds"].append(
                instance.context.data["assetBuilds"][name]
            )
        self.log.debug("Found asset builds: {}".format(data["assetBuilds"]))

        instance.data.update(data)


class CollectExistingAssetBuilds(api.ContextPlugin):
    """Collect all asset builds from database."""

    order = CollectAssetBuilds.order - 0.1
    label = "Collect Existing AssetBuilds"
    hosts = ["nukestudio"]

    def process(self, context):
        context.data["assetBuilds"] = {}
        for asset in io.find({"type": "asset"}):
            if asset["data"]["entityType"] == "AssetBuild":
                context.data["assetBuilds"][asset["name"]] = asset
