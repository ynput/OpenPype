from openpype.lib import usdlib
from pxr import Sdf


def test_create_asset(tmp_path):
    layers = usdlib.create_asset(str(tmp_path / "asset.usd"),
                                 asset_name="test",
                                 reference_layers=["./model.usd",
                                                   "./look.usd"])
    assert len(
        layers) == 2, "Expecting two files, the asset.usd and payload.usd"
    assert (tmp_path / "asset.usd").exists()
    assert (tmp_path / "payload.usd").exists()
    assert not (tmp_path / "model.usd").exists()
    assert not (tmp_path / "look.usd").exists()


def test_add_contributions_to_asset(tmp_path):
    """Test adding contributions on top of each other works as expected"""
    asset_usd = str(tmp_path / "asset.usd")
    usdlib.create_asset(asset_usd,
                        asset_name="test",
                        reference_layers=["./model.usd",
                                          "./look.usd"])

    layer = Sdf.Layer.OpenAsAnonymous(asset_usd)
    prim_path = Sdf.Path("/test")  # prim is named by `asset_name`

    path_in_variant = prim_path.AppendVariantSelection("model", "modelMain")
    assert not layer.GetPrimAtPath(path_in_variant), (
        "Variant should not exist yet and thus the prim should not exist"
    )

    # Adding a variant with a single prepended reference should work
    usdlib.set_variant_reference(
        layer,
        prim_path=prim_path,
        variant_selections=[["model", "modelMain"]],
        path="./modelMain.usd"
    )

    prim_in_variant = layer.GetPrimAtPath(path_in_variant)
    assert prim_in_variant, "Path in variant should be defined"
    references = prim_in_variant.referenceList.prependedItems[:]
    assert len(references) == 1, \
        "Must have only one reference"
    assert references[0].assetPath == "./modelMain.usd", \
        "Must reference ./modelMain.usd"

    # Replacing an existing variant reference should work
    usdlib.set_variant_reference(
        layer,
        prim_path=prim_path,
        variant_selections=[["model", "modelMain"]],
        path="./modelMain_v2.usd"
    )
    prim_in_variant = layer.GetPrimAtPath(path_in_variant)
    references = prim_in_variant.referenceList.prependedItems[:]
    assert len(references) == 1, \
        "Must have only one reference"
    assert references[0].assetPath == "./modelMain_v2.usd", \
        "Must reference ./modelMain_v2.usd"

    # Adding multiple variants should work and should not adjust original
    usdlib.set_variant_reference(
        layer,
        prim_path=prim_path,
        variant_selections=[["model", "modelDamaged"]],
        path="./modelDamaged.usd"
    )
    usdlib.set_variant_reference(
        layer,
        prim_path=prim_path,
        variant_selections=[["look", "lookMain"]],
        path="./lookMain.usd",
    )

    # Validate all exist and paths are set as expected path
    for variant_set_name, variant_name, expected_path in [
        ("model", "modelMain", "./modelMain_v2.usd"),
        ("model", "modelDamaged", "./modelDamaged.usd"),
        ("look", "lookMain", "./lookMain.usd"),
    ]:
        path_in_variant = prim_path.AppendVariantSelection(variant_set_name,
                                                           variant_name)
        prim_in_variant = layer.GetPrimAtPath(path_in_variant)
        references = prim_in_variant.referenceList.prependedItems[:]
        assert len(references) == 1, \
            "Must have only one reference"
        assert references[0].assetPath == expected_path, \
            f"Must reference {expected_path}"

    print(layer.ExportToString())


def test_create_shot(tmp_path):
    usdlib.create_shot(str(tmp_path / "shot.usd"),
                       layers=["./lighting.usd",
                               "./fx.usd",
                               "./animation.usd"
                               "./layout.usd"])
    assert (tmp_path / "shot.usd").exists()
    assert not (tmp_path / "lighting.usd").exists()
    assert not (tmp_path / "fx.usd").exists()
    assert not (tmp_path / "animation.usd").exists()
    assert not (tmp_path / "layout.usd").exists()


def test_add_variant_references_to_layer(tmp_path):
    layer = usdlib.add_variant_references_to_layer(variants=[
            ("main", "./main.usd"),
            ("twist", "./twist.usd"),
            ("damaged", "./damaged.usd"),
            ("tall", "./tall.usd"),
        ],
        variantset="model"
    )

    # Allow recalling with a layer provided to operate on that layer
    # instead; adding more variant definitions
    layer = usdlib.add_variant_references_to_layer(variants=[
            ("main", "./look_main.usd"),
            ("twist", "./look_twist.usd"),
            ("damaged", "./look_damaged.usd"),
            ("tall", "./look_tall.usd"),
        ],
        variantset="look",
        layer=layer
    )

    # Allow with a layer provided to operate on that layer
    # instead; adding more variant names to an existing variant set
    layer = usdlib.add_variant_references_to_layer(variants=[
            ("short", "./look_short.usd"),
        ],
        variantset="look",
        layer=layer,
        skip_variant_on_single_file=True
    )

    # Save
    layer.Export(
        str(tmp_path / "model.usd"),
        args={"format": "usda"}
    )

    # Debug print generated file (pytest excludes it by default but will
    # show it if the -s flag is passed)
    print(layer.ExportToString())
    assert (tmp_path / "model.usd").exists()
