from ayon_server.settings import BaseSettingsModel
from pydantic import Field


class BasicCreatorModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    default_variants: list[str] = Field(
        default_factory=list,
        title="Default Variants"
    )


class EqualizerCreatorPlugins(BaseSettingsModel):
    CreateMatchMove: BasicCreatorModel = Field(
        default_factory=BasicCreatorModel,
        title="Create Match Move data"
    )


EQ_CREATORS_PLUGINS_DEFAULTS = {
    "CreateMatchMove": {
        "enabled": True,
        "default_variants": [
            "CameraTrack",
            "ObjectTrack",
            "PointTrack",
            "Stabilize",
            "SurveyTrack",
            "UserTrack",
        ]
    },
}
