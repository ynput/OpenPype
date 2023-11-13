from openpype.lib import usdlib
from pxr import Sdf


def test_create_asset(tmp_path):
    """Test creating the basics of an asset structure."""
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
    """Test creating shot structure; which is just a bunch of layers"""
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
    """Test adding variants to a layer, replacing older ones"""
    # TODO: The code doesn't error but the data should still be validated

    prim_path = "/root"
    layer = usdlib.add_variant_references_to_layer(variants=[
            ("main", "./main.usd"),
            ("twist", "./twist.usd"),
            ("damaged", "./damaged.usd"),
            ("tall", "./tall.usd"),
        ],
        variantset="model",
        variant_prim=prim_path
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
        layer=layer,
        variant_prim=prim_path
    )

    # Allow with a layer provided to operate on that layer
    # instead; adding more variant names to an existing variant set
    layer = usdlib.add_variant_references_to_layer(variants=[
            ("short", "./look_short.usd"),
        ],
        variantset="look",
        layer=layer,
        set_default_variant=False,
        variant_prim=prim_path
    )

    # Applying variants to another prim should not affect first prim
    layer = usdlib.add_variant_references_to_layer(variants=[
            ("short", "./look_short.usd"),
        ],
        variantset="look",
        layer=layer,
        set_default_variant=False,
        variant_prim="/other_root"
    )

    # Export layer should work
    layer.Export(
        str(tmp_path / "model.usd"),
        args={"format": "usda"},
    )
    assert (tmp_path / "model.usd").exists()

    # Debug print generated file (pytest excludes it by default but will
    # show it if the -s flag is passed)
    print(layer.ExportToString())


def test_add_ordered_sublayer(tmp_path):
    """Test addinng sublayers by order and uniqueness"""
    # TODO: The code doesn't error but the data should still be validated

    layer = Sdf.Layer.CreateAnonymous()

    def get_paths(layer, remove_format_args=True):
        paths = layer.subLayerPaths
        # Remove stored metadata in string
        if remove_format_args:
            paths = [path.split(":SDF_FORMAT_ARGS:", 1)[0] for path in paths]
        return paths

    # The layer stack should have the higher orders earlier in the list
    # because those state "stronger opinions" - as such the order needs to be
    # reversed
    orders = [300, 500, 350, 600, 50, 150, 450]
    for order in orders:
        usdlib.add_ordered_sublayer(layer,
                                    contribution_path=str(order),
                                    layer_id=str(order),
                                    order=order)

    paths = get_paths(layer)
    assert paths == ["600", "500", "450", "350", "300", "150", "50"]

    # This should not add a sublayer but should replace by `layer_id`
    usdlib.add_ordered_sublayer(layer,
                                contribution_path="300_v2",
                                layer_id="300",
                                order=300)

    paths = get_paths(layer)
    assert paths == ["600", "500", "450", "350", "300_v2", "150", "50"]

    # When replacing a layer with a new 'id' the ordering is preserved from
    # before; the new order is not applied.
    usdlib.add_ordered_sublayer(layer,
                                contribution_path=f"500_v2",
                                layer_id="500",
                                order=9999)

    paths = get_paths(layer)
    assert paths == ["600", "500_v2", "450", "350", "300_v2", "150", "50"]

    # When replacing a layer with a new 'id' the ordering is preserved from
    # before; the new order is not applied even when it is None
    usdlib.add_ordered_sublayer(layer,
                                contribution_path=f"500_v3",
                                layer_id="500",
                                order=None)

    paths = get_paths(layer)
    assert paths == ["600", "500_v3", "450", "350", "300_v2", "150", "50"]

    # Adding new layer id should also work to insert the new layer
    usdlib.add_ordered_sublayer(layer,
                                contribution_path=f"75",
                                layer_id="75",
                                order=75)

    paths = get_paths(layer)
    assert paths == ["600", "500_v3", "450", "350", "300_v2", "150", "75", "50"]  # noqa: E501

    # Adding a layer with `order=None` should append at the start as a
    # strongest opinion
    usdlib.add_ordered_sublayer(layer,
                                contribution_path=f"None",
                                layer_id="None",
                                order=None)
    paths = get_paths(layer)
    assert paths == ["None", "600", "500_v3", "450", "350", "300_v2", "150", "75", "50"]  # noqa: E501

    # Adding a layer with `order=None` should also be replaceable
    usdlib.add_ordered_sublayer(layer,
                                contribution_path=f"None_v2",
                                layer_id="None",
                                order=None)
    paths = get_paths(layer)
    assert paths == ["None_v2", "600", "500_v3", "450", "350", "300_v2", "150", "75", "50"]  # noqa: E501

    # Debug print generated file (pytest excludes it by default but will
    # show it if the -s flag is passed)
    print(layer.ExportToString())
