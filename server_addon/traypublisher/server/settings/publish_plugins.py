from ayon_server.settings import BaseSettingsModel, SettingsField


class ValidatePluginModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = True
    optional: bool = SettingsField(True, title="Optional")
    active: bool = SettingsField(True, title="Active")


class ValidateFrameRangeModel(ValidatePluginModel):
    """Allows to publish multiple video files in one go. <br />Name of matching
     asset is parsed from file names ('asset.mov', 'asset_v001.mov',
     'my_asset_to_publish.mov')"""


class TrayPublisherPublishPlugins(BaseSettingsModel):
    CollectFrameDataFromAssetEntity: ValidatePluginModel = SettingsField(
        default_factory=ValidatePluginModel,
        title="Collect Frame Data From Folder Entity",
    )
    ValidateFrameRange: ValidateFrameRangeModel = SettingsField(
        title="Validate Frame Range",
        default_factory=ValidateFrameRangeModel,
    )
    ValidateExistingVersion: ValidatePluginModel = SettingsField(
        title="Validate Existing Version",
        default_factory=ValidatePluginModel,
    )


DEFAULT_PUBLISH_PLUGINS = {
    "CollectFrameDataFromAssetEntity": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateFrameRange": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateExistingVersion": {
        "enabled": True,
        "optional": True,
        "active": True
    }
}
