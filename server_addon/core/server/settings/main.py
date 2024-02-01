import json
from pydantic import validator
from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    MultiplatformPathListModel,
    ensure_unique_names,
    task_types_enum,
)
from ayon_server.exceptions import BadRequestException

from .publish_plugins import PublishPuginsModel, DEFAULT_PUBLISH_VALUES
from .tools import GlobalToolsModel, DEFAULT_TOOLS_VALUES


class DiskMappingItemModel(BaseSettingsModel):
    _layout = "expanded"
    source: str = SettingsField("", title="Source")
    destination: str = SettingsField("", title="Destination")


class DiskMappingModel(BaseSettingsModel):
    windows: list[DiskMappingItemModel] = SettingsField(
        title="Windows",
        default_factory=list,
    )
    linux: list[DiskMappingItemModel] = SettingsField(
        title="Linux",
        default_factory=list,
    )
    darwin: list[DiskMappingItemModel] = SettingsField(
        title="MacOS",
        default_factory=list,
    )


class ImageIOFileRuleModel(BaseSettingsModel):
    name: str = SettingsField("", title="Rule name")
    pattern: str = SettingsField("", title="Regex pattern")
    colorspace: str = SettingsField("", title="Colorspace name")
    ext: str = SettingsField("", title="File extension")


class CoreImageIOFileRulesModel(BaseSettingsModel):
    activate_global_file_rules: bool = SettingsField(False)
    rules: list[ImageIOFileRuleModel] = SettingsField(
        default_factory=list,
        title="Rules"
    )

    @validator("rules")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class CoreImageIOConfigModel(BaseSettingsModel):
    filepath: list[str] = SettingsField(
        default_factory=list, title="Config path"
    )


class CoreImageIOBaseModel(BaseSettingsModel):
    activate_global_color_management: bool = SettingsField(
        False,
        title="Enable Color Management"
    )
    ocio_config: CoreImageIOConfigModel = SettingsField(
        default_factory=CoreImageIOConfigModel,
        title="OCIO config"
    )
    file_rules: CoreImageIOFileRulesModel = SettingsField(
        default_factory=CoreImageIOFileRulesModel,
        title="File Rules"
    )


class VersionStartCategoryProfileModel(BaseSettingsModel):
    _layout = "expanded"
    host_names: list[str] = SettingsField(
        default_factory=list,
        title="Host names"
    )
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list,
        title="Task names"
    )
    product_types: list[str] = SettingsField(
        default_factory=list,
        title="Product types"
    )
    product_names: list[str] = SettingsField(
        default_factory=list,
        title="Product names"
    )
    version_start: int = SettingsField(
        1,
        title="Version Start",
        ge=0
    )


class VersionStartCategoryModel(BaseSettingsModel):
    profiles: list[VersionStartCategoryProfileModel] = SettingsField(
        default_factory=list,
        title="Profiles"
    )


class CoreSettings(BaseSettingsModel):
    studio_name: str = SettingsField("", title="Studio name", scope=["studio"])
    studio_code: str = SettingsField("", title="Studio code", scope=["studio"])
    environments: str = SettingsField(
        "{}",
        title="Global environment variables",
        widget="textarea",
        scope=["studio"],
    )
    disk_mapping: DiskMappingModel = SettingsField(
        default_factory=DiskMappingModel,
        title="Disk mapping",
    )
    tools: GlobalToolsModel = SettingsField(
        default_factory=GlobalToolsModel,
        title="Tools"
    )
    version_start_category: VersionStartCategoryModel = SettingsField(
        default_factory=VersionStartCategoryModel,
        title="Version start"
    )
    imageio: CoreImageIOBaseModel = SettingsField(
        default_factory=CoreImageIOBaseModel,
        title="Color Management (ImageIO)"
    )
    publish: PublishPuginsModel = SettingsField(
        default_factory=PublishPuginsModel,
        title="Publish plugins"
    )
    project_plugins: MultiplatformPathListModel = SettingsField(
        default_factory=MultiplatformPathListModel,
        title="Additional Project Plugin Paths",
    )
    project_folder_structure: str = SettingsField(
        "{}",
        widget="textarea",
        title="Project folder structure",
        section="---"
    )
    project_environments: str = SettingsField(
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
    "environments": "{\n\"STUDIO_SW\": {\n        \"darwin\": \"/mnt/REPO_SW\",\n        \"linux\": \"/mnt/REPO_SW\",\n        \"windows\": \"P:/REPO_SW\"\n    }\n}",
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
