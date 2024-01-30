from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum,
)


class WorkfileBuildProfilesModel(BaseSettingsModel):
    _layout = "expanded"
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list, title="Task names"
    )
    path: str = SettingsField("", title="Path to template")


class TemplatedProfilesModel(BaseSettingsModel):
    profiles: list[WorkfileBuildProfilesModel] = SettingsField(
        default_factory=list,
        title="Profiles"
    )


DEFAULT_TEMPLATED_WORKFILE_SETTINGS = {
    "profiles": []
}
