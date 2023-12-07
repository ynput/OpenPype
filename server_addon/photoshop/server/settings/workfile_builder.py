from pydantic import Field

from ayon_server.settings import BaseSettingsModel, MultiplatformPathModel


class CustomBuilderTemplate(BaseSettingsModel):
    _layout = "expanded"
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
    )

    path: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel,
        title="Template path"
    )


class WorkfileBuilderPlugin(BaseSettingsModel):
    _title = "Workfile Builder"
    create_first_version: bool = Field(
        False,
        title="Create first workfile"
    )

    custom_templates: list[CustomBuilderTemplate] = Field(
        default_factory=CustomBuilderTemplate,
        title="Template profiles"
    )
