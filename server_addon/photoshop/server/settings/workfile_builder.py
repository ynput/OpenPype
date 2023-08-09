from pydantic import Field
from pathlib import Path

from ayon_server.settings import BaseSettingsModel


class PathsTemplate(BaseSettingsModel):
    windows: Path = Field(
        '',
        title="Windows"
    )
    darwin: Path = Field(
        '',
        title="MacOS"
    )
    linux: Path = Field(
        '',
        title="Linux"
    )


class CustomBuilderTemplate(BaseSettingsModel):
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
    )
    template_path: PathsTemplate = Field(
        default_factory=PathsTemplate
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
