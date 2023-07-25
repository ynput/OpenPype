from pydantic import Field

from ayon_server.settings import BaseSettingsModel, task_types_enum


class IncludeByTaskTypeModel(BaseSettingsModel):
    task_type: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    include_handles: bool = Field(True, title="Include handles")


class IncludeHandlesModel(BaseSettingsModel):
    """Maya dirmap settings."""
    # _layout = "expanded"
    include_handles_default: bool = Field(True, title="Include handles by default")
    per_task_type: list[IncludeByTaskTypeModel] = Field(
        default_factory=list,
        title="Include/exclude handles by task type"
    )


DEFAULT_INCLUDE_HANDLES = {
    "include_handles_default": False,
    "per_task_type": []
}
