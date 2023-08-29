from ayon_server.settings import Field, BaseSettingsModel


class LoadClipModel(BaseSettingsModel):
    enabled: bool = Field(True)

    product_types: list[str] = Field(
        default_factory=list,
        title="Product types"
    )
    reel_group_name: str = Field(
        "OpenPype_Reels",
        title="Reel group name"
    )
    reel_name: str = Field(
        "Loaded",
        title="Reel name"
    )

    clip_name_template: str = Field(
        "{folder[name]}_{product[name]}<_{output}>",
        title="Clip name template"
    )
    layer_rename_template: str = Field("", title="Layer name template")
    layer_rename_patterns: list[str] = Field(
        default_factory=list,
        title="Layer rename patters",
    )


class LoadClipBatchModel(BaseSettingsModel):
    enabled: bool = Field(True)
    product_types: list[str] = Field(
        default_factory=list,
        title="Product types"
    )
    reel_name: str = Field(
        "OP_LoadedReel",
        title="Reel name"
    )
    clip_name_template: str = Field(
        "{batch}_{folder[name]}_{product[name]}<_{output}>",
        title="Clip name template"
    )
    layer_rename_template: str = Field("", title="Layer name template")
    layer_rename_patterns: list[str] = Field(
        default_factory=list,
        title="Layer rename patters",
    )


class LoaderPluginsModel(BaseSettingsModel):
    LoadClip: LoadClipModel = Field(
        default_factory=LoadClipModel,
        title="Load Clip"
    )
    LoadClipBatch: LoadClipBatchModel = Field(
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
