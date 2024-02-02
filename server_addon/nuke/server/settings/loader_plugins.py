from ayon_server.settings import BaseSettingsModel, SettingsField


class LoadImageModel(BaseSettingsModel):
    enabled: bool = SettingsField(
        title="Enabled"
    )
    representations_include: list[str] = SettingsField(
        default_factory=list,
        title="Include representations"
    )

    node_name_template: str = SettingsField(
        title="Read node name template"
    )


class LoadClipOptionsModel(BaseSettingsModel):
    start_at_workfile: bool = SettingsField(
        title="Start at workfile's start frame"
    )
    add_retime: bool = SettingsField(
        title="Add retime"
    )


class LoadClipModel(BaseSettingsModel):
    enabled: bool = SettingsField(
        title="Enabled"
    )
    representations_include: list[str] = SettingsField(
        default_factory=list,
        title="Include representations"
    )

    node_name_template: str = SettingsField(
        title="Read node name template"
    )
    options_defaults: LoadClipOptionsModel = SettingsField(
        default_factory=LoadClipOptionsModel,
        title="Loader option defaults"
    )


class LoaderPuginsModel(BaseSettingsModel):
    LoadImage: LoadImageModel = SettingsField(
        default_factory=LoadImageModel,
        title="Load Image"
    )
    LoadClip: LoadClipModel = SettingsField(
        default_factory=LoadClipModel,
        title="Load Clip"
    )


DEFAULT_LOADER_PLUGINS_SETTINGS = {
    "LoadImage": {
        "enabled": True,
        "representations_include": [],
        "node_name_template": "{class_name}_{ext}"
    },
    "LoadClip": {
        "enabled": True,
        "representations_include": [],
        "node_name_template": "{class_name}_{ext}",
        "options_defaults": {
            "start_at_workfile": True,
            "add_retime": True
        }
    }
}
