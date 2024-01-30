from ayon_server.settings import BaseSettingsModel, SettingsField


class FiltersSubmodel(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(title="Name")
    value: str = SettingsField(
        "",
        title="Textarea",
        widget="textarea",
    )


class PublishFiltersModel(BaseSettingsModel):
    env_search_replace_values: list[FiltersSubmodel] = SettingsField(
        default_factory=list
    )
