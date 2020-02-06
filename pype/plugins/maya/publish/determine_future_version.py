import pyblish
from avalon import api, io


class DetermineFutureVersion(pyblish.api.InstancePlugin):
    """
    This will determine version of subset if we want render to be attached to.
    """
    label = "Determine Subset Version"
    order = pyblish.api.IntegratorOrder
    hosts = ["maya"]
    families = ["renderlayer"]

    def process(self, instance):
        context = instance.context
        attach_to_subsets = [s["subset"] for s in instance.data['attachTo']]

        if not attach_to_subsets:
            return

        for i in context:
            if i.data["subset"] in attach_to_subsets:
                latest_version = self._get_latest_version(i.data["subset"])

                # this will get corresponding subset in attachTo list
                # so we can set version there
                sub = next(item for item in instance.data['attachTo'] if item["subset"] == i.data["subset"])  # noqa: E501

                if not latest_version:
                    # if latest_version is None, subset is not yet in
                    # database so we'll check its instance to see if version
                    # is there and use that, or we'll just stay with v1
                    latest_version = i.data.get("version", 1)

                sub["version"] = latest_version
                self.log.info("render will be attached to {} v{}".format(
                        sub["subset"], sub["version"]
                ))

    def _get_latest_version(self, subset):
        latest_version = None

        project_name = api.Session["AVALON_PROJECT"]
        asset_name = api.Session["AVALON_ASSET"]

        project_entity = io.find_one({
            "type": "project",
            "name": project_name
        })

        assert project_entity, (
            "Project '{0}' was not found."
        ).format(project_name)

        asset_entity = io.find_one({
            "type": "asset",
            "name": asset_name,
            "parent": project_entity["_id"]
        })
        assert asset_entity, (
            "No asset found by the name '{0}' in project '{1}'"
        ).format(asset_name, project_name)

        if asset_entity:
            subset_entity = io.find_one({
                "type": "subset",
                "name": subset,
                "parent": asset_entity["_id"]
            })

            if subset_entity is None:
                self.log.info("Subset entity does not exist yet.")
                pass

            else:
                version_entity = io.find_one(
                    {
                        "type": "version",
                        "parent": subset_entity["_id"]
                    },
                    sort=[("name", -1)]
                )
                if version_entity:
                    latest_version = version_entity["name"]
        return latest_version
