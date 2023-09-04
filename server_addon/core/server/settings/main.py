import json
from pydantic import Field, validator
from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathListModel,
    ensure_unique_names,
    task_types_enum,
)
from ayon_server.exceptions import BadRequestException

from .publish_plugins import PublishPuginsModel, DEFAULT_PUBLISH_VALUES
from .tools import GlobalToolsModel, DEFAULT_TOOLS_VALUES


class ImageIOFileRuleModel(BaseSettingsModel):
    name: str = Field("", title="Rule name")
    pattern: str = Field("", title="Regex pattern")
    colorspace: str = Field("", title="Colorspace name")
    ext: str = Field("", title="File extension")


class CoreImageIOFileRulesModel(BaseSettingsModel):
    activate_global_file_rules: bool = Field(False)
    rules: list[ImageIOFileRuleModel] = Field(
        default_factory=list,
        title="Rules"
    )

    @validator("rules")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class CoreImageIOConfigModel(BaseSettingsModel):
    filepath: list[str] = Field(default_factory=list, title="Config path")


class CoreImageIOBaseModel(BaseSettingsModel):
    activate_global_color_management: bool = Field(
        False,
        title="Enable Color Management"
    )
    ocio_config: CoreImageIOConfigModel = Field(
        default_factory=CoreImageIOConfigModel,
        title="OCIO config"
    )
    file_rules: CoreImageIOFileRulesModel = Field(
        default_factory=CoreImageIOFileRulesModel,
        title="File Rules"
    )


class VersionStartCategoryProfileModel(BaseSettingsModel):
    _layout = "expanded"
    host_names: list[str] = Field(
        default_factory=list,
        title="Host names"
    )
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = Field(
        default_factory=list,
        title="Task names"
    )
    product_types: list[str] = Field(
        default_factory=list,
        title="Product types"
    )
    product_names: list[str] = Field(
        default_factory=list,
        title="Product names"
    )
    version_start: int = Field(
        1,
        title="Version Start",
        ge=0
    )


class VersionStartCategoryModel(BaseSettingsModel):
    profiles: list[VersionStartCategoryProfileModel] = Field(
        default_factory=list,
        title="Profiles"
    )


class CoreSettings(BaseSettingsModel):
    studio_name: str = Field("", title="Studio name", scope=["studio"])
    studio_code: str = Field("", title="Studio code", scope=["studio"])
    environments: str = Field(
        "{}",
        title="Global environment variables",
        widget="textarea",
        scope=["studio"],
    )
    tools: GlobalToolsModel = Field(
        default_factory=GlobalToolsModel,
        title="Tools"
    )
    version_start_category: VersionStartCategoryModel = Field(
        default_factory=VersionStartCategoryModel,
        title="Version start"
    )
    imageio: CoreImageIOBaseModel = Field(
        default_factory=CoreImageIOBaseModel,
        title="Color Management (ImageIO)"
    )
    publish: PublishPuginsModel = Field(
        default_factory=PublishPuginsModel,
        title="Publish plugins"
    )
    project_plugins: MultiplatformPathListModel = Field(
        default_factory=MultiplatformPathListModel,
        title="Additional Project Plugin Paths",
    )
    project_folder_structure: str = Field(
        "{}",
        widget="textarea",
        title="Project folder structure",
        section="---"
    )
    project_environments: str = Field(
        "{}",
        widget="textarea",
        title="Project environments",
        section="---"
    )

    @validator(
        "environments",
        "project_folder_structure",
        "project_environments")
    def validate_json(cls, value):
        if not value.strip():
            return "{}"
        try:
            converted_value = json.loads(value)
            success = isinstance(converted_value, dict)
        except json.JSONDecodeError:
            success = False

        if not success:
            raise BadRequestException(
                "Environment's can't be parsed as json object"
            )
        return value


DEFAULT_VALUES = {
    "imageio": {
        "activate_global_color_management": False,
        "ocio_config": {
            "filepath": [
                "{BUILTIN_OCIO_ROOT}/aces_1.2/config.ocio",
                "{BUILTIN_OCIO_ROOT}/nuke-default/config.ocio"
            ]
        },
        "file_rules": {
            "activate_global_file_rules": False,
            "rules": [
                {
                    "name": "example",
                    "pattern": ".*(beauty).*",
                    "colorspace": "ACES - ACEScg",
                    "ext": "exr"
                }
            ]
        }
    },
    "studio_name": "",
    "studio_code": "",
    "environments": "{}",
    "tools": DEFAULT_TOOLS_VALUES,
    "version_start_category": {
        "profiles": []
    },
    "publish": DEFAULT_PUBLISH_VALUES,
    "project_folder_structure": json.dumps({
        "__project_root__": {
            "prod": {},
            "resources": {
                "footage": {
                    "plates": {},
                    "offline": {}
                },
                "audio": {},
                "art_dept": {}
            },
            "editorial": {},
            "assets": {
                "characters": {},
                "locations": {}
            },
            "shots": {}
        }
    }, indent=4),
    "project_plugins": {
        "windows": [],
        "darwin": [],
        "linux": []
    },
    "project_environments": "{}"
}
