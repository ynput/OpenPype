from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    MultiplatformPathModel,
)


class CustomPath(MultiplatformPathModel):
    _layout = "expanded"


class ServerListSubmodel(BaseSettingsModel):
    _layout = "expanded"
    name: str = SettingsField("", title="Name")
    value: CustomPath = SettingsField(
        default_factory=CustomPath
    )


class CollectSequencesFromJobModel(BaseSettingsModel):
    review: bool = SettingsField(
        True, title="Generate reviews from sequences"
    )


class PublishPluginsModel(BaseSettingsModel):
    CollectSequencesFromJob: CollectSequencesFromJobModel = SettingsField(
        default_factory=CollectSequencesFromJobModel,
        title="Collect Sequences from the Job"
    )


class RoyalRenderSettings(BaseSettingsModel):
    enabled: bool = True
    # WARNING/TODO this needs change
    # - both system and project settings contained 'rr_path'
    #   where project settings did choose one of rr_path from system settings
    #   that is not possible in AYON
    rr_paths: list[ServerListSubmodel] = SettingsField(
        default_factory=list,
        title="Royal Render Root Paths",
        scope=["studio"],
    )
    # This was 'rr_paths' in project settings and should be enum of
    #   'rr_paths' from system settings, but that's not possible in AYON
    selected_rr_paths: list[str] = SettingsField(
        default_factory=list,
        title="Selected Royal Render Paths",
        section="---",
    )
    publish: PublishPluginsModel = SettingsField(
        default_factory=PublishPluginsModel,
        title="Publish plugins",
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
    "selected_rr_paths": ["default"],
    "publish": {
        "CollectSequencesFromJob": {
            "review": True
        }
    }
}
