from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class LoadImageModel(BaseSettingsModel):
    enabled: bool = Field(
        title="Enabled"
    )
    """# TODO: v3 api used `_representation`
    New api is hiding it so it had to be renamed
    to `representations_include`
    """
    representations_include: list[str] = Field(
        default_factory=list,
        title="Include representations"
    )

    node_name_template: str = Field(
        title="Read node name template"
    )


class LoadClipOptionsModel(BaseSettingsModel):
    start_at_workfile: bool = Field(
        title="Start at workfile's start frame"
    )
    add_retime: bool = Field(
        title="Add retime"
    )


class LoadClipModel(BaseSettingsModel):
    enabled: bool = Field(
        title="Enabled"
    )
    """# TODO: v3 api used `_representation`
    New api is hiding it so it had to be renamed
    to `representations_include`
    """
    representations_include: list[str] = Field(
        default_factory=list,
        title="Include representations"
    )

    node_name_template: str = Field(
        title="Read node name template"
    )
    options_defaults: LoadClipOptionsModel = Field(
        default_factory=LoadClipOptionsModel,
        title="Loader option defaults"
    )


class LoaderPuginsModel(BaseSettingsModel):
    LoadImage: LoadImageModel = Field(
        default_factory=LoadImageModel,
        title="Load Image"
    )
    LoadClip: LoadClipModel = Field(
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
