from pydantic import Field, validator
from ayon_server.settings import BaseSettingsModel, ensure_unique_names


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
