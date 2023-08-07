from pydantic import Field

from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathModel,
    task_types_enum,
)


class CustomBuilderTemplate(BaseSettingsModel):
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    template_path: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel
    )


class WorkfileBuilderPlugin(BaseSettingsModel):
    _title = "Workfile Builder"
    create_first_version: bool = Field(
        False,
        title="Create first workfile"
    )

    custom_templates: list[CustomBuilderTemplate] = Field(
        default_factory=CustomBuilderTemplate
    )
