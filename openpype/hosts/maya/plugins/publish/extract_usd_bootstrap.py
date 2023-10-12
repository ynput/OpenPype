import os

import pyblish.api
from openpype.pipeline import publish


class ExtractBootstrapUSD(publish.Extractor):
    """Extract in-memory bootstrap USD files for Assets and Shots.

    See `collect_usd_bootstrap_asset.py` for more details.

    """

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Bootstrap USD"
    hosts = ["houdini", "maya"]
    targets = ["local"]
    families = ["usd.bootstrap"]

    def process(self, instance):
        from openpype.lib import usdlib

        staging_dir = self.staging_dir(instance)
        filename = "{subset}.usd".format(**instance.data)
        filepath = os.path.join(staging_dir, filename)
        self.log.info("Bootstrap USD '%s' to '%s'" % (filename, staging_dir))

        subset = instance.data["subset"]
        if subset == "usdAsset":
            # Asset
            steps = usdlib.PIPELINE["asset"]
            layers = self.get_usd_master_paths(steps, instance)
            usdlib.create_asset(filepath,
                                asset_name=instance.data["asset"],
                                reference_layers=layers)

        elif subset == "usdShot":
            # Shot
            steps = usdlib.PIPELINE["shot"]
            layers = self.get_usd_master_paths(steps, instance)
            usdlib.create_shot(filepath,
                               layers=layers)

        elif subset == "usdModel":
            variant_subsets = instance.data["variantSubsets"]
            usdlib.create_model(filepath,
                                asset=instance.data["asset"],
                                variant_subsets=variant_subsets)

        elif subset == "usdShade":
            variant_subsets = instance.data["variantSubsets"]
            usdlib.create_shade(filepath,
                                asset=instance.data["asset"],
                                variant_subsets=variant_subsets)

        elif subset in usdlib.PIPELINE["asset"]:
            # Asset layer
            # Generate the stub files with root primitive
            # TODO: implement
            #usdlib.create_stub_usd(filepath)
            raise NotImplementedError("TODO")

        elif subset in usdlib.PIPELINE["shot"]:
            # Shot Layer
            # Generate the stub file for an Sdf Layer
            # TODO: implement
            #usdlib.create_stub_usd_sdf_layer(filepath)
            raise NotImplementedError("TODO")

        else:
            raise RuntimeError("No bootstrap method "
                               "available for: %s" % subset)

        representations = instance.data.setdefault("representations", [])
        representations.append({
            "name": "usd",
            "ext": "usd",
            "files": filename,
            "stagingDir": staging_dir
        })

    def get_usd_master_paths(self, subsets, instance):

        raise NotImplementedError("TODO")
        # TODO: Implement the retrieval of the right paths
        # TODO: preferably with AYON asset resolver these would be AYON URIs
        # asset = instance.data["asset"]
        #
        # template = _get_project_publish_template()
        # layer_paths = []
        # for layer in subsets:
        #     layer_path = self._get_usd_master_path(
        #         subset=layer,
        #         asset=asset,
        #         template=template
        #     )
        #     layer_paths.append(layer_path)
        #     self.log.info("Asset references: %s" % layer_path)
        #
        # return layer_paths
