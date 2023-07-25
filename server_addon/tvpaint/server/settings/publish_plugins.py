from pydantic import Field, validator

from ayon_server.settings import BaseSettingsModel, ensure_unique_names
from ayon_server.types import ColorRGBA_uint8


class CollectRenderInstancesModel(BaseSettingsModel):
    ignore_render_pass_transparency: bool = Field(title="Ignore Render Pass opacity")


class ExtractSequenceModel(BaseSettingsModel):
    """Review BG color is used for whole scene review and for thumbnails."""
    # TODO Use alpha color
    review_bg: ColorRGBA_uint8 = Field(
        (255, 255, 255, 1.0),
        title="Review BG color")


class ValidatePluginModel(BaseSettingsModel):
    enabled: bool = True
    optional: bool = Field(True, title="Optional")
    active: bool = Field(True, title="Active")


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

    exr_compression: str = Field(
        "ZIP",
        enum_resolver=compression_enum,
        title="EXR Compression"
    )


class LoadImageDefaultModel(BaseSettingsModel):
    _layout = "expanded"
    stretch: bool = Field(title="Stretch")
    timestretch: bool = Field(title="TimeStretch")
    preload: bool = Field(title="Preload")


class LoadImageModel(BaseSettingsModel):
    defaults: LoadImageDefaultModel = Field(
        default_factory=LoadImageDefaultModel
    )


class PublishPluginsModel(BaseSettingsModel):
    CollectRenderInstances: CollectRenderInstancesModel = Field(
        default_factory=CollectRenderInstancesModel,
        title="Collect Render Instances")
    ExtractSequence: ExtractSequenceModel = Field(
        default_factory=ExtractSequenceModel,
        title="Extract Sequence")
    ValidateProjectSettings: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Project Settings")
    ValidateMarks: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate MarkIn/Out")
    ValidateStartFrame: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Scene Start Frame")
    ValidateAssetName: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Folder Name")
    ExtractConvertToEXR: ExtractConvertToEXRModel = Field(
        default_factory=ExtractConvertToEXRModel,
        title="Extract Convert To EXR")


class LoadPluginsModel(BaseSettingsModel):
    LoadImage: LoadImageModel = Field(
        default_factory=LoadImageModel,
        title="Load Image")
    ImportImage: LoadImageModel = Field(
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
