from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class CollectReviewPluginModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")


class ValidateSceneSettingsModel(BaseSettingsModel):
    """Validate naming of products and layers"""

    # _isGroup = True
    enabled: bool = Field(True, title="Enabled")
    optional: bool = Field(False, title="Optional")
    active: bool = Field(True, title="Active")
    skip_resolution_check: list[str] = Field(
        default_factory=list,
        title="Skip Resolution Check for Tasks",
    )
    skip_timelines_check: list[str] = Field(
        default_factory=list,
        title="Skip Timeline Check for Tasks",
    )


class ValidateContainersModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    optional: bool = Field(True, title="Optional")
    active: bool = Field(True, title="Active")


class AfterEffectsPublishPlugins(BaseSettingsModel):
    CollectReview: CollectReviewPluginModel = Field(
        default_factory=CollectReviewPluginModel,
        title="Collect Review",
    )
    ValidateSceneSettings: ValidateSceneSettingsModel = Field(
        default_factory=ValidateSceneSettingsModel,
        title="Validate Scene Settings",
    )
    ValidateContainers: ValidateContainersModel = Field(
        default_factory=ValidateContainersModel,
        title="Validate Containers",
    )


AE_PUBLISH_PLUGINS_DEFAULTS = {
    "CollectReview": {
        "enabled": True
    },
    "ValidateSceneSettings": {
        "enabled": True,
        "optional": True,
        "active": True,
        "skip_resolution_check": [
            ".*"
        ],
        "skip_timelines_check": [
            ".*"
        ]
    },
    "ValidateContainers": {
        "enabled": True,
        "optional": True,
        "active": True,
    }
}
