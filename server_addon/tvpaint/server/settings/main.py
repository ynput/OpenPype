from pydantic import Field, validator
from ayon_server.settings import (
    BaseSettingsModel,
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


class PublishGUIFilterItemModel(BaseSettingsModel):
    _layout = "compact"
    name: str = Field(title="Name")
    value: bool = Field(True, title="Active")


class PublishGUIFiltersModel(BaseSettingsModel):
    _layout = "compact"
    name: str = Field(title="Name")
    value: list[PublishGUIFilterItemModel] = Field(default_factory=list)

    @validator("value")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class TvpaintSettings(BaseSettingsModel):
    imageio: TVPaintImageIOModel = Field(
        default_factory=TVPaintImageIOModel,
        title="Color Management (ImageIO)"
    )
    stop_timer_on_application_exit: bool = Field(
        title="Stop timer on application exit")
    create: CreatePluginsModel = Field(
        default_factory=CreatePluginsModel,
        title="Create plugins"
    )
    publish: PublishPluginsModel = Field(
        default_factory=PublishPluginsModel,
        title="Publish plugins")
    load: LoadPluginsModel = Field(
        default_factory=LoadPluginsModel,
        title="Load plugins")
    workfile_builder: WorkfileBuilderPlugin = Field(
        default_factory=WorkfileBuilderPlugin,
        title="Workfile Builder"
    )
    filters: list[PublishGUIFiltersModel] = Field(
        default_factory=list,
        title="Publish GUI Filters")

    @validator("filters")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


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
