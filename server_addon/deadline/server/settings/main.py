from pydantic import Field, validator

from ayon_server.settings import BaseSettingsModel, ensure_unique_names

from .publish_plugins import (
    PublishPluginsModel,
    DEFAULT_DEADLINE_PLUGINS_SETTINGS
)


class ServerListSubmodel(BaseSettingsModel):
    _layout = "compact"
    name: str = Field(title="Name")
    value: str = Field(title="Value")


class DeadlineSettings(BaseSettingsModel):
    deadline_urls: list[ServerListSubmodel] = Field(
        default_factory=list,
        title="System Deadline Webservice URLs",
    )

    deadline_servers: list[str] = Field(
        title="Project deadline servers",
        section="---")

    publish: PublishPluginsModel = Field(
        default_factory=PublishPluginsModel,
        title="Publish Plugins",
    )

    @validator("deadline_urls")
    def validate_unique_names(cls, value):
        ensure_unique_names(value)
        return value


DEFAULT_VALUES = {
    "deadline_urls": [
        {
            "name": "default",
            "value": "http://127.0.0.1:8082"
        }
    ],
    # TODO: this needs to be dynamic from "deadline_urls"
    "deadline_servers": [],
    "publish": DEFAULT_DEADLINE_PLUGINS_SETTINGS
}
