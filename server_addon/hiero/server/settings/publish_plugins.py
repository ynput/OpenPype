from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class CollectInstanceVersionModel(BaseSettingsModel):
    enabled: bool = Field(
        True,
        title="Enabled"
    )


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
