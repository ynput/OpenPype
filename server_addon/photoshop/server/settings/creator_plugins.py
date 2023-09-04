from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class CreateImagePluginModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    active_on_create: bool = Field(True, title="Active by default")
    mark_for_review: bool = Field(False, title="Review by default")
    default_variants: list[str] = Field(
        default_factory=list,
        title="Default Variants"
    )


class AutoImageCreatorPluginModel(BaseSettingsModel):
    enabled: bool = Field(False, title="Enabled")
    active_on_create: bool = Field(True, title="Active by default")
    mark_for_review: bool = Field(False, title="Review by default")
    default_variant: str = Field("", title="Default Variants")


class CreateReviewPlugin(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    active_on_create: bool = Field(True, title="Active by default")
    default_variant: str = Field("", title="Default Variants")


class CreateWorkfilelugin(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    active_on_create: bool = Field(True, title="Active by default")
    default_variant: str = Field("", title="Default Variants")


class PhotoshopCreatorPlugins(BaseSettingsModel):
    ImageCreator: CreateImagePluginModel = Field(
        title="Create Image",
        default_factory=CreateImagePluginModel,
    )
    AutoImageCreator: AutoImageCreatorPluginModel = Field(
        title="Create Flatten Image",
        default_factory=AutoImageCreatorPluginModel,
    )
    ReviewCreator: CreateReviewPlugin = Field(
        title="Create Review",
        default_factory=CreateReviewPlugin,
    )
    WorkfileCreator: CreateWorkfilelugin = Field(
        title="Create Workfile",
        default_factory=CreateWorkfilelugin,
    )


DEFAULT_CREATE_SETTINGS = {
    "ImageCreator": {
        "enabled": True,
        "active_on_create": True,
        "mark_for_review": False,
        "default_variants": [
            "Main"
        ]
    },
    "AutoImageCreator": {
        "enabled": False,
        "active_on_create": True,
        "mark_for_review": False,
        "default_variant": ""
    },
    "ReviewCreator": {
        "enabled": True,
        "active_on_create": True,
        "default_variant": ""
    },
    "WorkfileCreator": {
        "enabled": True,
        "active_on_create": True,
        "default_variant": "Main"
    }
}
