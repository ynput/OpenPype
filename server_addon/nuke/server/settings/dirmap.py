from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class DirmapPathsSubmodel(BaseSettingsModel):
    _layout = "compact"
    source_path: list[str] = Field(
        default_factory=list,
        title="Source Paths"
    )
    destination_path: list[str] = Field(
        default_factory=list,
        title="Destination Paths"
    )


class DirmapSettings(BaseSettingsModel):
    """Nuke color management project settings."""
    _isGroup: bool = True

    enabled: bool = Field(title="enabled")
    paths: DirmapPathsSubmodel = Field(
        default_factory=DirmapPathsSubmodel,
        title="Dirmap Paths"
    )


"""# TODO:
nuke is having originally implemented
following data inputs:

"nuke-dirmap": {
    "enabled": false,
    "paths": {
        "source-path": [],
        "destination-path": []
    }
}
"""

DEFAULT_DIRMAP_SETTINGS = {
    "enabled": False,
    "paths": {
        "source_path": [],
        "destination_path": []
    }
}
