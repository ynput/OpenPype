from pydantic import Field, validator
from ayon_server.settings import BaseSettingsModel, ensure_unique_names


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


class ImageIORemappingRulesModel(BaseSettingsModel):
    host_native_name: str = Field(
        title="Application native colorspace name"
    )
    ocio_name: str = Field(title="OCIO colorspace name")


class ImageIORemappingModel(BaseSettingsModel):
    rules: list[ImageIORemappingRulesModel] = Field(
        default_factory=list
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


class ProfileNamesMappingInputsModel(BaseSettingsModel):
    _layout = "expanded"

    flameName: str = Field("", title="Flame name")
    ocioName: str = Field("", title="OCIO name")


class ProfileNamesMappingModel(BaseSettingsModel):
    _layout = "expanded"

    inputs: list[ProfileNamesMappingInputsModel] = Field(
        default_factory=list,
        title="Profile names mapping"
    )


class ImageIOProjectModel(BaseSettingsModel):
    colourPolicy: str = Field(
        "ACES 1.1",
        title="Colour Policy (name or path)",
        section="Project"
    )
    frameDepth: str = Field(
        "16-bit fp",
        title="Image Depth"
    )
    fieldDominance: str = Field(
        "PROGRESSIVE",
        title="Field Dominance"
    )


class FlameImageIOModel(BaseSettingsModel):
    _isGroup = True
    activate_host_color_management: bool = Field(
        True, title="Enable Color Management"
    )
    remapping: ImageIORemappingModel = Field(
        title="Remapping colorspace names",
        default_factory=ImageIORemappingModel
    )
    ocio_config: ImageIOConfigModel = Field(
        default_factory=ImageIOConfigModel,
        title="OCIO config"
    )
    file_rules: ImageIOFileRulesModel = Field(
        default_factory=ImageIOFileRulesModel,
        title="File Rules"
    )
    # NOTE 'project' attribute was expanded to this model but that caused
    #   inconsistency with v3 settings and harder conversion handling
    #   - it can be moved back but keep in mind that it must be handled in v3
    #       conversion script too
    project: ImageIOProjectModel = Field(
        default_factory=ImageIOProjectModel,
        title="Project"
    )
    profilesMapping: ProfileNamesMappingModel = Field(
        default_factory=ProfileNamesMappingModel,
        title="Profile names mapping"
    )


DEFAULT_IMAGEIO_SETTINGS = {
    "project": {
        "colourPolicy": "ACES 1.1",
        "frameDepth": "16-bit fp",
        "fieldDominance": "PROGRESSIVE"
    },
    "profilesMapping": {
        "inputs": [
            {
                "flameName": "ACEScg",
                "ocioName": "ACES - ACEScg"
            },
            {
                "flameName": "Rec.709 video",
                "ocioName": "Output - Rec.709"
            }
        ]
    }
}
