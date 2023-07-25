from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class CollectReviewPluginModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")


class ValidateSceneSettingsPlugin(BaseSettingsModel):
    """Validate naming of products and layers"""  #
    _isGroup = True
    enabled: bool = True
    optional: bool = Field(False, title="Optional")
    active: bool = Field(True, title="Active")

    skip_resolution_check: list[str] = Field(
        default_factory=list,
        title="Skip Resolution Check for Tasks"
    )

    skip_timelines_check: list[str] = Field(
        default_factory=list,
        title="Skip Timeline Check for Tasks"
    )


class AfterEffectsPublishPlugins(BaseSettingsModel):
    CollectReview: CollectReviewPluginModel = Field(
        default_facotory=CollectReviewPluginModel,
        title="Collect Review"
    )
    ValidateSceneSettings: ValidateSceneSettingsPlugin = Field(
        title="Validate Scene Settings",
        default_factory=ValidateSceneSettingsPlugin,
    )
