import os

import pyblish.api
from avalon import io

from pprint import pformat


class AppendCelactionAudio(pyblish.api.ContextPlugin):

    label = "Colect Audio for publishing"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        self.log.info('Collecting Audio Data')
        asset_entity = context.data["assetEntity"]

        # get all available representations
        subsets = self.get_subsets(asset_entity["name"],
                                   representations=["audio", "wav"]
                                   )
        self.log.info(f"subsets is: {pformat(subsets)}")

        if not subsets.get("audioMain"):
            raise AttributeError("`audioMain` subset does not exist")

        reprs = subsets.get("audioMain", {}).get("representations", [])
        self.log.info(f"reprs is: {pformat(reprs)}")

        repr = next((r for r in reprs), None)
        if not repr:
            raise "Missing `audioMain` representation"
        self.log.info(f"represetation is: {repr}")

        audio_file = repr.get('data', {}).get('path', "")

        if os.path.exists(audio_file):
            context.data["audioFile"] = audio_file
            self.log.info(
                'audio_file: {}, has been added to context'.format(audio_file))
        else:
            self.log.warning("Couldn't find any audio file on Ftrack.")

    def get_subsets(
        self,
        asset_name,
        representations,
        regex_filter=None,
        version=None
    ):
        """
        Query subsets with filter on name.

        The method will return all found subsets and its defined version
        and subsets. Version could be specified with number. Representation
        can be filtered.

        Arguments:
            asset_name (str): asset (shot) name
            regex_filter (raw): raw string with filter pattern
            version (str or int): `last` or number of version
            representations (list): list for all representations

        Returns:
            dict: subsets with version and representaions in keys
        """

        # query asset from db
        asset_io = io.find_one({"type": "asset", "name": asset_name})

        # check if anything returned
        assert asset_io, (
            "Asset not existing. Check correct name: `{}`").format(asset_name)

        # create subsets query filter
        filter_query = {"type": "subset", "parent": asset_io["_id"]}

        # add reggex filter string into query filter
        if regex_filter:
            filter_query["name"] = {"$regex": r"{}".format(regex_filter)}

        # query all assets
        subsets = list(io.find(filter_query))

        assert subsets, ("No subsets found. Check correct filter. "
                         "Try this for start `r'.*'`: "
                         "asset: `{}`").format(asset_name)

        output_dict = {}
        # Process subsets
        for subset in subsets:
            if not version:
                version_sel = io.find_one(
                    {
                        "type": "version",
                        "parent": subset["_id"]
                    },
                    sort=[("name", -1)]
                )
            else:
                assert isinstance(version, int), (
                    "version needs to be `int` type"
                )
                version_sel = io.find_one({
                    "type": "version",
                    "parent": subset["_id"],
                    "name": int(version)
                })

            find_dict = {"type": "representation",
                         "parent": version_sel["_id"]}

            filter_repr = {"name": {"$in": representations}}

            find_dict.update(filter_repr)
            repres_out = [i for i in io.find(find_dict)]

            if len(repres_out) > 0:
                output_dict[subset["name"]] = {"version": version_sel,
                                               "representations": repres_out}

        return output_dict
