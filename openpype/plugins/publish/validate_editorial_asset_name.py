from pprint import pformat

import pyblish.api

from openpype.pipeline import legacy_io


class ValidateEditorialAssetName(pyblish.api.ContextPlugin):
    """ Validating if editorial's asset names are not already created in db.

    Checking variations of names with different size of caps or with
    or without underscores.
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Editorial Asset Name"
    hosts = [
        "hiero",
        "standalonepublisher",
        "resolve",
        "flame"
    ]

    def process(self, context):

        asset_and_parents = self.get_parents(context)
        self.log.debug("__ asset_and_parents: {}".format(asset_and_parents))

        if not legacy_io.Session:
            legacy_io.install()

        db_assets = list(legacy_io.find(
            {"type": "asset"}, {"name": 1, "data.parents": 1}))
        self.log.debug("__ db_assets: {}".format(db_assets))

        asset_db_docs = {
            str(e["name"]): [str(p) for p in e["data"]["parents"]]
            for e in db_assets}

        self.log.debug("__ project_entities: {}".format(
            pformat(asset_db_docs)))

        assets_missing_name = {}
        assets_wrong_parent = {}
        for asset in asset_and_parents.keys():
            if asset not in asset_db_docs.keys():
                # add to some nonexistent list for next layer of check
                assets_missing_name[asset] = asset_and_parents[asset]
                continue

            if asset_and_parents[asset] != asset_db_docs[asset]:
                # add to some nonexistent list for next layer of check
                assets_wrong_parent[asset] = {
                    "required": asset_and_parents[asset],
                    "already_in_db": asset_db_docs[asset]
                }
                continue

            self.log.info("correct asset: {}".format(asset))

        if assets_missing_name:
            wrong_names = {}
            self.log.debug(
                ">> assets_missing_name: {}".format(assets_missing_name))

            # This will create set asset names
            asset_names = {
                a.lower().replace("_", "") for a in asset_db_docs
            }

            for asset in assets_missing_name:
                _asset = asset.lower().replace("_", "")
                if _asset in asset_names:
                    wrong_names[asset].update(
                        {
                            "required_name": asset,
                            "used_variants_in_db": [
                                a for a in asset_db_docs
                                if a.lower().replace("_", "") == _asset
                            ]
                        }
                    )

            if wrong_names:
                self.log.debug(
                    ">> wrong_names: {}".format(wrong_names))
                raise Exception(
                    "Some already existing asset name variants `{}`".format(
                        wrong_names))

        if assets_wrong_parent:
            self.log.debug(
                ">> assets_wrong_parent: {}".format(assets_wrong_parent))
            raise Exception(
                "Wrong parents on assets `{}`".format(assets_wrong_parent))

    def _get_all_assets(self, input_dict):
        """ Returns asset names in list.

            List contains all asset names including parents
        """
        for key in input_dict.keys():
            # check if child key is available
            if input_dict[key].get("childs"):
                # loop deeper
                self._get_all_assets(
                    input_dict[key]["childs"])
            else:
                self.all_testing_assets.append(key)

    def get_parents(self, context):
        return_dict = {}
        for instance in context:
            asset = instance.data["asset"]
            families = instance.data.get("families", []) + [
                instance.data["family"]
            ]
            # filter out non-shot families
            if "shot" not in families:
                continue

            parents = instance.data["parents"]

            return_dict[asset] = [
                str(p["entity_name"]) for p in parents
                if p["entity_type"].lower() != "project"
            ]
        return return_dict
