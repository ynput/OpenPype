from pydantic import Field, validator
from ayon_server.settings import (
    BaseSettingsModel, ensure_unique_names, normalize_name
)


class CollectInstanceVersionModel(BaseSettingsModel):
    enabled: bool = Field(
        True,
        title="Enabled"
    )


class CollectClipEffectsDefModel(BaseSettingsModel):
    _layout = "expanded"
    name: str = Field("", title="Name")
    effect_classes: list[str] = Field(
        default_factory=list, title="Effect Classes"
    )

    @validator("name")
    def validate_name(cls, value):
        """Ensure name does not contain weird characters"""
        return normalize_name(value)


class CollectClipEffectsModel(BaseSettingsModel):
    effect_categories: list[CollectClipEffectsDefModel] = Field(
        default_factory=list, title="Effect Categories"
    )

    @validator("effect_categories")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class ExtractReviewCutUpVideoModel(BaseSettingsModel):
    enabled: bool = Field(
        True,
        title="Enabled"
    )
    tags_addition: list[str] = Field(
        default_factory=list,
        title="Additional tags"
    )


class PublishPuginsModel(BaseSettingsModel):
    CollectInstanceVersion: CollectInstanceVersionModel = Field(
        default_factory=CollectInstanceVersionModel,
        title="Collect Instance Version"
    )
    CollectClipEffects: CollectClipEffectsModel = Field(
        default_factory=CollectClipEffectsModel,
        title="Collect Clip Effects"
    )
    """# TODO: enhance settings with host api:
    Rename class name and plugin name
    to match title (it makes more sense)
    """
    ExtractReviewCutUpVideo: ExtractReviewCutUpVideoModel = Field(
        default_factory=ExtractReviewCutUpVideoModel,
        title="Exctract Review Trim"
    )


DEFAULT_PUBLISH_PLUGIN_SETTINGS = {
    "CollectInstanceVersion": {
        "enabled": False,
    },
    "ExtractReviewCutUpVideo": {
        "enabled": True,
        "tags_addition": [
            "review"
        ]
    }
}
