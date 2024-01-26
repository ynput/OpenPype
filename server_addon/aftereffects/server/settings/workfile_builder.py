from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    MultiplatformPathModel,
)


class CustomBuilderTemplate(BaseSettingsModel):
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
    )
    template_path: MultiplatformPathModel = SettingsField(
        default_factory=MultiplatformPathModel
    )


class WorkfileBuilderPlugin(BaseSettingsModel):
    _title = "Workfile Builder"
    create_first_version: bool = SettingsField(
        False,
        title="Create first workfile"
    )

    custom_templates: list[CustomBuilderTemplate] = SettingsField(
        default_factory=list
    )
