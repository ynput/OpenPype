from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names,
)

from .imageio import TVPaintImageIOModel
from .workfile_builder import WorkfileBuilderPlugin
from .create_plugins import CreatePluginsModel, DEFAULT_CREATE_SETTINGS
from .publish_plugins import (
    PublishPluginsModel,
    LoadPluginsModel,
    DEFAULT_PUBLISH_SETTINGS,
)


class TvpaintSettings(BaseSettingsModel):
    imageio: TVPaintImageIOModel = SettingsField(
        default_factory=TVPaintImageIOModel,
        title="Color Management (ImageIO)"
    )
    stop_timer_on_application_exit: bool = SettingsField(
        title="Stop timer on application exit")
    create: CreatePluginsModel = SettingsField(
        default_factory=CreatePluginsModel,
        title="Create plugins"
    )
    publish: PublishPluginsModel = SettingsField(
        default_factory=PublishPluginsModel,
        title="Publish plugins")
    load: LoadPluginsModel = SettingsField(
        default_factory=LoadPluginsModel,
        title="Load plugins")
    workfile_builder: WorkfileBuilderPlugin = SettingsField(
        default_factory=WorkfileBuilderPlugin,
        title="Workfile Builder"
    )


DEFAULT_VALUES = {
    "stop_timer_on_application_exit": False,
    "create": DEFAULT_CREATE_SETTINGS,
    "publish": DEFAULT_PUBLISH_SETTINGS,
    "load": {
        "LoadImage": {
            "defaults": {
                "stretch": True,
                "timestretch": True,
                "preload": True
            }
        },
        "ImportImage": {
            "defaults": {
                "stretch": True,
                "timestretch": True,
                "preload": True
            }
        }
    },
    "workfile_builder": {
        "create_first_version": False,
        "custom_templates": []
    },
    "filters": []
}
