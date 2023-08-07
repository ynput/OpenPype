import json
from pydantic import Field, validator

from ayon_server.settings import BaseSettingsModel, ensure_unique_names
from ayon_server.exceptions import BadRequestException


def validate_json_dict(value):
    if not value.strip():
        return "{}"
    try:
        converted_value = json.loads(value)
        success = isinstance(converted_value, dict)
    except json.JSONDecodeError as exc:
        print(exc)
        success = False

    if not success:
        raise BadRequestException(
            "Environment's can't be parsed as json object"
        )
    return value


class MultiplatformStrList(BaseSettingsModel):
    windows: list[str] = Field(default_factory=list, title="Windows")
    linux: list[str] = Field(default_factory=list, title="Linux")
    darwin: list[str] = Field(default_factory=list, title="MacOS")


class AppVariant(BaseSettingsModel):
    name: str = Field("", title="Name")
    label: str = Field("", title="Label")
    executables: MultiplatformStrList = Field(
        default_factory=MultiplatformStrList, title="Executables"
    )
    arguments: MultiplatformStrList = Field(
        default_factory=MultiplatformStrList, title="Arguments"
    )
    environment: str = Field("{}", title="Environment", widget="textarea")

    @validator("environment")
    def validate_json(cls, value):
        return validate_json_dict(value)


class AppVariantWithPython(AppVariant):
    use_python_2: bool = Field(False, title="Use Python 2")


class AppGroup(BaseSettingsModel):
    enabled: bool = Field(True)
    label: str = Field("", title="Label")
    host_name: str = Field("", title="Host name")
    icon: str = Field("", title="Icon")
    environment: str = Field("{}", title="Environment", widget="textarea")

    variants: list[AppVariant] = Field(
        default_factory=list,
        title="Variants",
        description="Different variants of the applications",
        section="Variants",
    )

    @validator("variants")
    def validate_unique_name(cls, value):
        ensure_unique_names(value)
        return value


class AppGroupWithPython(AppGroup):
    variants: list[AppVariantWithPython] = Field(
        default_factory=list,
        title="Variants",
        description="Different variants of the applications",
        section="Variants",
    )


class AdditionalAppGroup(BaseSettingsModel):
    enabled: bool = Field(True)
    name: str = Field("", title="Name")
    label: str = Field("", title="Label")
    host_name: str = Field("", title="Host name")
    icon: str = Field("", title="Icon")
    environment: str = Field("{}", title="Environment", widget="textarea")

    variants: list[AppVariantWithPython] = Field(
        default_factory=list,
        title="Variants",
        description="Different variants of the applications",
        section="Variants",
    )

    @validator("variants")
    def validate_unique_name(cls, value):
        ensure_unique_names(value)
        return value


class ToolVariantModel(BaseSettingsModel):
    name: str = Field("", title="Name")
    label: str = Field("", title="Label")
    host_names: list[str] = Field(default_factory=list, title="Hosts")
    # TODO use applications enum if possible
    app_variants: list[str] = Field(default_factory=list, title="Applications")
    environment: str = Field("{}", title="Environments", widget="textarea")

    @validator("environment")
    def validate_json(cls, value):
        return validate_json_dict(value)


class ToolGroupModel(BaseSettingsModel):
    name: str = Field("", title="Name")
    label: str = Field("", title="Label")
    environment: str = Field("{}", title="Environments", widget="textarea")
    variants: list[ToolVariantModel] = Field(
        default_factory=ToolVariantModel
    )

    @validator("environment")
    def validate_json(cls, value):
        return validate_json_dict(value)

    @validator("variants")
    def validate_unique_name(cls, value):
        ensure_unique_names(value)
        return value


class ApplicationsSettings(BaseSettingsModel):
    """Applications settings"""

    maya: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Autodesk Maya")
    adsk_3dsmax: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Autodesk 3ds Max")
    flame: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Autodesk Flame")
    nuke: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Nuke")
    nukeassist: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Nuke Assist")
    nukex: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Nuke X")
    nukestudio: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Nuke Studio")
    hiero: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Hiero")
    fusion: AppGroup = Field(
        default_factory=AppGroupWithPython, title="Fusion")
    resolve: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Resolve")
    houdini: AppGroupWithPython = Field(
        default_factory=AppGroupWithPython, title="Houdini")
    blender: AppGroup = Field(
        default_factory=AppGroupWithPython, title="Blender")
    harmony: AppGroup = Field(
        default_factory=AppGroupWithPython, title="Harmony")
    tvpaint: AppGroup = Field(
        default_factory=AppGroupWithPython, title="TVPaint")
    photoshop: AppGroup = Field(
        default_factory=AppGroupWithPython, title="Adobe Photoshop")
    aftereffects: AppGroup = Field(
        default_factory=AppGroupWithPython, title="Adobe After Effects")
    celaction: AppGroup = Field(
        default_factory=AppGroupWithPython, title="Celaction 2D")
    unreal: AppGroup = Field(
        default_factory=AppGroupWithPython, title="Unreal Editor")
    additional_apps: list[AdditionalAppGroup] = Field(
        default_factory=list, title="Additional Applications")

    @validator("additional_apps")
    def validate_unique_name(cls, value):
        ensure_unique_names(value)
        return value


class ApplicationsAddonSettings(BaseSettingsModel):
    applications: ApplicationsSettings = Field(
        default_factory=ApplicationsSettings,
        title="Applications",
        scope=["studio"]
    )
    tool_groups: list[ToolGroupModel] = Field(
        default_factory=list,
        scope=["studio"]
    )
    only_available: bool = Field(
        True, title="Show only available applications")

    @validator("tool_groups")
    def validate_unique_name(cls, value):
        ensure_unique_names(value)
        return value


DEFAULT_VALUES = {
    "only_available": False
}
