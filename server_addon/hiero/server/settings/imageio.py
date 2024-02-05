from pydantic import validator

from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names,
)


def ocio_configs_switcher_enum():
    return [
        {"value": "nuke-default", "label": "nuke-default"},
        {"value": "spi-vfx", "label": "spi-vfx"},
        {"value": "spi-anim", "label": "spi-anim"},
        {"value": "aces_0.1.1", "label": "aces_0.1.1"},
        {"value": "aces_0.7.1", "label": "aces_0.7.1"},
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

    ocioConfigName: str = SettingsField(
        title="OpenColorIO Config",
        description="Switch between OCIO configs",
        enum_resolver=ocio_configs_switcher_enum,
        conditionalEnum=True
    )
    workingSpace: str = SettingsField(
        title="Working Space"
    )
    viewerLut: str = SettingsField(
        title="Viewer"
    )
    eightBitLut: str = SettingsField(
        title="8-bit files"
    )
    sixteenBitLut: str = SettingsField(
        title="16-bit files"
    )
    logLut: str = SettingsField(
        title="Log files"
    )
    floatLut: str = SettingsField(
        title="Float files"
    )
    thumbnailLut: str = SettingsField(
        title="Thumnails"
    )
    monitorOutLut: str = SettingsField(
        title="Monitor"
    )


class ClipColorspaceRulesItems(BaseSettingsModel):
    _layout = "expanded"

    regex: str = SettingsField("", title="Regex expression")
    colorspace: str = SettingsField("", title="Colorspace")


class RegexInputsModel(BaseSettingsModel):
    inputs: list[ClipColorspaceRulesItems] = SettingsField(
        default_factory=list,
        title="Inputs"
    )


class ImageIOConfigModel(BaseSettingsModel):
    override_global_config: bool = SettingsField(
        False,
        title="Override global OCIO config"
    )
    filepath: list[str] = SettingsField(
        default_factory=list,
        title="Config path"
    )


class ImageIOFileRuleModel(BaseSettingsModel):
    name: str = SettingsField("", title="Rule name")
    pattern: str = SettingsField("", title="Regex pattern")
    colorspace: str = SettingsField("", title="Colorspace name")
    ext: str = SettingsField("", title="File extension")


class ImageIOFileRulesModel(BaseSettingsModel):
    activate_host_rules: bool = SettingsField(False)
    rules: list[ImageIOFileRuleModel] = SettingsField(
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
    activate_host_color_management: bool = SettingsField(
        True, title="Enable Color Management"
    )
    ocio_config: ImageIOConfigModel = SettingsField(
        default_factory=ImageIOConfigModel,
        title="OCIO config"
    )
    file_rules: ImageIOFileRulesModel = SettingsField(
        default_factory=ImageIOFileRulesModel,
        title="File Rules"
    )
    workfile: WorkfileColorspaceSettings = SettingsField(
        default_factory=WorkfileColorspaceSettings,
        title="Workfile"
    )
    """# TODO: enhance settings with host api:
    - old settings are using `regexInputs` key but we
      need to rename to `regex_inputs`
    - no need for `inputs` middle part. It can stay
      directly on `regex_inputs`
    """
    regexInputs: RegexInputsModel = SettingsField(
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
