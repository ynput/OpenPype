from ayon_server.settings import BaseSettingsModel, SettingsField
from ayon_server.types import ColorRGBA_uint8


class CollectRenderInstancesModel(BaseSettingsModel):
    ignore_render_pass_transparency: bool = SettingsField(
        title="Ignore Render Pass opacity"
    )


class ExtractSequenceModel(BaseSettingsModel):
    """Review BG color is used for whole scene review and for thumbnails."""
    # TODO Use alpha color
    review_bg: ColorRGBA_uint8 = SettingsField(
        (255, 255, 255, 1.0),
        title="Review BG color")


class ValidatePluginModel(BaseSettingsModel):
    enabled: bool = True
    optional: bool = SettingsField(True, title="Optional")
    active: bool = SettingsField(True, title="Active")


def compression_enum():
    return [
        {"value": "ZIP", "label": "ZIP"},
        {"value": "ZIPS", "label": "ZIPS"},
        {"value": "DWAA", "label": "DWAA"},
        {"value": "DWAB", "label": "DWAB"},
        {"value": "PIZ", "label": "PIZ"},
        {"value": "RLE", "label": "RLE"},
        {"value": "PXR24", "label": "PXR24"},
        {"value": "B44", "label": "B44"},
        {"value": "B44A", "label": "B44A"},
        {"value": "none", "label": "None"}
    ]


class ExtractConvertToEXRModel(BaseSettingsModel):
    """WARNING: This plugin does not work on MacOS (using OIIO tool)."""
    enabled: bool = False
    replace_pngs: bool = True

    exr_compression: str = SettingsField(
        "ZIP",
        enum_resolver=compression_enum,
        title="EXR Compression"
    )


class LoadImageDefaultModel(BaseSettingsModel):
    _layout = "expanded"
    stretch: bool = SettingsField(title="Stretch")
    timestretch: bool = SettingsField(title="TimeStretch")
    preload: bool = SettingsField(title="Preload")


class LoadImageModel(BaseSettingsModel):
    defaults: LoadImageDefaultModel = SettingsField(
        default_factory=LoadImageDefaultModel
    )


class PublishPluginsModel(BaseSettingsModel):
    CollectRenderInstances: CollectRenderInstancesModel = SettingsField(
        default_factory=CollectRenderInstancesModel,
        title="Collect Render Instances")
    ExtractSequence: ExtractSequenceModel = SettingsField(
        default_factory=ExtractSequenceModel,
        title="Extract Sequence")
    ValidateProjectSettings: ValidatePluginModel = SettingsField(
        default_factory=ValidatePluginModel,
        title="Validate Project Settings")
    ValidateMarks: ValidatePluginModel = SettingsField(
        default_factory=ValidatePluginModel,
        title="Validate MarkIn/Out")
    ValidateStartFrame: ValidatePluginModel = SettingsField(
        default_factory=ValidatePluginModel,
        title="Validate Scene Start Frame")
    ValidateAssetName: ValidatePluginModel = SettingsField(
        default_factory=ValidatePluginModel,
        title="Validate Folder Name")
    ExtractConvertToEXR: ExtractConvertToEXRModel = SettingsField(
        default_factory=ExtractConvertToEXRModel,
        title="Extract Convert To EXR")


class LoadPluginsModel(BaseSettingsModel):
    LoadImage: LoadImageModel = SettingsField(
        default_factory=LoadImageModel,
        title="Load Image")
    ImportImage: LoadImageModel = SettingsField(
        default_factory=LoadImageModel,
        title="Import Image")


DEFAULT_PUBLISH_SETTINGS = {
    "CollectRenderInstances": {
        "ignore_render_pass_transparency": False
    },
    "ExtractSequence": {
        "review_bg": [255, 255, 255, 1.0]
    },
    "ValidateProjectSettings": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateMarks": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateStartFrame": {
        "enabled": False,
        "optional": True,
        "active": True
    },
    "ValidateAssetName": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ExtractConvertToEXR": {
        "enabled": False,
        "replace_pngs": True,
        "exr_compression": "ZIP"
    }
}
