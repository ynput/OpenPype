import dataclasses
import os
import copy
import re
import logging
from urllib.parse import urlparse, parse_qs
from collections import namedtuple

try:
    from pxr import Usd, UsdGeom, Sdf, Kind
except ImportError:
    # Allow to fall back on Multiverse 6.3.0+ pxr usd library
    from mvpxr import Usd, UsdGeom, Sdf, Kind

from openpype.client import (
    get_asset_by_name,
    get_subset_by_name,
    get_representation_by_name,
    get_hero_version_by_subset_id,
    get_version_by_name,
    get_last_version_by_subset_id
)
from openpype.pipeline import (
    get_current_project_name,
    get_representation_path
)

log = logging.getLogger(__name__)


# A contribution defines a layer or references into a particular bootstrap.
# The idea is that contributions can be bootstrapped so, that for example
# the bootstrap of a look variant would update the look bootstrap which updates
# the asset bootstrap. The exact data structure to access and configure these
# easily is still to be defined, but we need to at least know what it targets
# (e.g. where does it go into) and in what order (which contribution is stronger?)
# Preferably the bootstrapped data (e.g. the Shot) preserves metadata about
# the contributions so that we can design a system where custom contributions
# outside of the predefined orders are possible to be managed. So that if a
# particular asset requires an extra contribution level, you can add it
# directly from the publisher at that particular order. Future publishes will
# then see the existing contribution and will persist adding it to future
# bootstraps at that order
Contribution = namedtuple("Contribution",
                          ("family", "variant", "order", "step"))


@dataclasses.dataclass
class Layer:
    layer: Sdf.Layer
    path: str
    # Allow to anchor a layer to another so that when the layer would be
    # exported it'd write itself out relative to its anchor
    anchor: 'Layer' = None

    @property
    def identifier(self):
        return self.layer.identifier

    def get_full_path(self):
        """Return full path relative to the anchor layer"""
        if not os.path.isabs(self.path) and self.anchor:
            anchor_path = self.anchor.get_full_path()
            root = os.path.dirname(anchor_path)
            return os.path.normpath(os.path.join(root, self.path))
        else:
            return self.path

    def export(self, path=None, args=None):
        """Save the layer"""
        if path is None:
            path = self.get_full_path()

        if args is None:
            args = self.layer.GetFileFormatArguments()

        self.layer.Export(path, args=args)

    @classmethod
    def create_anonymous(cls, path, tag="LOP", anchor=None):
        sdf_layer = Sdf.Layer.CreateAnonymous(tag)
        return cls(layer=sdf_layer, path=path, anchor=anchor)


# The predefined steps order used for bootstrapping USD Shots and Assets.
# These are ordered in order from strongest to weakest opinions, like in USD.
PIPELINE = {
    "shot": [
        Contribution(family="usd", variant="lighting", order=500, step="lighting"),
        Contribution(family="usd", variant="fx", order=400, step="fx"),
        Contribution(family="usd", variant="simulation", order=300, step="simulation"),
        Contribution(family="usd", variant="animation", order=200, step="animation"),
        Contribution(family="usd", variant="layout", order=100, step="layout"),
    ],
    "asset": [
        Contribution(family="usd.rig", variant="main", order=300, step="rig"),
        Contribution(family="usd.look", variant="main", order=200, step="look"),
        Contribution(family="usd.model", variant="main", order=100, step="model")
    ],
}


def setup_asset_layer(
        layer,
        asset_name,
        reference_layers=None,
        kind=Kind.Tokens.component,
        define_class=True
):
    """
    Adds an asset prim to the layer with the `reference_layers` added as
    references for e.g. geometry and shading.

    The referenced layers will be moved into a separate `./payload.usd` file
    that the asset file uses to allow deferred loading of the heavier
    geometrical data. An example would be:

    asset.usd      <-- out filepath
      payload.usd  <-- always automatically added in-between
        look.usd   <-- reference layer 0 from `reference_layers` argument
        model.usd  <-- reference layer 1 from `reference_layers` argument

    If `define_class` is enabled then a `/__class__/{asset_name}` class
    definition will be created that the root asset inherits from

    Examples:
        >>> create_asset("/path/to/asset.usd",
        >>>              asset_name="test",
        >>>              reference_layers=["./model.usd", "./look.usd"])

    Returns:
        List[Tuple[Sdf.Layer, str]]: List of created layers with their
            preferred output save paths.

    Args:
        layer (Sdf.Layer): Layer to set up the asset structure for.
        asset_name (str): The name for the Asset identifier and default prim.
        reference_layers (list): USD Files to reference in the asset.
            Note that the bottom layer (first file, like a model) would
            be last in the list. The strongest layer will be the first
            index.
        kind (pxr.Kind): A USD Kind for the root asset.
        define_class: Define a `/__class__/{asset_name}` class which the
            root asset prim will inherit from.

    """
    # Define root prim for the asset and make it the default for the stage.
    prim_name = asset_name

    if define_class:
        class_prim = Sdf.PrimSpec(
            layer.pseudoRoot,
            "__class__",
            Sdf.SpecifierClass,
        )
        _class_asset_prim = Sdf.PrimSpec(
            class_prim,
            prim_name,
            Sdf.SpecifierClass,
        )

    asset_prim = Sdf.PrimSpec(
        layer.pseudoRoot,
        prim_name,
        Sdf.SpecifierDef,
        "Xform"
    )

    if define_class:
        asset_prim.inheritPathList.prependedItems[:] = [
            "/__class__/{}".format(prim_name)
        ]

    # Define Kind
    # Usually we will "loft up" the kind authored into the exported geometry
    # layer rather than re-stamping here; we'll leave that for a later
    # tutorial, and just be explicit here.
    asset_prim.kind = kind

    # Set asset info
    asset_prim.assetInfo["name"] = asset_name
    asset_prim.assetInfo["identifier"] = "%s/%s.usd" % (asset_name, asset_name)

    # asset.assetInfo["version"] = asset_version
    set_layer_defaults(layer, default_prim=asset_name)

    created_layers = []

    # Add references to the  asset prim
    if reference_layers:
        # Create a relative payload file to filepath through which we sublayer
        # the heavier payloads
        # Prefix with `LOP` just so so that if Houdini ROP were to save
        # the nodes it's capable of exporting with explicit save path
        payload_layer = Sdf.Layer.CreateAnonymous("LOP",
                                                  args={"format": "usda"})
        set_layer_defaults(payload_layer, default_prim=asset_name)
        created_layers.append(Layer(layer=payload_layer,
                                    path="./payload.usd"))

        # Add sublayers to the payload layer
        # Note: Sublayering is tricky because it requires that the sublayers
        #   actually define the path at defaultPrim otherwise the payload
        #   reference will not find the defaultPrim and turn up empty.
        for ref_layer in reference_layers:
            payload_layer.subLayerPaths.append(ref_layer)

        # Add payload
        asset_prim.payloadList.prependedItems[:] = [
            Sdf.Payload(assetPath=payload_layer.identifier)
        ]

    return created_layers


def create_asset(
        filepath,
        asset_name,
        reference_layers=None,
        kind=Kind.Tokens.component,
        define_class=True
):
    """Creates and saves a prepared asset stage layer.

    Creates an asset file that consists of a top level asset prim, asset info
     and references in the provided `reference_layers`.

    Returns:
        list: Created layers

    """
    # Also see create_asset.py in PixarAnimationStudios/USD endToEnd example

    sdf_layer = Sdf.Layer.CreateAnonymous()
    layer = Layer(layer=sdf_layer, path=filepath)

    created_layers = setup_asset_layer(
            layer=sdf_layer,
            asset_name=asset_name,
            reference_layers=reference_layers,
            kind=kind,
            define_class=define_class
    )
    for created_layer in created_layers:
        created_layer.anchor = layer
        created_layer.export()

        # Update the dependency on the base layer
        sdf_layer.UpdateCompositionAssetDependency(
            created_layer.identifier, created_layer.get_full_path()
        )

    # Make the layer ascii - good for readability, plus the file is small
    log.debug("Creating asset at %s", filepath)
    layer.export(args={"format": "usda"})

    return [layer] + created_layers


def create_shot(filepath, layers, create_layers=False):
    """Create a shot with separate layers for departments.

    Examples:
        >>> create_shot("/path/to/shot.usd",
        >>>             layers=["lighting.usd", "fx.usd", "animation.usd"])
        "/path/to/shot.usd"

    Args:
        filepath (str): Filepath where the asset.usd file will be saved.
        layers (list): When provided this will be added verbatim in the
            subLayerPaths layers. When the provided layer paths do not exist
            they are generated using Sdf.Layer.CreateNew
        create_layers (bool): Whether to create the stub layers on disk if
            they do not exist yet.

    Returns:
        str: The saved shot file path

    """
    # Also see create_shot.py in PixarAnimationStudios/USD endToEnd example
    root_layer = Sdf.Layer.CreateAnonymous()

    created_layers = [root_layer]
    for layer_path in layers:
        if create_layers and not os.path.exists(layer_path):
            # We use the Sdf API here to quickly create layers.  Also, we're
            # using it as a way to author the subLayerPaths as there is no
            # way to do that directly in the Usd API.
            layer_folder = os.path.dirname(layer_path)
            if not os.path.exists(layer_folder):
                os.makedirs(layer_folder)

            new_layer = Sdf.Layer.CreateNew(layer_path)
            created_layers.append(new_layer)

        root_layer.subLayerPaths.append(layer_path)

    set_layer_defaults(root_layer)
    log.debug("Creating shot at %s" % filepath)
    root_layer.Export(filepath, args={"format": "usda"})

    return created_layers


def create_model(filename, asset, variant_subsets):
    """Create a USD Model file.

    For each of the variation paths it will payload the path and set its
    relevant variation name.

    """

    project_name = get_current_project_name()
    asset_doc = get_asset_by_name(project_name, asset)
    assert asset_doc, "Asset not found: %s" % asset

    variants = []
    for subset in variant_subsets:
        prefix = "usdModel"
        if subset.startswith(prefix):
            # Strip off `usdModel_`
            variant = subset[len(prefix):]
        else:
            raise ValueError(
                "Model subsets must start " "with usdModel: %s" % subset
            )

        path = get_representation_path_by_names(
            project_name=project_name,
            asset_name=asset_doc,
            subset_name=subset,
            version_name="latest",
            representation_name="usd"
        )
        if path:
            variants.append((variant, path))

    stage = _create_variants_file(
        filename,
        variants=variants,
        variantset="model",
        variant_prim="/root",
        reference_prim="/root/geo",
        as_payload=True,
    )

    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    # modelAPI = Usd.ModelAPI(root_prim)
    # modelAPI.SetKind(Kind.Tokens.component)

    # See http://openusd.org/docs/api/class_usd_model_a_p_i.html#details
    # for more on assetInfo
    # modelAPI.SetAssetName(asset)
    # modelAPI.SetAssetIdentifier(asset)

    stage.GetRootLayer().Save()


def create_shade(filename, asset, variant_subsets):
    """Create a master USD shade file for an asset.

    For each available model variation this should generate a reference
    to a `usdShade_{modelVariant}` subset.

    """

    project_name = get_current_project_name()
    asset_doc = get_asset_by_name(project_name, asset)
    assert asset_doc, "Asset not found: %s" % asset

    variants = []

    for subset in variant_subsets:
        prefix = "usdModel"
        if subset.startswith(prefix):
            # Strip off `usdModel_`
            variant = subset[len(prefix):]
        else:
            raise ValueError(
                "Model subsets must start " "with usdModel: %s" % subset
            )

        shade_subset = re.sub("^usdModel", "usdShade", subset)
        path = get_representation_path_by_names(
            project_name=project_name,
            asset_name=asset_doc,
            subset_name=shade_subset,
            version_name="latest",
            representation_name="usd"
        )
        variants.append((variant, path))

    stage = _create_variants_file(
        variants=variants, variantset="model", variant_prim="/root"
    )
    stage.GetRootLayer().Export(filename, args={"format": "usda"})


def create_shade_variation(filename, asset, model_variant, shade_variants):
    """Create the master Shade file for a specific model variant.

    This should reference all shade variants for the specific model variant.

    """

    project_name = get_current_project_name()
    asset_doc = get_asset_by_name(project_name, asset)
    assert asset_doc, "Asset not found: %s" % asset

    variants = []
    for variant in shade_variants:
        subset = "usdShade_{model}_{shade}".format(
            model=model_variant, shade=variant
        )
        path = get_representation_path_by_names(
            project_name=project_name,
            asset_name=asset_doc,
            subset_name=subset,
            version_name="latest",
            representation_name="usd"
        )
        variants.append((variant, path))

    stage = _create_variants_file(
        variants=variants, variantset="shade", variant_prim="/root"
    )
    stage.GetRootLayer().Export(filename, args={"format": "usda"})


def _create_variants_file(
    variants,
    variantset,
    default_variant=None,
    variant_prim="/root",
    reference_prim=None,
    set_default_variant=True,
    as_payload=False,
    skip_variant_on_single_file=True,
):
    """Create a USD file with references to given variants and their paths.

    Examples:
    >>> stage = _create_variants_file("model.usd",
    >>>     variants=[
    >>>         ("main", "main.usd"),
    >>>         ("damaged", "damaged.usd"),
    >>>         ("twisted", "twisted.usd")
    >>>     ],
    >>>     variantset="model")
    >>> stage.rootLayer.Export("model.usd", args={"format": "usda"})

    Arguments:
        variants (List[List[str, str]): List of two-tuples of variant name to
            the filepath that should be referenced in for that variant.
        variantset (str): Name of the variant set
        default_variant (str): Default variant to set. If not provided
            the first variant will be used.
        reference_prim (str): Path to the reference prim where to add the
            references and variant sets.
        set_default_variant (bool): Whether to set the default variant.
            When False no default variant will be set, even if a value
            was provided to `default_variant`
        as_payload (bool): When enabled, instead of referencing use payloads
        skip_variant_on_single_file (bool): If this is enabled and only
            a single variant is provided then do not create the variant set
            but just reference that single file.

    Returns:
        Usd.Stage: The saved usd stage

    """

    root_layer = Sdf.Layer.CreateAnonymous()
    stage = Usd.Stage.Open(root_layer)

    root_prim = stage.DefinePrim(variant_prim)
    stage.SetDefaultPrim(root_prim)

    def _reference(path):
        """Reference/Payload path depending on function arguments"""

        if reference_prim:
            prim = stage.DefinePrim(reference_prim)
        else:
            prim = root_prim

        if as_payload:
            # Payload
            prim.GetPayloads().AddPayload(Sdf.Payload(path))
        else:
            # Reference
            prim.GetReferences().AddReference(Sdf.Reference(path))

    assert variants, "Must have variants, got: %s" % variants

    if skip_variant_on_single_file and len(variants) == 1:
        # Reference directly, no variants
        variant_path = variants[0][1]
        _reference(variant_path)

        log.debug("Creating without variants due to single file only.")
        log.debug("Path: %s", variant_path)

    else:
        # Variants
        append = Usd.ListPositionBackOfAppendList
        variant_set = root_prim.GetVariantSets().AddVariantSet(
            variantset, append
        )
        debug_label = "Payloading" if as_payload else "Referencing"

        for variant, variant_path in variants:

            if default_variant is None:
                default_variant = variant

            variant_set.AddVariant(variant, append)
            variant_set.SetVariantSelection(variant)
            with variant_set.GetVariantEditContext():
                _reference(variant_path)

                log.debug("%s variants.", debug_label)
                log.debug("Variant: %s",  variant)
                log.debug("Path: %s", variant_path)

        if set_default_variant and default_variant is not None:
            variant_set.SetVariantSelection(default_variant)

    return stage


def get_representation_by_names(
        project_name,
        asset_name,
        subset_name,
        version_name,
        representation_name,
):
    """Get representation entity for asset and subset.

    If version_name is "hero" then return the hero version
    If version_name is "latest" then return the latest version
    Otherwise use version_name as the exact integer version name.

    """

    if isinstance(asset_name, dict) and "name" in asset_name:
        # Allow explicitly passing asset document
        asset_doc = asset_name
    else:
        asset_doc = get_asset_by_name(project_name, asset_name, fields=["_id"])
    if not asset_doc:
        return

    if isinstance(subset_name, dict) and "name" in subset_name:
        # Allow explicitly passing subset document
        subset_doc = subset_name
    else:
        subset_doc = get_subset_by_name(project_name,
                                        subset_name,
                                        asset_id=asset_doc["_id"],
                                        fields=["_id"])
    if not subset_doc:
        return

    if version_name == "hero":
        version = get_hero_version_by_subset_id(project_name,
                                                subset_id=subset_doc["_id"])
    elif version_name == "latest":
        version = get_last_version_by_subset_id(project_name,
                                                subset_id=subset_doc["_id"])
    else:
        version = get_version_by_name(project_name,
                                      version_name,
                                      subset_id=subset_doc["_id"])
    if not version:
        return

    return get_representation_by_name(project_name,
                                      representation_name,
                                      version_id=version["_id"])


def get_representation_path_by_names(
        project_name,
        asset_name,
        subset_name,
        version_name,
        representation_name):
    """Get (latest) filepath for representation for asset and subset.

    See `get_representation_by_names` for more details.

    Returns:
        str: The representation path if the representation exists.

    """
    representation = get_representation_by_names(
        project_name,
        asset_name,
        subset_name,
        version_name,
        representation_name
    )
    if representation:
        path = get_representation_path(representation)
        return path.replace("\\", "/")


def parse_ayon_uri(uri):
    """Parse ayon+entity URI into individual components.

    URI specification:
        ayon+entity://{project}/{asset}?product={product}
            &version={version}
            &representation={representation}
    URI example:
        ayon+entity://test/hero?modelMain&version=2&representation=usd

    Example:
    >>> parse_ayon_uri(
    >>>     "ayon+entity://test/villain?product=modelMain&version=2&representation=usd"  # noqa: E501
    >>> )
    {'project': 'test', 'asset': 'villain',
     'product': 'modelMain', 'version': 1,
     'representation': 'usd'}

    Returns:
        dict: The individual keys of the ayon entity query.

    """

    if not uri.startswith("ayon+entity://"):
        return

    parsed = urlparse(uri)
    if parsed.scheme != "ayon+entity":
        return

    result = {
        "project": parsed.netloc,
        "asset": parsed.path.strip("/")
    }
    query = parse_qs(parsed.query)
    for key in ["product", "version", "representation"]:
        if key in query:
            result[key] = query[key][0]

    # Convert version to integer if it is a digit
    version = result.get("version")
    if version is not None and version.isdigit():
        result["version"] = int(version)

    return result


def construct_ayon_uri(
        project_name,
        asset_name,
        product,
        version,
        representation_name
):
    if not (isinstance(version, int) or version in {"latest", "hero"}):
        raise ValueError(
            "Version must either be integer, 'latest' or 'hero'. "
            "Got: {}".format(version)
        )
    return (
        "ayon+entity://{project}/{asset}?product={product}&version={version}"
        "&representation={representation}".format(
            project=project_name,
            asset=asset_name,
            product=product,
            version=version,
            representation=representation_name
        )
    )


def get_representation_path_by_ayon_uri(
        uri,
        context=None
):
    """Return resolved path for Ayon entity URI.

    Allow resolving 'latest' paths from a publishing context's instances
    as if they will exist after publishing without them being integrated yet.

    Args:
        uri (str): Ayon entity URI. See `parse_ayon_uri`
        context (pyblish.api.Context): Publishing context.

    Returns:
        Union[str, None]: Returns the path if it could be resolved

    """
    query = parse_ayon_uri(uri)

    if context is not None and context.data["projectName"] == query["project"]:
        # Search first in publish context to allow resolving latest versions
        # from e.g. the current publish session if the context is provided
        if query["version"] == "hero":
            raise NotImplementedError(
                "Hero version resolving not implemented from context"
            )

        specific_version = isinstance(query["version"], int)
        for instance in context:
            if instance.data.get("asset") != query["asset"]:
                continue

            if instance.data.get("subset") != query["product"]:
                continue

            # Only consider if the instance has a representation by
            # that name
            representations = instance.data.get("representations", [])
            if not any(representation.get("name") == query["representation"]
                       for representation in representations):
                continue

            return get_instance_expected_output_path(
                instance,
                representation_name=query["representation"],
                version=query["version"] if specific_version else None
            )

    return get_representation_path_by_names(
        project_name=query["project"],
        asset_name=query["asset"],
        subset_name=query["product"],
        version_name=query["version"],
        representation_name=query["representation"],
    )


def get_instance_expected_output_path(instance, representation_name,
                                      ext=None, version=None):
    """Return expected publish filepath for representation in instance

    This does not validate whether the instance has any representation by the
    given name, extension and/or version.

    Arguments:
        instance (pyblish.api.Instance): publish instance
        representation_name (str): representation name
        ext (Optional[str]): extension for the file, useful if `name` += `ext`
        version (Optional[int]): if provided, force it to format to this
            particular version.
        representation_name (str): representation name

    Returns:
        str: Resolved path

    """

    if ext is None:
        ext = representation_name
    if version is None:
        version = instance.data["version"]

    context = instance.context
    anatomy = context.data["anatomy"]
    path_template_obj = anatomy.templates_obj["publish"]["path"]
    template_data = copy.deepcopy(instance.data["anatomyData"])
    template_data.update({
        "ext": ext,
        "representation": representation_name,
        "subset": instance.data["subset"],
        "asset": instance.data["asset"],
        "variant": instance.data.get("variant"),
        "version": version
    })

    template_filled = path_template_obj.format_strict(template_data)
    return os.path.normpath(template_filled)


def set_layer_defaults(layer,
                       up_axis=UsdGeom.Tokens.y,
                       meters_per_unit=1.0,
                       default_prim=None):
    """Set some default metadata for the SdfLayer.

    Arguments:
        layer (Sdf.Layer): The layer to set default for via Sdf API.
        up_axis (UsdGeom.Token); Which axis is the up-axis
        meters_per_unit (float): Meters per unit
        default_prim (Optional[str]: Default prim name

    """
    # Set default prim
    if default_prim is not None:
        layer.defaultPrim = default_prim

    # Let viewing applications know how to orient a free camera properly
    # Similar to: UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    layer.pseudoRoot.SetInfo(UsdGeom.Tokens.upAxis, up_axis)

    # Set meters per unit
    layer.pseudoRoot.SetInfo(UsdGeom.Tokens.metersPerUnit,
                             float(meters_per_unit))
