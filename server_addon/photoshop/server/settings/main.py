from ayon_server.settings import BaseSettingsModel, SettingsField

from .imageio import PhotoshopImageIOModel
from .creator_plugins import PhotoshopCreatorPlugins, DEFAULT_CREATE_SETTINGS
from .publish_plugins import PhotoshopPublishPlugins, DEFAULT_PUBLISH_SETTINGS
from .workfile_builder import WorkfileBuilderPlugin


class PhotoshopSettings(BaseSettingsModel):
    """Photoshop Project Settings."""

    imageio: PhotoshopImageIOModel = SettingsField(
        default_factory=PhotoshopImageIOModel,
        title="OCIO config"
    )

    create: PhotoshopCreatorPlugins = SettingsField(
        default_factory=PhotoshopCreatorPlugins,
        title="Creator plugins"
    )

    publish: PhotoshopPublishPlugins = SettingsField(
        default_factory=PhotoshopPublishPlugins,
        title="Publish plugins"
    )

    workfile_builder: WorkfileBuilderPlugin = SettingsField(
        default_factory=WorkfileBuilderPlugin,
        title="Workfile Builder"
    )


DEFAULT_PHOTOSHOP_SETTING = {
    "create": DEFAULT_CREATE_SETTINGS,
    "publish": DEFAULT_PUBLISH_SETTINGS,
    "workfile_builder": {
        "create_first_version": False,
        "custom_templates": []
    }
}
