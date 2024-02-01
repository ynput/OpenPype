from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum,
    MultiplatformPathModel,
)


class CustomTemplateModel(BaseSettingsModel):
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    path: MultiplatformPathModel = SettingsField(
        default_factory=MultiplatformPathModel,
        title="Gizmo Directory Path"
    )


class BuilderProfileItemModel(BaseSettingsModel):
    product_name_filters: list[str] = SettingsField(
        default_factory=list,
        title="Product name"
    )
    product_types: list[str] = SettingsField(
        default_factory=list,
        title="Product types"
    )
    repre_names: list[str] = SettingsField(
        default_factory=list,
        title="Representations"
    )
    loaders: list[str] = SettingsField(
        default_factory=list,
        title="Loader plugins"
    )


class BuilderProfileModel(BaseSettingsModel):
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    tasks: list[str] = SettingsField(
        default_factory=list,
        title="Task names"
    )
    current_context: list[BuilderProfileItemModel] = SettingsField(
        default_factory=list,
        title="Current context"
    )
    linked_assets: list[BuilderProfileItemModel] = SettingsField(
        default_factory=list,
        title="Linked assets/shots"
    )


class WorkfileBuilderModel(BaseSettingsModel):
    """[deprecated] use Template Workfile Build Settings instead.
    """
    create_first_version: bool = SettingsField(
        title="Create first workfile")
    custom_templates: list[CustomTemplateModel] = SettingsField(
        default_factory=list,
        title="Custom templates"
    )
    builder_on_start: bool = SettingsField(
        default=False,
        title="Run Builder at first workfile"
    )
    profiles: list[BuilderProfileModel] = SettingsField(
        default_factory=list,
        title="Builder profiles"
    )


DEFAULT_WORKFILE_BUILDER_SETTINGS = {
    "create_first_version": False,
    "custom_templates": [],
    "builder_on_start": False,
    "profiles": []
}
