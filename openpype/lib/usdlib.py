import dataclasses
import os
import copy
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


def add_variant_references_to_layer(
    variants,
    variantset,
    default_variant=None,
    variant_prim="/root",
    reference_prim=None,
    set_default_variant=True,
    as_payload=False,
    skip_variant_on_single_file=False,
    layer=None
):
    """Add or set a prim's variants to reference specified paths in the layer.

    Note:
        This does not clear any of the other opinions than replacing
        `prim.referenceList.prependedItems` with the new reference.
        If `as_payload=True` then this only does it for payloads and leaves
        references as they were in-tact.

    Note:
        If `skip_variant_on_single_file=True` it does *not* check if any
        other variants do exist; it only checks whether you are currently
        adding more than one since it'd be hard to find out whether previously
        this was also skipped and should now if you're adding a new one
        suddenly also be its original 'variant'. As such it's recommended to
        keep this disabled unless you know you're not updating the file later
        into the same variant set.

    Examples:
    >>> layer = add_variant_references_to_layer("model.usd",
    >>>     variants=[
    >>>         ("main", "main.usd"),
    >>>         ("damaged", "damaged.usd"),
    >>>         ("twisted", "twisted.usd")
    >>>     ],
    >>>     variantset="model")
    >>> layer.Export("model.usd", args={"format": "usda"})

    Arguments:
        variants (List[List[str, str]): List of two-tuples of variant name to
            the filepath that should be referenced in for that variant.
        variantset (str): Name of the variant set
        default_variant (str): Default variant to set. If not provided
            the first variant will be used.
        variant_prim (str): Variant prim?
        reference_prim (str): Path to the reference prim where to add the
            references and variant sets.
        set_default_variant (bool): Whether to set the default variant.
            When False no default variant will be set, even if a value
            was provided to `default_variant`
        as_payload (bool): When enabled, instead of referencing use payloads
        skip_variant_on_single_file (bool): If this is enabled and only
            a single variant is provided then do not create the variant set
            but just reference that single file.
        layer (Sdf.Layer): When provided operate on this layer, otherwise
            create an anonymous layer in memory.

    Returns:
        Usd.Stage: The saved usd stage

    """
    if layer is None:
        layer = Sdf.Layer.CreateAnonymous()
        set_layer_defaults(layer, default_prim=variant_prim.strip("/"))

    prim_path_to_get_variants = Sdf.Path(variant_prim)
    root_prim = get_or_define_prim_spec(layer, variant_prim, "Xform")

    # TODO: Define why there's a need for separate variant_prim and
    #   reference_prim attribute. When should they differ? Does it even work?
    if not reference_prim:
        reference_prim = root_prim
    else:
        reference_prim = get_or_define_prim_spec(layer, reference_prim,
                                                 "Xform")

    assert variants, "Must have variants, got: %s" % variants

    if skip_variant_on_single_file and len(variants) == 1:
        # Reference directly, no variants
        variant_path = variants[0][1]
        if as_payload:
            # Payload
            reference_prim.payloadList.prependedItems.append(
                Sdf.Payload(variant_path)
            )
        else:
            # Reference
            reference_prim.referenceList.prependedItems.append(
                Sdf.Reference(variant_path)
            )

        log.debug("Creating without variants due to single file only.")
        log.debug("Path: %s", variant_path)

    else:
        # Variants
        for variant, variant_filepath in variants:
            if default_variant is None:
                default_variant = variant

            set_variant_reference(layer,
                                  prim_path=prim_path_to_get_variants,
                                  variant_selections=[[variantset, variant]],
                                  path=variant_filepath,
                                  as_payload=as_payload)

        if set_default_variant and default_variant is not None:
            # Set default variant selection
            root_prim.variantSelections[variantset] = default_variant

    return layer


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


def get_or_define_prim_spec(layer, prim_path, type_name):
    """Get or create a PrimSpec in the layer.

    Note:
        This creates a Sdf.PrimSpec with Sdf.SpecifierDef but if the PrimSpec
        already exists this will not force it to be a Sdf.SpecifierDef and
        it may remain what it was, e.g. Sdf.SpecifierOver

    Args:
        layer (Sdf.Layer): The layer to create it in.
        prim_path (Any[str, Sdf.Path]): Prim path to create.
        type_name (str): Type name for the PrimSpec.
            This will only be set if the prim does not exist in the layer
            yet. It does not update type for an existing prim.

    Returns:
        Sdf.PrimSpec: The PrimSpec in the layer for the given prim path.

    """
    prim_spec = layer.GetPrimAtPath(prim_path)
    if prim_spec:
        return prim_spec

    prim_spec = Sdf.CreatePrimInLayer(layer, prim_path)
    prim_spec.specifier = Sdf.SpecifierDef
    prim_spec.typeName = type_name
    return prim_spec


def variant_nested_prim_path(prim_path, variant_selections):
    """Return the Sdf.Path path for a nested variant selection at prim path.

    Examples:
    >>> prim_path = Sdf.Path("/asset")
    >>> variant_spec = variant_nested_prim_path(
    >>>     prim_path,
    >>>     variant_selections=[["model", "main"], ["look", "main"]]
    >>> )
    >>> variant_spec.path

    Args:
        prim_path (Sdf.PrimPath): The prim path to create the spec in
        variant_selections (List[List[str, str]]): A list of variant set names
            and variant names to get the prim spec in.

    Returns:
        Sdf.Path: The variant prim path

    """
    variant_prim_path = Sdf.Path(prim_path)
    for variant_set_name, variant_name in variant_selections:
        variant_prim_path = variant_prim_path.AppendVariantSelection(
            variant_set_name, variant_name)
    return variant_prim_path


def set_variant_reference(sdf_layer, prim_path, variant_selections, path,
                          as_payload=False,
                          append=True):
    """Get or define variant selection at prim path and add a reference

    If the Variant Prim already exists the prepended references are replaced
    with a reference to `path`, it is overridden.

    Args:
        sdf_layer (Sdf.Layer): Layer to operate in.
        prim_path (Any[str, Sdf.Path]): Prim path to add variant to.
        variant_selections (List[List[str, str]]): A list of variant set names
            and variant names to get the prim spec in.
        path (str): Path to reference or payload
        as_payload (bool): When enabled it will generate a payload instead of
            a reference. Defaults to False.
        append (bool): When enabled it will append the reference of payload
            to prepended items, otherwise it will replace it.

    Returns:
        S

    """
    prim_path = Sdf.Path(prim_path)
    # TODO: inherit type from outside of variants if it has it
    get_or_define_prim_spec(sdf_layer, prim_path, "Xform")
    variant_prim_path = variant_nested_prim_path(prim_path, variant_selections)
    variant_prim = get_or_define_prim_spec(sdf_layer,
                                           variant_prim_path,
                                           "Xform")
    # Replace the prepended references or payloads
    if as_payload:
        # Payload
        if append:
            variant_prim.payloadList.prependedItems.append(
                Sdf.Payload(assetPath=path)
            )
        else:
            variant_prim.payloadList.prependedItems.append(
                Sdf.Payload(assetPath=path)
            )
    else:
        # Reference
        if append:
            variant_prim.referenceList.prependedItems[:] = [
                Sdf.Reference(assetPath=path)
            ]
        else:
            variant_prim.payloadList.prependedItems[:] = [
                Sdf.Payload(assetPath=path)
            ]

    return variant_prim


def get_sdf_format_args(path):
    """Return SDF_FORMAT_ARGS parsed to `dict`"""
    if ":SDF_FORMAT_ARGS:" not in path:
        return {}

    format_args_str = path.split(":SDF_FORMAT_ARGS:", 1)[-1]
    args = {}
    for arg_str in format_args_str.split(":"):
        if "=" not in arg_str:
            # ill-formed argument key=value
            continue

        key, value = arg_str.split("=", 1)
        args[key] = value
    return args

# TODO: Functions below are not necessarily USD functions and hence should not
#  be in this file. Refactor by moving them elsewhere
# region representations and Ayon uris


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
    """Parse ayon entity URI into individual components.

    URI specification:
        ayon+entity://{project}/{asset}?product={product}
            &version={version}
            &representation={representation}
    URI example:
        ayon+entity://test/hero?modelMain&version=2&representation=usd

    However - if the netloc is `ayon://` it will by default also resolve as
    `ayon+entity://` on AYON server, thus we need to support both. The shorter
    `ayon://` is preferred for user readability.

    Example:
    >>> parse_ayon_uri(
    >>>     "ayon://test/villain?product=modelMain&version=2&representation=usd"  # noqa: E501
    >>> )
    {'project': 'test', 'asset': 'villain',
     'product': 'modelMain', 'version': 1,
     'representation': 'usd'}
    >>> parse_ayon_uri(
    >>>     "ayon+entity://project/asset?product=renderMain&version=3&representation=exr"  # noqa: E501
    >>> )
    {'project': 'project', 'asset': 'asset',
     'product': 'renderMain', 'version': 3,
     'representation': 'exr'}

    Returns:
        dict: The individual keys of the ayon entity query.

    """

    if not (uri.startswith("ayon+entity://") or uri.startswith("ayon://")):
        return

    parsed = urlparse(uri)
    if parsed.scheme not in {"ayon+entity", "ayon"}:
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
    """Construct Ayon entity URI from its components

    Returns:
        str: Ayon Entity URI to query entity path.
            Also works with `get_representation_path_by_ayon_uri`
    """
    if not (isinstance(version, int) or version in {"latest", "hero"}):
        raise ValueError(
            "Version must either be integer, 'latest' or 'hero'. "
            "Got: {}".format(version)
        )
    return (
        "ayon://{project}/{asset}?product={product}&version={version}"
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

# endregion
