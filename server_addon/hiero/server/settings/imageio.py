from pydantic import Field, validator

from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathListModel,
    ensure_unique_names,
)


ocio_configs_switcher_enum = [
    {"value": "nuke-default", "label": "nuke-default"},
    {"value": "spi-vfx", "label": "spi-vfx"},
    {"value": "spi-anim", "label": "spi-anim"},
    {"value": "aces_0.1.1", "label": "aces_0.1.1"},
    {"value": "aces_0.7.1" , "label": "aces_0.7.1"},
    {"value": "aces_1.0.1", "label": "aces_1.0.1"},
    {"value": "aces_1.0.3", "label": "aces_1.0.3"},
    {"value": "aces_1.1", "label": "aces_1.1"},
    {"value": "aces_1.2", "label": "aces_1.2"},
    {"value": "aces_1.3", "label": "aces_1.3"},
    {"value": "custom", "label": "custom"}
]


class WorkfileColorspaceSettings(BaseSettingsModel):
    """Hiero workfile colorspace preset. """
    """# TODO: enhance settings with host api:
    we need to add mapping to resolve properly keys.
    Hiero is excpecting camel case key names,
    but for better code consistency we are using snake_case:

    ocio_config = ocioConfigName
    working_space_name = workingSpace
    int_16_name = sixteenBitLut
    int_8_name = eightBitLut
    float_name = floatLut
    log_name = logLut
    viewer_name = viewerLut
    thumbnail_name = thumbnailLut
    """

    ocioConfigName: str = Field(
        title="OpenColorIO Config",
        description="Switch between OCIO configs",
        enum_resolver=lambda: ocio_configs_switcher_enum,
        conditionalEnum=True
    )
    workingSpace: str = Field(
        title="Working Space"
    )
    viewerLut: str = Field(
        title="Viewer"
    )
    eightBitLut: str = Field(
        title="8-bit files"
    )
    sixteenBitLut: str = Field(
        title="16-bit files"
    )
    logLut: str = Field(
        title="Log files"
    )
    floatLut: str = Field(
        title="Float files"
    )
    thumbnailLut: str = Field(
        title="Thumnails"
    )
    monitorOutLut: str = Field(
        title="Monitor"
    )


class ClipColorspaceRulesItems(BaseSettingsModel):
    _layout = "expanded"

    regex: str = Field("", title="Regex expression")
    colorspace: str = Field("", title="Colorspace")


class RegexInputsModel(BaseSettingsModel):
    inputs: list[ClipColorspaceRulesItems] = Field(
        default_factory=list,
        title="Inputs"
    )


class ImageIOConfigModel(BaseSettingsModel):
    override_global_config: bool = Field(
        False,
        title="Override global OCIO config"
    )
    filepath: list[str] = Field(
        default_factory=list,
        title="Config path"
    )


class ImageIOFileRuleModel(BaseSettingsModel):
    name: str = Field("", title="Rule name")
    pattern: str = Field("", title="Regex pattern")
    colorspace: str = Field("", title="Colorspace name")
    ext: str = Field("", title="File extension")


class ImageIOFileRulesModel(BaseSettingsModel):
    activate_host_rules: bool = Field(False)
    rules: list[ImageIOFileRuleModel] = Field(
        default_factory=list,
        title="Rules"
    )

    @validator("rules")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class ImageIOSettings(BaseSettingsModel):
    """Hiero color management project settings. """
    _isGroup: bool = True
    activate_host_color_management: bool = Field(
        True, title="Enable Color Management"
    )
    ocio_config: ImageIOConfigModel = Field(
        default_factory=ImageIOConfigModel,
        title="OCIO config"
    )
    file_rules: ImageIOFileRulesModel = Field(
        default_factory=ImageIOFileRulesModel,
        title="File Rules"
    )
    workfile: WorkfileColorspaceSettings = Field(
        default_factory=WorkfileColorspaceSettings,
        title="Workfile"
    )
    """# TODO: enhance settings with host api:
    - old settings are using `regexInputs` key but we
      need to rename to `regex_inputs`
    - no need for `inputs` middle part. It can stay
      directly on `regex_inputs`
    """
    regexInputs:  RegexInputsModel = Field(
        default_factory=RegexInputsModel,
        title="Assign colorspace to clips via rules"
    )


DEFAULT_IMAGEIO_SETTINGS = {
    "workfile": {
        "ocioConfigName": "nuke-default",
        "workingSpace": "linear",
        "viewerLut": "sRGB",
        "eightBitLut": "sRGB",
        "sixteenBitLut": "sRGB",
        "logLut": "Cineon",
        "floatLut": "linear",
        "thumbnailLut": "sRGB",
        "monitorOutLut": "sRGB"
    },
    "regexInputs": {
        "inputs": [
            {
                "regex": "[^-a-zA-Z0-9](plateRef).*(?=mp4)",
                "colorspace": "sRGB"
            }
        ]
    }
}
