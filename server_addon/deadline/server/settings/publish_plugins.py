from pydantic import Field, validator

from ayon_server.settings import BaseSettingsModel, ensure_unique_names


class CollectDefaultDeadlineServerModel(BaseSettingsModel):
    """Settings for event handlers running in ftrack service."""

    pass_mongo_url: bool = Field(title="Pass Mongo url to job")


class CollectDeadlinePoolsModel(BaseSettingsModel):
    """Settings Deadline default pools."""

    primary_pool: str = Field(title="Primary Pool")

    secondary_pool: str = Field(title="Secondary Pool")


class ValidateExpectedFilesModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    active: bool = Field(True, title="Active")
    allow_user_override: bool = Field(
        True, title="Allow user change frame range"
    )
    families: list[str] = Field(
        default_factory=list, title="Trigger on families"
    )
    targets: list[str] = Field(
        default_factory=list, title="Trigger for plugins"
    )


def tile_assembler_enum():
    """Return a list of value/label dicts for the enumerator.

    Returning a list of dicts is used to allow for a custom label to be
    displayed in the UI.
    """
    return [
        {
            "value": "DraftTileAssembler",
            "label": "Draft Tile Assembler"
        },
        {
            "value": "OpenPypeTileAssembler",
            "label": "Open Image IO"
        }
    ]


class ScenePatchesSubmodel(BaseSettingsModel):
    _layout = "expanded"
    name: str = Field(title="Patch name")
    regex: str = Field(title="Patch regex")
    line: str = Field(title="Patch line")


class MayaSubmitDeadlineModel(BaseSettingsModel):
    """Maya deadline submitter settings."""

    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    use_published: bool = Field(title="Use Published scene")
    import_reference: bool = Field(title="Use Scene with Imported Reference")
    asset_dependencies: bool = Field(title="Use Asset dependencies")
    priority: int = Field(title="Priority")
    tile_priority: int = Field(title="Tile Priority")
    group: str = Field(title="Group")
    limit: list[str] = Field(
        default_factory=list,
        title="Limit Groups"
    )
    tile_assembler_plugin: str = Field(
        title="Tile Assembler Plugin",
        enum_resolver=tile_assembler_enum,
    )
    jobInfo: str = Field(
        title="Additional JobInfo data",
        widget="textarea",
    )
    pluginInfo: str = Field(
        title="Additional PluginInfo data",
        widget="textarea",
    )

    scene_patches: list[ScenePatchesSubmodel] = Field(
        default_factory=list,
        title="Scene patches",
    )
    strict_error_checking: bool = Field(
        title="Disable Strict Error Check profiles"
    )

    @validator("limit", "scene_patches")
    def validate_unique_names(cls, value):
        ensure_unique_names(value)
        return value


class MaxSubmitDeadlineModel(BaseSettingsModel):
    enabled: bool = Field(True)
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    use_published: bool = Field(title="Use Published scene")
    priority: int = Field(title="Priority")
    chunk_size: int = Field(title="Frame per Task")
    group: str = Field("", title="Group Name")


class EnvSearchReplaceSubmodel(BaseSettingsModel):
    _layout = "compact"
    name: str = Field(title="Name")
    value: str = Field(title="Value")


class LimitGroupsSubmodel(BaseSettingsModel):
    _layout = "expanded"
    name: str = Field(title="Name")
    value: list[str] = Field(
        default_factory=list,
        title="Limit Groups"
    )


def fusion_deadline_plugin_enum():
    """Return a list of value/label dicts for the enumerator.

    Returning a list of dicts is used to allow for a custom label to be
    displayed in the UI.
    """
    return [
        {
            "value": "Fusion",
            "label": "Fusion"
        },
        {
            "value": "FusionCmd",
            "label": "FusionCmd"
        }
    ]


class FusionSubmitDeadlineModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    optional: bool = Field(False, title="Optional")
    active: bool = Field(True, title="Active")
    priority: int = Field(50, title="Priority")
    chunk_size: int = Field(10, title="Frame per Task")
    concurrent_tasks: int = Field(1, title="Number of concurrent tasks")
    group: str = Field("", title="Group Name")
    plugin: str = Field("Fusion",
                        enum_resolver=fusion_deadline_plugin_enum,
                        title="Deadline Plugin")


class NukeSubmitDeadlineModel(BaseSettingsModel):
    """Nuke deadline submitter settings."""

    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    priority: int = Field(title="Priority")
    chunk_size: int = Field(title="Chunk Size")
    concurrent_tasks: int = Field(title="Number of concurrent tasks")
    group: str = Field(title="Group")
    department: str = Field(title="Department")
    use_gpu: bool = Field(title="Use GPU")

    env_allowed_keys: list[str] = Field(
        default_factory=list,
        title="Allowed environment keys"
    )

    env_search_replace_values: list[EnvSearchReplaceSubmodel] = Field(
        default_factory=list,
        title="Search & replace in environment values",
    )

    limit_groups: list[LimitGroupsSubmodel] = Field(
        default_factory=list,
        title="Limit Groups",
    )

    @validator("limit_groups", "env_allowed_keys", "env_search_replace_values")
    def validate_unique_names(cls, value):
        ensure_unique_names(value)
        return value


class HarmonySubmitDeadlineModel(BaseSettingsModel):
    """Harmony deadline submitter settings."""

    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    use_published: bool = Field(title="Use Published scene")
    priority: int = Field(title="Priority")
    chunk_size: int = Field(title="Chunk Size")
    group: str = Field(title="Group")
    department: str = Field(title="Department")


class AfterEffectsSubmitDeadlineModel(BaseSettingsModel):
    """After Effects deadline submitter settings."""

    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    use_published: bool = Field(title="Use Published scene")
    priority: int = Field(title="Priority")
    chunk_size: int = Field(title="Chunk Size")
    group: str = Field(title="Group")
    department: str = Field(title="Department")
    multiprocess: bool = Field(title="Optional")


class CelactionSubmitDeadlineModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    deadline_department: str = Field("", title="Deadline apartment")
    deadline_priority: int = Field(50, title="Deadline priority")
    deadline_pool: str = Field("", title="Deadline pool")
    deadline_pool_secondary: str = Field("", title="Deadline pool (secondary)")
    deadline_group: str = Field("", title="Deadline Group")
    deadline_chunk_size: int = Field(10, title="Deadline Chunk size")
    deadline_job_delay: str = Field(
        "", title="Delay job (timecode dd:hh:mm:ss)"
    )


class BlenderSubmitDeadlineModel(BaseSettingsModel):
    enabled: bool = Field(True)
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    use_published: bool = Field(title="Use Published scene")
    priority: int = Field(title="Priority")
    chunk_size: int = Field(title="Frame per Task")
    group: str = Field("", title="Group Name")


class AOVFilterSubmodel(BaseSettingsModel):
    _layout = "expanded"
    name: str = Field(title="Host")
    value: list[str] = Field(
        default_factory=list,
        title="AOV regex"
    )


class ProcessSubmittedJobOnFarmModel(BaseSettingsModel):
    """Process submitted job on farm."""

    enabled: bool = Field(title="Enabled")
    deadline_department: str = Field(title="Department")
    deadline_pool: str = Field(title="Pool")
    deadline_group: str = Field(title="Group")
    deadline_chunk_size: int = Field(title="Chunk Size")
    deadline_priority: int = Field(title="Priority")
    publishing_script: str = Field(title="Publishing script path")
    skip_integration_repre_list: list[str] = Field(
        default_factory=list,
        title="Skip integration of representation with ext"
    )
    aov_filter: list[AOVFilterSubmodel] = Field(
        default_factory=list,
        title="Reviewable products filter",
    )

    @validator("aov_filter", "skip_integration_repre_list")
    def validate_unique_names(cls, value):
        ensure_unique_names(value)
        return value


class PublishPluginsModel(BaseSettingsModel):
    CollectDefaultDeadlineServer: CollectDefaultDeadlineServerModel = Field(
        default_factory=CollectDefaultDeadlineServerModel,
        title="Default Deadline Webservice")
    CollectDefaultDeadlineServer: CollectDefaultDeadlineServerModel = Field(
        default_factory=CollectDefaultDeadlineServerModel,
        title="Default Deadline Webservice")
    CollectDeadlinePools: CollectDeadlinePoolsModel = Field(
        default_factory=CollectDeadlinePoolsModel,
        title="Default Pools")
    ValidateExpectedFiles: ValidateExpectedFilesModel = Field(
        default_factory=ValidateExpectedFilesModel,
        title="Validate Expected Files"
    )
    MayaSubmitDeadline: MayaSubmitDeadlineModel = Field(
        default_factory=MayaSubmitDeadlineModel,
        title="Maya Submit to deadline")
    MaxSubmitDeadline: MaxSubmitDeadlineModel = Field(
        default_factory=MaxSubmitDeadlineModel,
        title="Max Submit to deadline")
    FusionSubmitDeadline: FusionSubmitDeadlineModel = Field(
        default_factory=FusionSubmitDeadlineModel,
        title="Fusion submit to Deadline")
    NukeSubmitDeadline: NukeSubmitDeadlineModel = Field(
        default_factory=NukeSubmitDeadlineModel,
        title="Nuke Submit to deadline")
    HarmonySubmitDeadline: HarmonySubmitDeadlineModel = Field(
        default_factory=HarmonySubmitDeadlineModel,
        title="Harmony Submit to deadline")
    AfterEffectsSubmitDeadline: AfterEffectsSubmitDeadlineModel = Field(
        default_factory=AfterEffectsSubmitDeadlineModel,
        title="After Effects to deadline")
    CelactionSubmitDeadline: CelactionSubmitDeadlineModel = Field(
        default_factory=CelactionSubmitDeadlineModel,
        title="Celaction Submit Deadline")
    BlenderSubmitDeadline: BlenderSubmitDeadlineModel = Field(
        default_factory=BlenderSubmitDeadlineModel,
        title="Blender Submit Deadline")
    ProcessSubmittedJobOnFarm: ProcessSubmittedJobOnFarmModel = Field(
        default_factory=ProcessSubmittedJobOnFarmModel,
        title="Process submitted job on farm.")


DEFAULT_DEADLINE_PLUGINS_SETTINGS = {
    "CollectDefaultDeadlineServer": {
        "pass_mongo_url": True
    },
    "CollectDeadlinePools": {
        "primary_pool": "",
        "secondary_pool": ""
    },
    "ValidateExpectedFiles": {
        "enabled": True,
        "active": True,
        "allow_user_override": True,
        "families": [
            "render"
        ],
        "targets": [
            "deadline"
        ]
    },
    "MayaSubmitDeadline": {
        "enabled": True,
        "optional": False,
        "active": True,
        "tile_assembler_plugin": "DraftTileAssembler",
        "use_published": True,
        "import_reference": False,
        "asset_dependencies": True,
        "strict_error_checking": True,
        "priority": 50,
        "tile_priority": 50,
        "group": "none",
        "limit": [],
        # this used to be empty dict
        "jobInfo": "",
        # this used to be empty dict
        "pluginInfo": "",
        "scene_patches": []
    },
    "MaxSubmitDeadline": {
        "enabled": True,
        "optional": False,
        "active": True,
        "use_published": True,
        "priority": 50,
        "chunk_size": 10,
        "group": "none"
    },
    "FusionSubmitDeadline": {
        "enabled": True,
        "optional": False,
        "active": True,
        "priority": 50,
        "chunk_size": 10,
        "concurrent_tasks": 1,
        "group": ""
    },
    "NukeSubmitDeadline": {
        "enabled": True,
        "optional": False,
        "active": True,
        "priority": 50,
        "chunk_size": 10,
        "concurrent_tasks": 1,
        "group": "",
        "department": "",
        "use_gpu": True,
        "env_allowed_keys": [],
        "env_search_replace_values": [],
        "limit_groups": []
    },
    "HarmonySubmitDeadline": {
        "enabled": True,
        "optional": False,
        "active": True,
        "use_published": True,
        "priority": 50,
        "chunk_size": 10000,
        "group": "",
        "department": ""
    },
    "AfterEffectsSubmitDeadline": {
        "enabled": True,
        "optional": False,
        "active": True,
        "use_published": True,
        "priority": 50,
        "chunk_size": 10000,
        "group": "",
        "department": "",
        "multiprocess": True
    },
    "CelactionSubmitDeadline": {
        "enabled": True,
        "deadline_department": "",
        "deadline_priority": 50,
        "deadline_pool": "",
        "deadline_pool_secondary": "",
        "deadline_group": "",
        "deadline_chunk_size": 10,
        "deadline_job_delay": "00:00:00:00"
    },
    "BlenderSubmitDeadline": {
        "enabled": True,
        "optional": False,
        "active": True,
        "use_published": True,
        "priority": 50,
        "chunk_size": 10,
        "group": "none"
    },
    "ProcessSubmittedJobOnFarm": {
        "enabled": True,
        "deadline_department": "",
        "deadline_pool": "",
        "deadline_group": "",
        "deadline_chunk_size": 1,
        "deadline_priority": 50,
        "publishing_script": "",
        "skip_integration_repre_list": [],
        "aov_filter": [
            {
                "name": "maya",
                "value": [
                    ".*([Bb]eauty).*"
                ]
            },
            {
                "name": "blender",
                "value": [
                    ".*([Bb]eauty).*"
                ]
            },
            {
                "name": "aftereffects",
                "value": [
                    ".*"
                ]
            },
            {
                "name": "celaction",
                "value": [
                    ".*"
                ]
            },
            {
                "name": "harmony",
                "value": [
                    ".*"
                ]
            },
            {
                "name": "max",
                "value": [
                    ".*"
                ]
            },
            {
                "name": "fusion",
                "value": [
                    ".*"
                ]
            }
        ]
    }
}
