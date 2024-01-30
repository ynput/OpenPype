from pydantic import validator
from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names,
)


class PublishGUIFilterItemModel(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(title="Name")
    value: bool = SettingsField(True, title="Active")


class PublishGUIFiltersModel(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(title="Name")
    value: list[PublishGUIFilterItemModel] = SettingsField(
        default_factory=list
    )

    @validator("value")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value
