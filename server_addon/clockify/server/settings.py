from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class ClockifySettings(BaseSettingsModel):
    workspace_name: str = Field(
        "",
        title="Workspace name"
    )
