from pydantic import Field
from ayon_server.settings import (
    BaseSettingsModel,
    task_types_enum,
    MultiplatformPathModel,
)


class TemplatedWorkfileProfileModel(BaseSettingsModel):
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = Field(
        default_factory=list,
        title="Task names"
    )
    path: str = Field(
        title="Path to template"
    )
    keep_placeholder: bool = Field(
        False,
        title="Keep placeholders")
    create_first_version: bool = Field(
        True,
        title="Create first version"
    )


class TemplatedWorkfileBuildModel(BaseSettingsModel):
    profiles: list[TemplatedWorkfileProfileModel] = Field(
        default_factory=list
    )
