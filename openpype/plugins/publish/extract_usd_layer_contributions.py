from operator import attrgetter
import dataclasses
import os

import pyblish.api
from pxr import Sdf

from openpype.lib import (
    TextDef,
    BoolDef,
    UISeparatorDef,
    UILabelDef,
    EnumDef
)
from openpype.lib.usdlib import (
    set_variant_reference,
    setup_asset_layer,
    add_ordered_sublayer,
    construct_ayon_uri,
    get_representation_path_by_ayon_uri,
    get_representation_path_by_names,
    set_layer_defaults
)
from openpype.pipeline import publish


# A contribution defines a contribution into a (department) layer which will
# get layered into the target product, usually the asset or shot.
# We need to at least know what it targets (e.g. where does it go into) and
# in what order (which contribution is stronger?)
# Preferably the bootstrapped data (e.g. the Shot) preserves metadata about
# the contributions so that we can design a system where custom contributions
# outside of the predefined orders are possible to be managed. So that if a
# particular asset requires an extra contribution level, you can add it
# directly from the publisher at that particular order. Future publishes will
# then see the existing contribution and will persist adding it to future
# bootstraps at that order
# TODO: Avoid hardcoded ordering - might need to be set through settings?
LAYER_ORDERS = {
    # asset layers
    "model": 100,
    "assembly": 150,
    "look": 200,
    "rig": 300,
    # shot layers
    "layout": 200,
    "animation": 300,
    "simulation": 400,
    "fx": 500,
    "lighting": 600,
}

# This global toggle is here mostly for debugging purposes and should usually
# be True so that new publishes merge and extend on previous contributions.
# With this enabled a new variant model layer publish would e.g. merge with
# the model layer's other variants nicely, so you can build up an asset by
# individual publishes instead of requiring to republish each contribution
# all the time at the same time
BUILD_INTO_LAST_VERSIONS = True


@dataclasses.dataclass
class Contribution:
    # What are we contributing?
    instance: pyblish.api.Instance  # instance that contributes it

    # Where are we contributing to?
    layer_id: str  # usually the department or task name
    target_product: str = "usdAsset"  # target subset the layer should merge to

    # Variant
    apply_as_variant: bool = False
    variant_set_name: str = ""
    variant_name: str = ""
    variant_is_default: bool = False

    order: int = 0


def get_instance_uri_path(
        instance,
        resolve=True
):
    """Return path for instance's usd representation"""
    context = instance.context
    asset = instance.data["asset"]
    subset = instance.data["subset"]
    project_name = context.data["projectName"]

    # Get the layer's published path
    path = construct_ayon_uri(
        project_name=project_name,
        asset_name=asset,
        product=subset,
        version="latest",
        representation_name="usd"
    )

    # Resolve contribution path
    # TODO: Remove this when Asset Resolver is used
    if resolve:
        path = get_representation_path_by_ayon_uri(
            path,
            # Allow also resolving live to entries from current context
            context=instance.context
        )
        # Ensure `None` for now is also a string
        path = str(path)

    return path


def get_last_publish(instance, representation="usd"):
    return get_representation_path_by_names(
        project_name=instance.context.data["projectName"],
        asset_name=instance.data["asset"],
        subset_name=instance.data["subset"],
        version_name="latest",
        representation_name=representation
    )


def add_representation(instance, name,
                       files, staging_dir, ext=None,
                       output_name=None):
    """Add a representation to publish and integrate.

    A representation must exist of either a single file or a
    single file sequence. It can *not* contain multiple files.

    For the integration to succeed the instance must provide the context
    for asset, frame range, etc. even though the representation can
    override some parts of it.

    Arguments:
        instance (pyblish.api.Instance): Publish instance
        name (str): The representation name
        ext (Optional[str]): Explicit extension for the output
        output_name (Optional[str]): Output name suffix for the
            destination file to ensure the file is unique if
            multiple representations share the same extension.

    Returns:
        dict: Representation data for integration.

    """
    if ext is None:
        # TODO: Use filename
        ext = name

    representation = {
        "name": name,
        "ext": ext,
        "stagingDir": staging_dir,
        "files": files
    }
    if output_name:
        representation["outputName"] = output_name

    instance.data.setdefault("representations", []).append(representation)
    return representation


class CollectUSDLayerContributions(pyblish.api.InstancePlugin,
                                   publish.OpenPypePyblishPluginMixin):
    """Collect the USD Layer Contributions and create dependent instances.

    Our contributions go to the layer

        Instance representation -> Department Layer -> Asset

    So that for example:
        modelMain --> variant 'main' in model.usd -> asset.usd
        modelDamaged --> variant 'damaged' in model.usd -> asset.usd

    """

    order = pyblish.api.CollectorOrder + 0.35
    label = "Collect USD Layer Contributions (Asset/Shot)"
    families = ["usd"]

    def process(self, instance):

        attr_values = self.get_attr_values_from_data(instance.data)
        if not attr_values.get("contribution_enabled"):
            return

        instance.data["subsetGroup"] = (
            instance.data.get("subsetGroup") or "USD Layer"
        )

        # Allow formatting in variant set name and variant name
        data = instance.data.copy()
        data["layer"] = attr_values["contribution_layer"]
        for key in [
            "contribution_variant_set_name",
            "contribution_variant"
        ]:
            attr_values[key] = attr_values[key].format(**data)

        # Define contribution
        order = LAYER_ORDERS.get(attr_values["contribution_layer"], 0)
        contribution = Contribution(
            instance=instance,
            layer_id=attr_values["contribution_layer"],
            target_product=attr_values["contribution_target_product"],
            apply_as_variant=attr_values["contribution_apply_as_variant"],
            variant_set_name=attr_values["contribution_variant_set_name"],
            variant_name=attr_values["contribution_variant"],
            variant_is_default=attr_values["contribution_variant_is_default"],
            order=order
        )
        asset_subset = contribution.target_product
        layer_subset = "{}_{}".format(asset_subset, contribution.layer_id)

        # Layer contribution instance
        layer_instance = self.get_or_create_instance(
            subset=layer_subset,
            variant=contribution.layer_id,
            source_instance=instance,
            families=["usd", "usdLayer"],
        )
        layer_instance.data.setdefault("usd_contributions", []).append(
            contribution
        )
        layer_instance.data["usd_layer_id"] = contribution.layer_id
        layer_instance.data["usd_layer_order"] = contribution.order

        layer_instance.data["subsetGroup"] = (
            instance.data.get("subsetGroup") or "USD Layer"
        )

        # Asset/Shot contribution instance
        target_instance = self.get_or_create_instance(
            subset=asset_subset,
            variant=asset_subset,
            source_instance=layer_instance,
            families=["usd", "usdAsset"],
        )
        target_instance.data["contribution_target_product_init"] = attr_values[
            "contribution_target_product_init"
        ]

        self.log.info(
            f"Contributing {instance.data['subset']} to "
            f"{layer_subset} -> {asset_subset}"
        )

    def find_instance(self, context, data, ignore_instance):
        for instance in context:
            if instance is ignore_instance:
                continue

            if all(instance.data.get(key) == value
                   for key, value in data.items()):
                return instance

    def get_or_create_instance(self,
                               subset,
                               variant,
                               source_instance,
                               families):
        """Get or create the instance matching the subset/variant.

        The source instance will be used to do additional matching, like
        ensuring it's a subset for the same asset and task. If the instance
        already exists in the `context` then the existing one is returned.

        For each source instance this is called the sources will be appended
        to a `instance.data["source_instances"]` list on the returned instance.

        Arguments:
            subset (str): Subset name
            variant (str): Variant name
            source_instance (pyblish.api.Instance): Source instance to
                be related to for asset, task.
            families (list): The families required to be set on the instance.

        Returns:
            pyblish.api.Instance: The resulting instance.

        """

        # Potentially the instance already exists due to multiple instances
        # contributing to the same layer or asset - so we first check for
        # existence
        context = source_instance.context

        # Required matching vars
        data = {
            "asset": source_instance.data["asset"],
            "task": source_instance.data.get("task"),
            "subset": subset,
            "variant": variant,
            "families": families
        }
        existing_instance = self.find_instance(context, data,
                                               ignore_instance=source_instance)
        if existing_instance:
            existing_instance.append(source_instance.id)
            existing_instance.data["source_instances"].append(source_instance)
            return existing_instance

        # Otherwise create the instance
        new_instance = context.create_instance(name=subset)
        new_instance.data.update(data)

        new_instance.data["label"] = (
            "{0} ({1})".format(subset, new_instance.data["asset"])
        )
        new_instance.data["family"] = "usd"
        new_instance.data["icon"] = "link"
        new_instance.data["comment"] = "Automated bootstrap USD file."
        new_instance.append(source_instance.id)
        new_instance.data["source_instances"] = [source_instance]

        return new_instance

    @classmethod
    def get_attribute_defs(cls):

        return [
            UISeparatorDef("usd_container_settings1"),
            UILabelDef(label="<b>USD Contribution</b>"),
            BoolDef("contribution_enabled",
                    label="Enable",
                    tooltip=(
                        "When enabled this publish instance will be added "
                        "into a department layer into a target product, "
                        "usually an asset or shot.\n"
                        "When disabled this publish instance will not be "
                        "added into another USD file and remain as is.\n"
                        "In both cases the USD data itself is free to have "
                        "references and sublayers of its own."
                    ),
                    default=True),
            TextDef("contribution_target_product",
                    label="Target product",
                    tooltip=(
                        "The target product the contribution should be added "
                        "to. Usually this is the asset or shot product.\nThe "
                        "department layer will be added to this product, and "
                        "the contribution itself will be added to the "
                        "department layer."
                    ),
                    default="usdAsset"),
            EnumDef("contribution_target_product_init",
                    label="Initialize as",
                    tooltip=(
                        "The target product's USD file will be initialized "
                        "based on this type if there's no existing USD of "
                        "that product yet.\nIf there's already an existing "
                        "product with the name of the 'target product' this "
                        "setting will do nothing."
                    ),
                    items=["asset", "shot"],
                    default="asset"),

            # Asset layer, e.g. model.usd, look.usd, rig.usd
            EnumDef("contribution_layer",
                    label="Add to department layer",
                    tooltip=(
                        "The layer the contribution should be made to in the "
                        "target product.\nThe layers have their own "
                        "predefined ordering.\nA higher order (further down "
                        "the list) will contribute as a stronger opinion."
                    ),
                    items=list(LAYER_ORDERS.keys()),
                    default="model"),
            BoolDef("contribution_apply_as_variant",
                    label="Add as variant",
                    tooltip=(
                        "When enabled the contribution to the department "
                        "layer will be added as a variant where the variant "
                        "on the default root prim will be added as a "
                        "reference.\nWhen disabled the contribution will be "
                        "appended to as a sublayer to the department layer "
                        "instead."
                    ),
                    default=True),
            TextDef("contribution_variant_set_name",
                    label="Variant Set Name",
                    default="{layer}"),
            TextDef("contribution_variant",
                    label="Variant Name",
                    default="{variant}"),
            BoolDef("contribution_variant_is_default",
                    label="Set as default variant selection",
                    tooltip=(
                        "Whether to set this instance's variant name as the "
                        "default selected variant name for the variant set.\n"
                        "It is always expected to be enabled for only one "
                        "variant name in the variant set.\n"
                        "The behavior is unpredictable if multiple instances "
                        "for the same variant set have this enabled."
                    ),
                    default=False),
            UISeparatorDef("usd_container_settings3"),
        ]


class ExtractUSDLayerContribution(publish.Extractor):

    families = ["usdLayer"]
    label = "Extract USD Layer Contributions (Asset/Shot)"
    order = pyblish.api.ExtractorOrder + 0.45

    def process(self, instance):
        from pxr import Sdf

        asset = instance.data["asset"]
        product = instance.data["subset"]
        self.log.debug(f"Building layer: {asset} > {product}")

        path = get_last_publish(instance)
        if path and BUILD_INTO_LAST_VERSIONS:
            sdf_layer = Sdf.Layer.OpenAsAnonymous(path)
            default_prim = sdf_layer.defaultPrim
        else:
            default_prim = asset
            sdf_layer = Sdf.Layer.CreateAnonymous()
            set_layer_defaults(sdf_layer, default_prim=default_prim)

        contributions = instance.data.get("usd_contributions", [])
        for contribution in sorted(contributions, key=attrgetter("order")):
            path = get_instance_uri_path(contribution.instance)
            if contribution.apply_as_variant:
                # Add contribution as variants to their layer subsets
                self.log.debug(f"Adding variant: {contribution}")
                prim_path = f"/{default_prim}"
                variant_set_name = contribution.variant_set_name
                variant_name = contribution.variant_name
                set_variant_reference(
                    sdf_layer,
                    prim_path=prim_path,
                    variant_selections=[(variant_set_name, variant_name)],
                    path=path
                )
                prim = sdf_layer.GetPrimAtPath(prim_path)

                # Set default variant selection
                if contribution.variant_is_default or \
                        variant_set_name not in prim.variantSelections:
                    prim.variantSelections[variant_set_name] = variant_name

            else:
                # Sublayer source file
                self.log.debug(f"Adding sublayer: {contribution}")

                # This replaces existing versions of itself so that
                # republishing does not continuously add more versions of the
                # same subset
                subset = contribution.instance.data["subset"]
                add_ordered_sublayer(
                    layer=sdf_layer,
                    contribution_path=path,
                    layer_id=subset,
                    order=None,  # unordered
                    add_sdf_arguments_metadata=True
                )

        # Save the file
        staging_dir = self.staging_dir(instance)
        filename = f"{instance.name}.usd"
        filepath = os.path.join(staging_dir, filename)
        sdf_layer.Export(filepath, args={"format": "usda"})

        add_representation(
            instance,
            name="usd",
            files=filename,
            staging_dir=staging_dir
        )


class ExtractUSDAssetContribution(publish.Extractor):

    families = ["usdAsset"]
    label = "Extract USD Asset/Shot Contributions"
    order = ExtractUSDLayerContribution.order + 0.01

    def process(self, instance):
        from pxr import Sdf

        asset = instance.data["asset"]
        subset = instance.data["subset"]
        self.log.debug(f"Building asset: {asset} > {subset}")

        # Contribute layers to asset
        # Use existing asset and add to it, or initialize a new asset layer
        path = get_last_publish(instance)
        payload_layer = None
        if path and BUILD_INTO_LAST_VERSIONS:
            # If there's a payload file, put it in the payload instead
            folder = os.path.dirname(path)
            payload_path = os.path.join(folder, "payload.usd")
            if os.path.exists(payload_path):
                payload_layer = Sdf.Layer.OpenAsAnonymous(payload_path)

            asset_layer = Sdf.Layer.OpenAsAnonymous(path)
        else:
            # If not existing publish of this product yet then we initialize
            # the layer as either a default asset or shot structure.
            init_type = instance.data["contribution_target_product_init"]
            asset_layer, payload_layer = self.init_layer(asset_name=asset,
                                                         init_type=init_type)

        target_layer = payload_layer if payload_layer else asset_layer

        # Get unique layer instances (remove duplicate entries)
        processed_ids = set()
        layer_instances = []
        for layer_inst in instance.data["source_instances"]:
            if layer_inst.id in processed_ids:
                continue
            layer_instances.append(layer_inst)
            processed_ids.add(layer_inst.id)

        # Insert the layer in contributions order
        def sort_by_order(instance):
            return instance.data["usd_layer_order"]

        for layer_instance in sorted(layer_instances,
                                     key=sort_by_order,
                                     reverse=True):

            layer_id = layer_instance.data["usd_layer_id"]
            order = layer_instance.data["usd_layer_order"]

            path = get_instance_uri_path(instance=layer_instance)
            add_ordered_sublayer(target_layer,
                                 contribution_path=path,
                                 layer_id=layer_id,
                                 order=order,
                                 # Add the sdf argument metadata which allows
                                 # us to later detect whether another path
                                 # has the same layer id, so we can replace it
                                 # it.
                                 add_sdf_arguments_metadata=True)

        # Save the file
        staging_dir = self.staging_dir(instance)
        filename = f"{instance.name}.usd"
        filepath = os.path.join(staging_dir, filename)
        asset_layer.Export(filepath, args={"format": "usda"})

        add_representation(
            instance,
            name="usd",
            files=filename,
            staging_dir=staging_dir
        )

        if payload_layer:
            payload_path = os.path.join(staging_dir, "payload.usd")
            payload_layer.Export(payload_path, args={"format": "usda"})
            self.add_relative_file(instance, payload_path)

    def init_layer(self, asset_name, init_type):
        """Initialize layer if no previous version exists"""

        if init_type == "asset":
            asset_layer = Sdf.Layer.CreateAnonymous()
            created_layers = setup_asset_layer(asset_layer, asset_name,
                                               force_add_payload=True,
                                               set_payload_path=True)
            payload_layer = created_layers[0].layer
            return asset_layer, payload_layer

        elif init_type == "shot":
            shot_layer = Sdf.Layer.CreateAnonymous()
            set_layer_defaults(shot_layer, default_prim=None)
            return shot_layer, None

        else:
            raise ValueError(
                "USD Target Product contribution can only initialize "
                "as 'asset' or 'shot', got: '{}'".format(init_type)
            )

    def add_relative_file(self, instance, source, staging_dir=None):
        """Add transfer for a relative path form staging to publish dir.

        Unlike files in representations, the file will not be renamed and
        will be ingested one-to-one into the publish directory.

        Note: This file does not get registered as a representation, because
          representation files always get renamed by the publish template
          system. These files get included in the `representation["files"]`
          info with all the representations of the version - and thus will
          appear multiple times per version.

        """
        # TODO: It can be nice to force a particular representation no matter
        #  what to adhere to a certain filename on integration because e.g. a
        #  particular file format relies on that file named like that or alike
        #  and still allow regular registering with the database as a file of
        #  the version. As such we might want to tweak integrator logic?
        if staging_dir is None:
            staging_dir = self.staging_dir(instance)
        publish_dir = instance.data["publishDir"]

        relative_path = os.path.relpath(source, staging_dir)
        destination = os.path.join(publish_dir, relative_path)
        destination = os.path.normpath(destination)

        transfers = instance.data.setdefault("transfers", [])
        self.log.debug(f"Adding relative file {source} -> {relative_path}")
        transfers.append((source, destination))
