from pydantic import Field
from ayon_server.settings import BaseSettingsModel, MultiplatformPathModel


class ServerListSubmodel(BaseSettingsModel):
    _layout = "compact"
    name: str = Field("", title="Name")
    value: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel
    )


class CollectSequencesFromJobModel(BaseSettingsModel):
    review: bool = Field(True, title="Generate reviews from sequences")


class PublishPluginsModel(BaseSettingsModel):
    CollectSequencesFromJob: CollectSequencesFromJobModel = Field(
        default_factory=CollectSequencesFromJobModel,
        title="Collect Sequences from the Job"
    )


class RoyalRenderSettings(BaseSettingsModel):
    enabled: bool = True
    rr_paths: list[ServerListSubmodel] = Field(
        default_factory=list,
        title="Royal Render Root Paths",
    )
    publish: PublishPluginsModel = Field(
        default_factory=PublishPluginsModel,
        title="Publish plugins"
    )


DEFAULT_VALUES = {
    "enabled": False,
    "rr_paths": [
        {
            "name": "default",
            "value": {
                "windows": "",
                "darwin": "",
                "linux": ""
            }
        }
    ],
    "publish": {
        "CollectSequencesFromJob": {
            "review": True
        }
    }
}
