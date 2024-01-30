from pydantic import validator

from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names,
)

from .publish_plugins import (
    PublishPluginsModel,
    DEFAULT_DEADLINE_PLUGINS_SETTINGS
)


class ServerListSubmodel(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(title="Name")
    value: str = SettingsField(title="Value")


async def defined_deadline_ws_name_enum_resolver(
    addon: "BaseServerAddon",
    settings_variant: str = "production",
    project_name: str | None = None,
) -> list[str]:
    """Provides list of names of configured Deadline webservice urls."""
    if addon is None:
        return []

    settings = await addon.get_studio_settings(variant=settings_variant)

    ws_urls = []
    for deadline_url_item in settings.deadline_urls:
        ws_urls.append(deadline_url_item.name)

    return ws_urls


class DeadlineSettings(BaseSettingsModel):
    deadline_urls: list[ServerListSubmodel] = SettingsField(
        default_factory=list,
        title="System Deadline Webservice URLs",
        scope=["studio"],
    )
    deadline_server: str = SettingsField(
        title="Project deadline server",
        section="---",
        scope=["project"],
        enum_resolver=defined_deadline_ws_name_enum_resolver
    )
    publish: PublishPluginsModel = SettingsField(
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
    "deadline_server": "default",
    "publish": DEFAULT_DEADLINE_PLUGINS_SETTINGS
}
