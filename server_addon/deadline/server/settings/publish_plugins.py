from pydantic import validator

from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names,
)


class CollectDeadlinePoolsModel(BaseSettingsModel):
    """Settings Deadline default pools."""

    primary_pool: str = SettingsField(title="Primary Pool")

    secondary_pool: str = SettingsField(title="Secondary Pool")


class ValidateExpectedFilesModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    active: bool = SettingsField(True, title="Active")
    allow_user_override: bool = SettingsField(
        True, title="Allow user change frame range"
    )
    families: list[str] = SettingsField(
        default_factory=list, title="Trigger on families"
    )
    targets: list[str] = SettingsField(
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
    name: str = SettingsField(title="Patch name")
    regex: str = SettingsField(title="Patch regex")
    line: str = SettingsField(title="Patch line")


class MayaSubmitDeadlineModel(BaseSettingsModel):
    """Maya deadline submitter settings."""

    enabled: bool = SettingsField(title="Enabled")
    optional: bool = SettingsField(title="Optional")
    active: bool = SettingsField(title="Active")
    use_published: bool = SettingsField(title="Use Published scene")
    import_reference: bool = SettingsField(
        title="Use Scene with Imported Reference"
    )
    asset_dependencies: bool = SettingsField(title="Use Asset dependencies")
    priority: int = SettingsField(title="Priority")
    tile_priority: int = SettingsField(title="Tile Priority")
    group: str = SettingsField(title="Group")
    limit: list[str] = SettingsField(
        default_factory=list,
        title="Limit Groups"
    )
    tile_assembler_plugin: str = SettingsField(
        title="Tile Assembler Plugin",
        enum_resolver=tile_assembler_enum,
    )
    jobInfo: str = SettingsField(
        title="Additional JobInfo data",
        widget="textarea",
    )
    pluginInfo: str = SettingsField(
        title="Additional PluginInfo data",
        widget="textarea",
    )

    scene_patches: list[ScenePatchesSubmodel] = SettingsField(
        default_factory=list,
        title="Scene patches",
    )
    strict_error_checking: bool = SettingsField(
        title="Disable Strict Error Check profiles"
    )

    @validator("scene_patches")
    def validate_unique_names(cls, value):
        ensure_unique_names(value)
        return value


class MaxSubmitDeadlineModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)
    optional: bool = SettingsField(title="Optional")
    active: bool = SettingsField(title="Active")
    use_published: bool = SettingsField(title="Use Published scene")
    priority: int = SettingsField(title="Priority")
    chunk_size: int = SettingsField(title="Frame per Task")
    group: str = SettingsField("", title="Group Name")


class EnvSearchReplaceSubmodel(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(title="Name")
    value: str = SettingsField(title="Value")


class LimitGroupsSubmodel(BaseSettingsModel):
    _layout = "expanded"
    name: str = SettingsField(title="Name")
    value: list[str] = SettingsField(
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
    enabled: bool = SettingsField(True, title="Enabled")
    optional: bool = SettingsField(False, title="Optional")
    active: bool = SettingsField(True, title="Active")
    priority: int = SettingsField(50, title="Priority")
    chunk_size: int = SettingsField(10, title="Frame per Task")
    concurrent_tasks: int = SettingsField(
        1, title="Number of concurrent tasks"
    )
    group: str = SettingsField("", title="Group Name")
    plugin: str = SettingsField("Fusion",
                        enum_resolver=fusion_deadline_plugin_enum,
                        title="Deadline Plugin")


class NukeSubmitDeadlineModel(BaseSettingsModel):
    """Nuke deadline submitter settings."""

    enabled: bool = SettingsField(title="Enabled")
    optional: bool = SettingsField(title="Optional")
    active: bool = SettingsField(title="Active")
    priority: int = SettingsField(title="Priority")
    chunk_size: int = SettingsField(title="Chunk Size")
    concurrent_tasks: int = SettingsField(title="Number of concurrent tasks")
    group: str = SettingsField(title="Group")
    department: str = SettingsField(title="Department")
    use_gpu: bool = SettingsField(title="Use GPU")
    workfile_dependency: bool = SettingsField(title="Workfile Dependency")
    use_published_workfile: bool = SettingsField(
        title="Use Published Workfile"
    )

    env_allowed_keys: list[str] = SettingsField(
        default_factory=list,
        title="Allowed environment keys"
    )

    env_search_replace_values: list[EnvSearchReplaceSubmodel] = SettingsField(
        default_factory=list,
        title="Search & replace in environment values",
    )

    limit_groups: list[LimitGroupsSubmodel] = SettingsField(
        default_factory=list,
        title="Limit Groups",
    )

    @validator(
        "limit_groups",
        "env_allowed_keys",
        "env_search_replace_values")
    def validate_unique_names(cls, value):
        ensure_unique_names(value)
        return value


class HarmonySubmitDeadlineModel(BaseSettingsModel):
    """Harmony deadline submitter settings."""

    enabled: bool = SettingsField(title="Enabled")
    optional: bool = SettingsField(title="Optional")
    active: bool = SettingsField(title="Active")
    use_published: bool = SettingsField(title="Use Published scene")
    priority: int = SettingsField(title="Priority")
    chunk_size: int = SettingsField(title="Chunk Size")
    group: str = SettingsField(title="Group")
    department: str = SettingsField(title="Department")


class AfterEffectsSubmitDeadlineModel(BaseSettingsModel):
    """After Effects deadline submitter settings."""

    enabled: bool = SettingsField(title="Enabled")
    optional: bool = SettingsField(title="Optional")
    active: bool = SettingsField(title="Active")
    use_published: bool = SettingsField(title="Use Published scene")
    priority: int = SettingsField(title="Priority")
    chunk_size: int = SettingsField(title="Chunk Size")
    group: str = SettingsField(title="Group")
    department: str = SettingsField(title="Department")
    multiprocess: bool = SettingsField(title="Optional")


class CelactionSubmitDeadlineModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    deadline_department: str = SettingsField("", title="Deadline apartment")
    deadline_priority: int = SettingsField(50, title="Deadline priority")
    deadline_pool: str = SettingsField("", title="Deadline pool")
    deadline_pool_secondary: str = SettingsField(
        "", title="Deadline pool (secondary)"
    )
    deadline_group: str = SettingsField("", title="Deadline Group")
    deadline_chunk_size: int = SettingsField(10, title="Deadline Chunk size")
    deadline_job_delay: str = SettingsField(
        "", title="Delay job (timecode dd:hh:mm:ss)"
    )


class BlenderSubmitDeadlineModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)
    optional: bool = SettingsField(title="Optional")
    active: bool = SettingsField(title="Active")
    use_published: bool = SettingsField(title="Use Published scene")
    priority: int = SettingsField(title="Priority")
    chunk_size: int = SettingsField(title="Frame per Task")
    group: str = SettingsField("", title="Group Name")
    job_delay: str = SettingsField(
        "", title="Delay job (timecode dd:hh:mm:ss)"
    )


class AOVFilterSubmodel(BaseSettingsModel):
    _layout = "expanded"
    name: str = SettingsField(title="Host")
    value: list[str] = SettingsField(
        default_factory=list,
        title="AOV regex"
    )


class ProcessCacheJobFarmModel(BaseSettingsModel):
    """Process submitted job on farm."""

    enabled: bool = SettingsField(title="Enabled")
    deadline_department: str = SettingsField(title="Department")
    deadline_pool: str = SettingsField(title="Pool")
    deadline_group: str = SettingsField(title="Group")
    deadline_chunk_size: int = SettingsField(title="Chunk Size")
    deadline_priority: int = SettingsField(title="Priority")


class ProcessSubmittedJobOnFarmModel(BaseSettingsModel):
    """Process submitted job on farm."""

    enabled: bool = SettingsField(title="Enabled")
    deadline_department: str = SettingsField(title="Department")
    deadline_pool: str = SettingsField(title="Pool")
    deadline_group: str = SettingsField(title="Group")
    deadline_chunk_size: int = SettingsField(title="Chunk Size")
    deadline_priority: int = SettingsField(title="Priority")
    publishing_script: str = SettingsField(title="Publishing script path")
    skip_integration_repre_list: list[str] = SettingsField(
        default_factory=list,
        title="Skip integration of representation with ext"
    )
    aov_filter: list[AOVFilterSubmodel] = SettingsField(
        default_factory=list,
        title="Reviewable products filter",
    )

    @validator("aov_filter")
    def validate_unique_names(cls, value):
        ensure_unique_names(value)
        return value


class PublishPluginsModel(BaseSettingsModel):
    CollectDeadlinePools: CollectDeadlinePoolsModel = SettingsField(
        default_factory=CollectDeadlinePoolsModel,
        title="Default Pools")
    ValidateExpectedFiles: ValidateExpectedFilesModel = SettingsField(
        default_factory=ValidateExpectedFilesModel,
        title="Validate Expected Files"
    )
    MayaSubmitDeadline: MayaSubmitDeadlineModel = SettingsField(
        default_factory=MayaSubmitDeadlineModel,
        title="Maya Submit to deadline")
    MaxSubmitDeadline: MaxSubmitDeadlineModel = SettingsField(
        default_factory=MaxSubmitDeadlineModel,
        title="Max Submit to deadline")
    FusionSubmitDeadline: FusionSubmitDeadlineModel = SettingsField(
        default_factory=FusionSubmitDeadlineModel,
        title="Fusion submit to Deadline")
    NukeSubmitDeadline: NukeSubmitDeadlineModel = SettingsField(
        default_factory=NukeSubmitDeadlineModel,
        title="Nuke Submit to deadline")
    HarmonySubmitDeadline: HarmonySubmitDeadlineModel = SettingsField(
        default_factory=HarmonySubmitDeadlineModel,
        title="Harmony Submit to deadline")
    AfterEffectsSubmitDeadline: AfterEffectsSubmitDeadlineModel = (
        SettingsField(
            default_factory=AfterEffectsSubmitDeadlineModel,
            title="After Effects to deadline"
        )
    )
    CelactionSubmitDeadline: CelactionSubmitDeadlineModel = SettingsField(
        default_factory=CelactionSubmitDeadlineModel,
        title="Celaction Submit Deadline")
    BlenderSubmitDeadline: BlenderSubmitDeadlineModel = SettingsField(
        default_factory=BlenderSubmitDeadlineModel,
        title="Blender Submit Deadline")
    ProcessSubmittedCacheJobOnFarm: ProcessCacheJobFarmModel = SettingsField(
        default_factory=ProcessCacheJobFarmModel,
        title="Process submitted cache Job on farm.")
    ProcessSubmittedJobOnFarm: ProcessSubmittedJobOnFarmModel = SettingsField(
        default_factory=ProcessSubmittedJobOnFarmModel,
        title="Process submitted job on farm.")


DEFAULT_DEADLINE_PLUGINS_SETTINGS = {
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
        "workfile_dependency": True,
        "use_published_workfile": True,
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
        "group": "none",
        "job_delay": "00:00:00:00"
    },
    "ProcessSubmittedCacheJobOnFarm": {
        "enabled": True,
        "deadline_department": "",
        "deadline_pool": "",
        "deadline_group": "",
        "deadline_chunk_size": 1,
        "deadline_priority": 50
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
