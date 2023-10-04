from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class FiltersSubmodel(BaseSettingsModel):
    _layout = "compact"
    name: str = Field(title="Name")
    value: str = Field(
        "",
        title="Textarea",
        widget="textarea",
    )


class PublishFiltersModel(BaseSettingsModel):
    env_search_replace_values: list[FiltersSubmodel] = Field(
        default_factory=list
    )
