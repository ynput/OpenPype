from ayon_server.settings import BaseSettingsModel, SettingsField


class CollectReviewPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")


class ValidateSceneSettingsModel(BaseSettingsModel):
    """Validate naming of products and layers"""

    # _isGroup = True
    enabled: bool = SettingsField(True, title="Enabled")
    optional: bool = SettingsField(False, title="Optional")
    active: bool = SettingsField(True, title="Active")
    skip_resolution_check: list[str] = SettingsField(
        default_factory=list,
        title="Skip Resolution Check for Tasks",
    )
    skip_timelines_check: list[str] = SettingsField(
        default_factory=list,
        title="Skip Timeline Check for Tasks",
    )


class ValidateContainersModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    optional: bool = SettingsField(True, title="Optional")
    active: bool = SettingsField(True, title="Active")


class AfterEffectsPublishPlugins(BaseSettingsModel):
    CollectReview: CollectReviewPluginModel = SettingsField(
        default_factory=CollectReviewPluginModel,
        title="Collect Review",
    )
    ValidateSceneSettings: ValidateSceneSettingsModel = SettingsField(
        default_factory=ValidateSceneSettingsModel,
        title="Validate Scene Settings",
    )
    ValidateContainers: ValidateContainersModel = SettingsField(
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
