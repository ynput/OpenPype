from ayon_server.settings import SettingsField, BaseSettingsModel


class LoadClipModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)

    product_types: list[str] = SettingsField(
        default_factory=list,
        title="Product types"
    )
    reel_group_name: str = SettingsField(
        "OpenPype_Reels",
        title="Reel group name"
    )
    reel_name: str = SettingsField(
        "Loaded",
        title="Reel name"
    )

    clip_name_template: str = SettingsField(
        "{folder[name]}_{product[name]}<_{output}>",
        title="Clip name template"
    )
    layer_rename_template: str = SettingsField(
        "", title="Layer name template"
    )
    layer_rename_patterns: list[str] = SettingsField(
        default_factory=list,
        title="Layer rename patters",
    )


class LoadClipBatchModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)
    product_types: list[str] = SettingsField(
        default_factory=list,
        title="Product types"
    )
    reel_name: str = SettingsField(
        "OP_LoadedReel",
        title="Reel name"
    )
    clip_name_template: str = SettingsField(
        "{batch}_{folder[name]}_{product[name]}<_{output}>",
        title="Clip name template"
    )
    layer_rename_template: str = SettingsField(
        "", title="Layer name template"
    )
    layer_rename_patterns: list[str] = SettingsField(
        default_factory=list,
        title="Layer rename patters",
    )


class LoaderPluginsModel(BaseSettingsModel):
    LoadClip: LoadClipModel = SettingsField(
        default_factory=LoadClipModel,
        title="Load Clip"
    )
    LoadClipBatch: LoadClipBatchModel = SettingsField(
        default_factory=LoadClipBatchModel,
        title="Load as clip to current batch"
    )


DEFAULT_LOADER_SETTINGS = {
    "LoadClip": {
        "enabled": True,
        "product_types": [
            "render2d",
            "source",
            "plate",
            "render",
            "review"
        ],
        "reel_group_name": "OpenPype_Reels",
        "reel_name": "Loaded",
        "clip_name_template": "{folder[name]}_{product[name]}<_{output}>",
        "layer_rename_template": "{folder[name]}_{product[name]}<_{output}>",
        "layer_rename_patterns": [
            "rgb",
            "rgba"
        ]
    },
    "LoadClipBatch": {
        "enabled": True,
        "product_types": [
            "render2d",
            "source",
            "plate",
            "render",
            "review"
        ],
        "reel_name": "OP_LoadedReel",
        "clip_name_template": "{batch}_{folder[name]}_{product[name]}<_{output}>",
        "layer_rename_template": "{folder[name]}_{product[name]}<_{output}>",
        "layer_rename_patterns": [
            "rgb",
            "rgba"
        ]
    }
}
