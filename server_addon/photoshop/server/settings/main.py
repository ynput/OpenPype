from pydantic import Field
from ayon_server.settings import BaseSettingsModel

from .imageio import PhotoshopImageIOModel
from .creator_plugins import PhotoshopCreatorPlugins, DEFAULT_CREATE_SETTINGS
from .publish_plugins import PhotoshopPublishPlugins, DEFAULT_PUBLISH_SETTINGS
from .workfile_builder import WorkfileBuilderPlugin


class PhotoshopSettings(BaseSettingsModel):
    """Photoshop Project Settings."""

    imageio: PhotoshopImageIOModel = Field(
        default_factory=PhotoshopImageIOModel,
        title="OCIO config"
    )

    create: PhotoshopCreatorPlugins = Field(
        default_factory=PhotoshopCreatorPlugins,
        title="Creator plugins"
    )

    publish: PhotoshopPublishPlugins = Field(
        default_factory=PhotoshopPublishPlugins,
        title="Publish plugins"
    )

    workfile_builder: WorkfileBuilderPlugin = Field(
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
