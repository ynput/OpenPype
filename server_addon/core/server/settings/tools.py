from pydantic import validator
from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    normalize_name,
    ensure_unique_names,
    task_types_enum,
)


class ProductTypeSmartSelectModel(BaseSettingsModel):
    _layout = "expanded"
    name: str = SettingsField("", title="Product type")
    task_names: list[str] = SettingsField(
        default_factory=list, title="Task names"
    )

    @validator("name")
    def normalize_value(cls, value):
        return normalize_name(value)


class ProductNameProfile(BaseSettingsModel):
    _layout = "expanded"
    product_types: list[str] = SettingsField(
        default_factory=list, title="Product types"
    )
    hosts: list[str] = SettingsField(default_factory=list, title="Hosts")
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    tasks: list[str] = SettingsField(default_factory=list, title="Task names")
    template: str = SettingsField("", title="Template")


class CreatorToolModel(BaseSettingsModel):
    # TODO this was dynamic dictionary '{name: task_names}'
    product_types_smart_select: list[ProductTypeSmartSelectModel] = (
        SettingsField(
            default_factory=list,
            title="Create Smart Select"
        )
    )
    product_name_profiles: list[ProductNameProfile] = SettingsField(
        default_factory=list,
        title="Product name profiles"
    )

    @validator("product_types_smart_select")
    def validate_unique_name(cls, value):
        ensure_unique_names(value)
        return value


class WorkfileTemplateProfile(BaseSettingsModel):
    _layout = "expanded"
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    # TODO this should use hosts enum
    hosts: list[str] = SettingsField(default_factory=list, title="Hosts")
    # TODO this was using project anatomy template name
    workfile_template: str = SettingsField("", title="Workfile template")


class LastWorkfileOnStartupProfile(BaseSettingsModel):
    _layout = "expanded"
    # TODO this should use hosts enum
    hosts: list[str] = SettingsField(default_factory=list, title="Hosts")
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    tasks: list[str] = SettingsField(default_factory=list, title="Task names")
    enabled: bool = SettingsField(True, title="Enabled")
    use_last_published_workfile: bool = SettingsField(
        True, title="Use last published workfile"
    )


class WorkfilesToolOnStartupProfile(BaseSettingsModel):
    _layout = "expanded"
    # TODO this should use hosts enum
    hosts: list[str] = SettingsField(default_factory=list, title="Hosts")
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    tasks: list[str] = SettingsField(default_factory=list, title="Task names")
    enabled: bool = SettingsField(True, title="Enabled")


class ExtraWorkFoldersProfile(BaseSettingsModel):
    _layout = "expanded"
    # TODO this should use hosts enum
    hosts: list[str] = SettingsField(default_factory=list, title="Hosts")
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list, title="Task names"
    )
    folders: list[str] = SettingsField(default_factory=list, title="Folders")


class WorkfilesLockProfile(BaseSettingsModel):
    _layout = "expanded"
    # TODO this should use hosts enum
    host_names: list[str] = SettingsField(default_factory=list, title="Hosts")
    enabled: bool = SettingsField(True, title="Enabled")


class WorkfilesToolModel(BaseSettingsModel):
    workfile_template_profiles: list[WorkfileTemplateProfile] = SettingsField(
        default_factory=list,
        title="Workfile template profiles"
    )
    last_workfile_on_startup: list[LastWorkfileOnStartupProfile] = (
        SettingsField(
            default_factory=list,
            title="Open last workfile on launch"
        )
    )
    open_workfile_tool_on_startup: list[WorkfilesToolOnStartupProfile] = (
        SettingsField(
            default_factory=list,
            title="Open workfile tool on launch"
        )
    )
    extra_folders: list[ExtraWorkFoldersProfile] = SettingsField(
        default_factory=list,
        title="Extra work folders"
    )
    workfile_lock_profiles: list[WorkfilesLockProfile] = SettingsField(
        default_factory=list,
        title="Workfile lock profiles"
    )


def _product_types_enum():
    return [
        "action",
        "animation",
        "assembly",
        "audio",
        "backgroundComp",
        "backgroundLayout",
        "camera",
        "editorial",
        "gizmo",
        "image",
        "layout",
        "look",
        "matchmove",
        "mayaScene",
        "model",
        "nukenodes",
        "plate",
        "pointcache",
        "prerender",
        "redshiftproxy",
        "reference",
        "render",
        "review",
        "rig",
        "setdress",
        "take",
        "usdShade",
        "vdbcache",
        "vrayproxy",
        "workfile",
        "xgen",
        "yetiRig",
        "yeticache"
    ]


class LoaderProductTypeFilterProfile(BaseSettingsModel):
    _layout = "expanded"
    # TODO this should use hosts enum
    hosts: list[str] = SettingsField(default_factory=list, title="Hosts")
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    is_include: bool = SettingsField(True, title="Exclude / Include")
    filter_product_types: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=_product_types_enum
    )


class LoaderToolModel(BaseSettingsModel):
    product_type_filter_profiles: list[LoaderProductTypeFilterProfile] = (
        SettingsField(default_factory=list, title="Product type filtering")
    )


class PublishTemplateNameProfile(BaseSettingsModel):
    _layout = "expanded"
    product_types: list[str] = SettingsField(
        default_factory=list,
        title="Product types"
    )
    # TODO this should use hosts enum
    hosts: list[str] = SettingsField(default_factory=list, title="Hosts")
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list, title="Task names"
    )
    template_name: str = SettingsField("", title="Template name")


class CustomStagingDirProfileModel(BaseSettingsModel):
    active: bool = SettingsField(True, title="Is active")
    hosts: list[str] = SettingsField(default_factory=list, title="Host names")
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list, title="Task names"
    )
    product_types: list[str] = SettingsField(
        default_factory=list, title="Product types"
    )
    product_names: list[str] = SettingsField(
        default_factory=list, title="Product names"
    )
    custom_staging_dir_persistent: bool = SettingsField(
        False, title="Custom Staging Folder Persistent"
    )
    template_name: str = SettingsField("", title="Template Name")


class PublishToolModel(BaseSettingsModel):
    template_name_profiles: list[PublishTemplateNameProfile] = SettingsField(
        default_factory=list,
        title="Template name profiles"
    )
    hero_template_name_profiles: list[PublishTemplateNameProfile] = (
        SettingsField(
            default_factory=list,
            title="Hero template name profiles"
        )
    )
    custom_staging_dir_profiles: list[CustomStagingDirProfileModel] = (
        SettingsField(
            default_factory=list,
            title="Custom Staging Dir Profiles"
        )
    )


class GlobalToolsModel(BaseSettingsModel):
    creator: CreatorToolModel = SettingsField(
        default_factory=CreatorToolModel,
        title="Creator"
    )
    Workfiles: WorkfilesToolModel = SettingsField(
        default_factory=WorkfilesToolModel,
        title="Workfiles"
    )
    loader: LoaderToolModel = SettingsField(
        default_factory=LoaderToolModel,
        title="Loader"
    )
    publish: PublishToolModel = SettingsField(
        default_factory=PublishToolModel,
        title="Publish"
    )


DEFAULT_TOOLS_VALUES = {
    "creator": {
        "product_types_smart_select": [
            {
                "name": "Render",
                "task_names": [
                    "light",
                    "render"
                ]
            },
            {
                "name": "Model",
                "task_names": [
                    "model"
                ]
            },
            {
                "name": "Layout",
                "task_names": [
                    "layout"
                ]
            },
            {
                "name": "Look",
                "task_names": [
                    "look"
                ]
            },
            {
                "name": "Rig",
                "task_names": [
                    "rigging",
                    "rig"
                ]
            }
        ],
        "product_name_profiles": [
            {
                "product_types": [],
                "hosts": [],
                "task_types": [],
                "tasks": [],
                "template": "{product[type]}{variant}"
            },
            {
                "product_types": [
                    "workfile"
                ],
                "hosts": [],
                "task_types": [],
                "tasks": [],
                "template": "{product[type]}{Task[name]}"
            },
            {
                "product_types": [
                    "render"
                ],
                "hosts": [],
                "task_types": [],
                "tasks": [],
                "template": "{product[type]}{Task[name]}{Variant}"
            },
            {
                "product_types": [
                    "renderLayer",
                    "renderPass"
                ],
                "hosts": [
                    "tvpaint"
                ],
                "task_types": [],
                "tasks": [],
                "template": "{product[type]}{Task[name]}_{Renderlayer}_{Renderpass}"
            },
            {
                "product_types": [
                    "review",
                    "workfile"
                ],
                "hosts": [
                    "aftereffects",
                    "tvpaint"
                ],
                "task_types": [],
                "tasks": [],
                "template": "{product[type]}{Task[name]}"
            },
            {
                "product_types": ["render"],
                "hosts": [
                    "aftereffects"
                ],
                "task_types": [],
                "tasks": [],
                "template": "{product[type]}{Task[name]}{Composition}{Variant}"
            },
            {
                "product_types": [
                    "staticMesh"
                ],
                "hosts": [
                    "maya"
                ],
                "task_types": [],
                "tasks": [],
                "template": "S_{folder[name]}{variant}"
            },
            {
                "product_types": [
                    "skeletalMesh"
                ],
                "hosts": [
                    "maya"
                ],
                "task_types": [],
                "tasks": [],
                "template": "SK_{folder[name]}{variant}"
            }
        ]
    },
    "Workfiles": {
        "workfile_template_profiles": [
            {
                "task_types": [],
                "hosts": [],
                "workfile_template": "work"
            },
            {
                "task_types": [],
                "hosts": [
                    "unreal"
                ],
                "workfile_template": "work_unreal"
            }
        ],
        "last_workfile_on_startup": [
            {
                "hosts": [],
                "task_types": [],
                "tasks": [],
                "enabled": True,
                "use_last_published_workfile": False
            }
        ],
        "open_workfile_tool_on_startup": [
            {
                "hosts": [],
                "task_types": [],
                "tasks": [],
                "enabled": False
            }
        ],
        "extra_folders": [],
        "workfile_lock_profiles": []
    },
    "loader": {
        "product_type_filter_profiles": [
            {
                "hosts": [],
                "task_types": [],
                "is_include": True,
                "filter_product_types": []
            }
        ]
    },
    "publish": {
        "template_name_profiles": [
            {
                "product_types": [],
                "hosts": [],
                "task_types": [],
                "task_names": [],
                "template_name": "publish"
            },
            {
                "product_types": [
                    "review",
                    "render",
                    "prerender"
                ],
                "hosts": [],
                "task_types": [],
                "task_names": [],
                "template_name": "publish_render"
            },
            {
                "product_types": [
                    "simpleUnrealTexture"
                ],
                "hosts": [
                    "standalonepublisher"
                ],
                "task_types": [],
                "task_names": [],
                "template_name": "publish_simpleUnrealTexture"
            },
            {
                "product_types": [
                    "staticMesh",
                    "skeletalMesh"
                ],
                "hosts": [
                    "maya"
                ],
                "task_types": [],
                "task_names": [],
                "template_name": "publish_maya2unreal"
            },
            {
                "product_types": [
                    "online"
                ],
                "hosts": [
                    "traypublisher"
                ],
                "task_types": [],
                "task_names": [],
                "template_name": "publish_online"
            },
            {
                "product_types": [
                    "tycache"
                ],
                "hosts": [
                    "max"
                ],
                "task_types": [],
                "task_names": [],
                "template_name": "publish_tycache"
            }
        ],
        "hero_template_name_profiles": [
            {
                "product_types": [
                    "simpleUnrealTexture"
                ],
                "hosts": [
                    "standalonepublisher"
                ],
                "task_types": [],
                "task_names": [],
                "template_name": "hero_simpleUnrealTextureHero"
            }
        ]
    }
}
