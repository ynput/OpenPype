from pydantic import validator
from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names,
    normalize_name,
)


class CollectInstanceVersionModel(BaseSettingsModel):
    enabled: bool = SettingsField(
        True,
        title="Enabled"
    )


class CollectClipEffectsDefModel(BaseSettingsModel):
    _layout = "expanded"
    name: str = SettingsField("", title="Name")
    effect_classes: list[str] = SettingsField(
        default_factory=list, title="Effect Classes"
    )

    @validator("name")
    def validate_name(cls, value):
        """Ensure name does not contain weird characters"""
        return normalize_name(value)


class CollectClipEffectsModel(BaseSettingsModel):
    effect_categories: list[CollectClipEffectsDefModel] = SettingsField(
        default_factory=list, title="Effect Categories"
    )

    @validator("effect_categories")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class ExtractReviewCutUpVideoModel(BaseSettingsModel):
    enabled: bool = SettingsField(
        True,
        title="Enabled"
    )
    tags_addition: list[str] = SettingsField(
        default_factory=list,
        title="Additional tags"
    )


class PublishPuginsModel(BaseSettingsModel):
    CollectInstanceVersion: CollectInstanceVersionModel = SettingsField(
        default_factory=CollectInstanceVersionModel,
        title="Collect Instance Version"
    )
    CollectClipEffects: CollectClipEffectsModel = SettingsField(
        default_factory=CollectClipEffectsModel,
        title="Collect Clip Effects"
    )
    """# TODO: enhance settings with host api:
    Rename class name and plugin name
    to match title (it makes more sense)
    """
    ExtractReviewCutUpVideo: ExtractReviewCutUpVideoModel = SettingsField(
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
    },
    "CollectClipEffectsModel": {
        "effect_categories": []
    }
}
