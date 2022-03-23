import os
import re
import logging

try:
    from pxr import Usd, UsdGeom, Sdf, Kind
except ImportError:
    # Allow to fall back on Multiverse 6.3.0+ pxr usd library
    from mvpxr import Usd, UsdGeom, Sdf, Kind

from avalon import io, api

log = logging.getLogger(__name__)


# The predefined steps order used for bootstrapping USD Shots and Assets.
# These are ordered in order from strongest to weakest opinions, like in USD.
PIPELINE = {
    "shot": [
        "usdLighting",
        "usdFx",
        "usdSimulation",
        "usdAnimation",
        "usdLayout",
    ],
    "asset": ["usdShade", "usdModel"],
}


def create_asset(
    filepath, asset_name, reference_layers, kind=Kind.Tokens.component
):
    """
    Creates an asset file that consists of a top level layer and sublayers for
    shading and geometry.

    Args:
        filepath (str): Filepath where the asset.usd file will be saved.
        reference_layers (list): USD Files to reference in the asset.
            Note that the bottom layer (first file, like a model) would
            be last in the list. The strongest layer will be the first
            index.
        asset_name (str): The name for the Asset identifier and default prim.
        kind (pxr.Kind): A USD Kind for the root asset.

    """
    # Also see create_asset.py in PixarAnimationStudios/USD endToEnd example

    log.info("Creating asset at %s", filepath)

    # Make the layer ascii - good for readability, plus the file is small
    root_layer = Sdf.Layer.CreateNew(filepath, args={"format": "usda"})
    stage = Usd.Stage.Open(root_layer)

    # Define a prim for the asset and make it the default for the stage.
    asset_prim = UsdGeom.Xform.Define(stage, "/%s" % asset_name).GetPrim()
    stage.SetDefaultPrim(asset_prim)

    # Let viewing applications know how to orient a free camera properly
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    # Usually we will "loft up" the kind authored into the exported geometry
    # layer rather than re-stamping here; we'll leave that for a later
    # tutorial, and just be explicit here.
    model = Usd.ModelAPI(asset_prim)
    if kind:
        model.SetKind(kind)

    model.SetAssetName(asset_name)
    model.SetAssetIdentifier("%s/%s.usd" % (asset_name, asset_name))

    # Add references to the  asset prim
    references = asset_prim.GetReferences()
    for reference_filepath in reference_layers:
        references.AddReference(reference_filepath)

    stage.GetRootLayer().Save()


def create_shot(filepath, layers, create_layers=False):
    """Create a shot with separate layers for departments.

    Args:
        filepath (str): Filepath where the asset.usd file will be saved.
        layers (str): When provided this will be added verbatim in the
            subLayerPaths layers. When the provided layer paths do not exist
            they are generated using  Sdf.Layer.CreateNew
        create_layers (bool): Whether to create the stub layers on disk if
            they do not exist yet.

    Returns:
        str: The saved shot file path

    """
    # Also see create_shot.py in PixarAnimationStudios/USD endToEnd example

    stage = Usd.Stage.CreateNew(filepath)
    log.info("Creating shot at %s" % filepath)

    for layer_path in layers:
        if create_layers and not os.path.exists(layer_path):
            # We use the Sdf API here to quickly create layers.  Also, we're
            # using it as a way to author the subLayerPaths as there is no
            # way to do that directly in the Usd API.
            layer_folder = os.path.dirname(layer_path)
            if not os.path.exists(layer_folder):
                os.makedirs(layer_folder)

            Sdf.Layer.CreateNew(layer_path)

        stage.GetRootLayer().subLayerPaths.append(layer_path)

    # Lets viewing applications know how to orient a free camera properly
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.GetRootLayer().Save()

    return filepath


def create_model(filename, asset, variant_subsets):
    """Create a USD Model file.

    For each of the variation paths it will payload the path and set its
    relevant variation name.

    """

    asset_doc = io.find_one({"name": asset, "type": "asset"})
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

        path = get_usd_master_path(
            asset=asset_doc, subset=subset, representation="usd"
        )
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

    asset_doc = io.find_one({"name": asset, "type": "asset"})
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
        path = get_usd_master_path(
            asset=asset_doc, subset=shade_subset, representation="usd"
        )
        variants.append((variant, path))

    stage = _create_variants_file(
        filename, variants=variants, variantset="model", variant_prim="/root"
    )

    stage.GetRootLayer().Save()


def create_shade_variation(filename, asset, model_variant, shade_variants):
    """Create the master Shade file for a specific model variant.

    This should reference all shade variants for the specific model variant.

    """

    asset_doc = io.find_one({"name": asset, "type": "asset"})
    assert asset_doc, "Asset not found: %s" % asset

    variants = []
    for variant in shade_variants:
        subset = "usdShade_{model}_{shade}".format(
            model=model_variant, shade=variant
        )
        path = get_usd_master_path(
            asset=asset_doc, subset=subset, representation="usd"
        )
        variants.append((variant, path))

    stage = _create_variants_file(
        filename, variants=variants, variantset="shade", variant_prim="/root"
    )

    stage.GetRootLayer().Save()


def _create_variants_file(
    filename,
    variants,
    variantset,
    default_variant=None,
    variant_prim="/root",
    reference_prim=None,
    set_default_variant=True,
    as_payload=False,
    skip_variant_on_single_file=True,
):

    root_layer = Sdf.Layer.CreateNew(filename, args={"format": "usda"})
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

    log.info(filename)

    if skip_variant_on_single_file and len(variants) == 1:
        # Reference directly, no variants
        variant_path = variants[0][1]
        _reference(variant_path)

        log.info("Non-variants..")
        log.info("Path: %s" % variant_path)

    else:
        # Variants
        append = Usd.ListPositionBackOfAppendList
        variant_set = root_prim.GetVariantSets().AddVariantSet(
            variantset, append
        )

        for variant, variant_path in variants:

            if default_variant is None:
                default_variant = variant

            variant_set.AddVariant(variant, append)
            variant_set.SetVariantSelection(variant)
            with variant_set.GetVariantEditContext():
                _reference(variant_path)

                log.info("Variants..")
                log.info("Variant: %s" % variant)
                log.info("Path: %s" % variant_path)

        if set_default_variant:
            variant_set.SetVariantSelection(default_variant)

    return stage


def get_usd_master_path(asset, subset, representation):
    """Get the filepath for a .usd file of a subset.

    This will return the path to an unversioned master file generated by
    `usd_master_file.py`.

    """

    project = io.find_one(
        {"type": "project"}, projection={"config.template.publish": True}
    )
    template = project["config"]["template"]["publish"]

    if isinstance(asset, dict) and "name" in asset:
        # Allow explicitly passing asset document
        asset_doc = asset
    else:
        asset_doc = io.find_one({"name": asset, "type": "asset"})

    path = template.format(
        **{
            "root": api.registered_root(),
            "project": api.Session["AVALON_PROJECT"],
            "asset": asset_doc["name"],
            "subset": subset,
            "representation": representation,
            "version": 0,  # stub version zero
        }
    )

    # Remove the version folder
    subset_folder = os.path.dirname(os.path.dirname(path))
    master_folder = os.path.join(subset_folder, "master")
    fname = "{0}.{1}".format(subset, representation)

    return os.path.join(master_folder, fname).replace("\\", "/")


def parse_avalon_uri(uri):
    # URI Pattern: avalon://{asset}/{subset}.{ext}
    pattern = r"avalon://(?P<asset>[^/.]*)/(?P<subset>[^/]*)\.(?P<ext>.*)"
    if uri.startswith("avalon://"):
        match = re.match(pattern, uri)
        if match:
            return match.groupdict()
