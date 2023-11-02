import pyblish.api

from openpype.client import get_subset_by_name, get_asset_by_name
import openpype.lib.usdlib as usdlib
from openpype.pipeline.create import get_subset_name


class CollectUsdBootstrap(pyblish.api.InstancePlugin):
    """Collect special Asset/Shot bootstrap instances if those are needed.

    Some specific subsets are intended to be part of the default structure
    of an "Asset" or "Shot" in our USD pipeline. For example, for an Asset
    we layer a Model and Look USD file over each other and expose that in
    a Asset USD file, ready to use.

    On the first publish of any components of an Asset or Shot the
    missing pieces are bootstrapped and generated in the pipeline too. This
    means that on the very first publish of your model the Asset USD file
    will exist too.

    """

    order = pyblish.api.CollectorOrder - 0.4
    label = "Collect USD Bootstrap"
    hosts = ["maya"]
    families = ["usd"]

    def process(self, instance):

        bootstrap = instance.data.get("usd_bootstrap")
        if bootstrap:
            self.log.debug("Add bootstrap for: %s" % bootstrap)
            self.add_bootstrap(instance, bootstrap)

    def add_bootstrap(self, instance, bootstrap):

        project_name = instance.context.data["projectName"]
        asset = get_asset_by_name(project_name, instance.data["asset"])
        assert asset, "Asset must exist: %s" % asset

        # Check which are not about to be created and don't exist yet
        variants_to_create = [bootstrap]

        require_all_layers = instance.data.get("requireAllLayers", False)
        if require_all_layers:
            # USD files load fine in usdview and Houdini even when layered or
            # referenced files do not exist. So by default we don't require
            # the layers to exist.
            contributions = usdlib.PIPELINE.get(bootstrap)
            if contributions:
                variants_to_create.extend(
                    contribution.variant for contribution in contributions
                )

        if not variants_to_create:
            return

        for variant in variants_to_create:
            self.log.info("USD bootstrapping usd-variant: %s", variant)

            subset = get_subset_name(
                family="usd",
                variant=variant.title(),
                task_name=instance.data["task"],
                asset_doc=asset,
                project_name=project_name
            )
            self.log.info(subset)

            defined = self.get_subset_in_context(instance, subset, asset)
            if defined:
                defined.append(instance.id)
                self.log.info("defined..")
                continue

            self.log.debug(
                "Creating USD bootstrap: "
                "{asset} > {subset}".format(
                    bootstrap=bootstrap,
                    asset=asset["name"],
                    subset=subset
                )
            )

            new = instance.context.create_instance(subset)

            # Define subset with
            new.data["subset"] = subset
            new.data["variant"] = variant
            new.data["label"] = "{0} ({1})".format(subset, asset["name"])
            new.data["family"] = "usd"
            new.data["families"] = ["usd", "usd.bootstrap"]
            new.data["icon"] = "link"
            new.data["comment"] = "Automated bootstrap USD file."
            new.data["publishFamilies"] = ["usd"]
            new[:] = [instance.id]

            # Do not allow the user to toggle this instance
            new.data["optional"] = False

            # Copy some data from the instance for which we bootstrap
            for key in ["asset", "task"]:
                new.data[key] = instance.data[key]

    def get_subset_in_context(self, instance, subset, asset):
        """Return whether subset exists in current context."""
        # Allow it to be created during this publish session
        context = instance.context
        for inst in context:
            if (
                inst.data["subset"] == subset
                and inst.data["asset"] == asset["name"]
            ):
                return inst

        # TODO: Since we don't have an asset resolver that will resolve
        #  'to latest' we currently always want to push an update to the
        #  bootstrap explicitly
        # Or, if they already exist in the database we can
        # skip them too.
        # if get_subset_by_name(
        #     project_name, subset, asset["_id"], fields=["_id"]
        # ):
        #     return True
        # return False
