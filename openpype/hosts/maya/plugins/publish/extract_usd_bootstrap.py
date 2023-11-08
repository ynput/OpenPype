import os
import copy
import operator

import pyblish.api
from openpype.pipeline import publish
from openpype.pipeline.create import get_subset_name


def get_instance_expected_output_path(instance, representation_name, ext=None):

    if ext is None:
        ext = representation_name

    context = instance.context
    anatomy = context.data["anatomy"]
    path_template_obj = anatomy.templates_obj["publish"]["path"]
    template_data = copy.deepcopy(instance.data["anatomyData"])
    template_data.update({
        "ext": ext,
        "representation": representation_name,
        "subset": instance.data["subset"],
        "asset": instance.data["asset"],
        "variant": instance.data["variant"],
        "version": instance.data["version"]
    })

    template_filled = path_template_obj.format_strict(template_data)
    return os.path.normpath(template_filled)


class ExtractBootstrapUSD(publish.Extractor):
    """Extract in-memory bootstrap USD files for Assets and Shots.

    See `collect_usd_bootstrap_asset.py` for more details.

    """

    order = pyblish.api.ExtractorOrder + 0.2
    label = "Bootstrap USD"
    hosts = ["houdini", "maya"]
    targets = ["local"]
    families = ["usd.bootstrap"]

    def process(self, instance):
        from openpype.lib import usdlib

        staging_dir = self.staging_dir(instance)
        filename = "{subset}.usd".format(**instance.data)
        filepath = os.path.join(staging_dir, filename)
        self.log.debug("Bootstrap USD '%s' to '%s'" % (filename, staging_dir))

        subset = instance.data["subset"]
        if subset == "usdAsset":
            # Asset
            contributions = usdlib.PIPELINE["asset"]
            layers = self.get_contribution_paths(contributions, instance)
            created_layers = usdlib.create_asset(
                filepath,
                asset_name=instance.data["asset"],
                reference_layers=layers
            )

            # Ignore the first layer which is the asset layer that is not
            # relative to itself
            created_layers = created_layers[1:]
            for layer in created_layers:
                self.add_relative_file(instance, layer.get_full_path())

        elif subset == "usdShot":
            # Shot
            steps = usdlib.PIPELINE["shot"]
            layers = self.get_contribution_paths(steps, instance)
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

    def add_relative_file(self, instance, source, staging_dir=None):
        """Add transfer for a relative path form staging to publish dir.

        Unlike files in representations, the file will not be renamed and
        will be ingested one-to-one into the publish directory.

        """
        if staging_dir is None:
            staging_dir = self.staging_dir(instance)
        publish_dir = instance.data["publishDir"]

        relative_path = os.path.relpath(source, staging_dir)
        destination = os.path.join(publish_dir, relative_path)
        destination = os.path.normpath(destination)

        transfers = instance.data.setdefault("transfers", [])
        self.log.debug(f"Adding relative file {source} -> {relative_path}")
        transfers.append((source, destination))

    def get_contribution_paths(self, contributions, instance):
        """Return the asset paths (filepath) for the contributions.

        If the contribution is not found in the current publish context nor
        as an existing entity in the database it will be silently excluded
        from the result.

        """
        # TODO: create paths for AYON asset resolver as AYON URIs
        # TODO: Get any contributions from the last version of the instance
        #   so that we ensure we're always adding into the last existing
        #   version instead of replacing
        # last_contributions = self.get_last_contributions(instance)
        # for contribution in last_contributions:
        #     if contribution not in contributions:
        #         contributions.append(last_contributions)
        contributions.sort(key=operator.attrgetter("order"))

        # Define subsets from family + variant
        subsets = []
        for contribution in contributions:
            subset = get_subset_name(
                family=contribution.family,
                variant=contribution.variant,
                task_name=instance.data["task"],
                asset_doc=instance.data["assetEntity"],
                project_name=instance.context.data["projectName"]
            )
            subsets.append(subset)

        # Find all subsets in the current publish session
        result = self.get_representation_path_per_subset_in_publish(subsets,
                                                                    instance)

        # Find last existing version for those not in current publish session
        missing = [subset for subset in subsets if subset not in result]
        if missing:
            existing = self.get_existing_representation_path_per_subset(
                missing, instance
            )
            result.update(existing)

        order = {subset: index for index, subset in enumerate(subsets)}
        result = {
            subset: path for subset, path in sorted(result.items(),
                                                    key=lambda x: order[x[0]])
        }

        self.log.debug(
            "Found subsets to contribute: {}".format(", ".join(result))
        )
        assert result, "Must have one subset to contribute at least"
        return list(result.values())

    def get_representation_path_per_subset_in_publish(self, subsets, instance):
        """Get path for representations in the current publish session

        Given the input subset names compute all destination paths for
        active instances in the current publish session that will be
        ingested as the new versions for those publishes.

        This assumes those subset will generate a USD representation and
        must already have it added in `instance.data["representations"]`

        """
        asset = instance.data["asset"]
        result = {}
        context = instance.context
        self.log.debug(f"Looking for subsets: {subsets}")
        for other_instance in context:
            if other_instance is instance:
                continue

            if not other_instance.data.get("active", True):
                continue

            if not other_instance.data.get("publish", True):
                continue

            if other_instance.data["asset"] != asset:
                continue

            if other_instance.data["subset"] not in subsets:
                continue

            subset = other_instance.data["subset"]

            # Make sure the instance has a `usd` representation; note that
            # usually the extractors add these so we want this plug-in to
            # run quite late as an extractor to ensure others have run before
            if not any(
                repre["name"] == "usd" for repre in
                other_instance.data.get("representations", [])
            ):
                raise RuntimeError(
                    "Missing `usd` representation on instance with "
                    "subset {}".format(subset)
                )

            path = get_instance_expected_output_path(
                other_instance, representation_name="usd"
            )
            result[subset] = path

        return result

    def get_existing_representation_path_per_subset(self, subsets, instance):
        """Get last version for subsets in the database

        Given the input subset names find all latest existing version in the
        database and retrieve their `usd` representation paths.

        """
        context = instance.context
        project_name = context.data["projectName"]
        asset_entity = instance.data["assetEntity"]

        from openpype.pipeline import get_representation_path
        from openpype.client import (
            get_subsets,
            get_last_versions,
            get_representations
        )

        def to_id(entity):
            return entity["_id"]

        subsets_docs = list(
            get_subsets(project_name,
                        subset_names=subsets,
                        asset_ids=[asset_entity["_id"]])
        )
        if not subsets_docs:
            return {}

        version_docs = list(get_last_versions(
            project_name,
            subset_ids=map(to_id, subsets_docs)
        ).values())
        if not version_docs:
            return {}

        representation_docs = list(get_representations(
            project_name,
            version_ids=map(to_id, version_docs),
            representation_names=["usd"]
        ))
        if not representation_docs:
            return {}

        result = {}
        versions_by_id = {v["_id"]: v for v in version_docs}
        subsets_by_id = {s["_id"]: s for s in subsets_docs}
        for representation in representation_docs:
            version_doc = versions_by_id[representation["parent"]]
            subset_doc = subsets_by_id[version_doc["parent"]]
            subset = subset_doc["name"]

            self.log.debug(
                "Found existing subset '{}' version 'v{:03d}'".format(
                    subset, version_doc["name"]
            ))

            path = get_representation_path(representation)
            result[subset] = path

        return result
