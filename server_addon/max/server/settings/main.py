from pydantic import Field
from ayon_server.settings import BaseSettingsModel
from .imageio import ImageIOSettings
from .render_settings import (
    RenderSettingsModel, DEFAULT_RENDER_SETTINGS
)
from .publishers import (
    PublishersModel, DEFAULT_PUBLISH_SETTINGS
)


class PRTAttributesModel(BaseSettingsModel):
    _layout = "compact"
    name: str = Field(title="Name")
    value: str = Field(title="Attribute")


class PointCloudSettings(BaseSettingsModel):
    attribute: list[PRTAttributesModel] = Field(
        default_factory=list, title="Channel Attribute")


class MaxSettings(BaseSettingsModel):
    imageio: ImageIOSettings = Field(
        default_factory=ImageIOSettings,
        title="Color Management (ImageIO)"
    )
    render_settings: RenderSettingsModel = Field(
        default_factory=RenderSettingsModel,
        title="Render Settings"
    )
    PointCloud: PointCloudSettings = Field(
        default_factory=PointCloudSettings,
        title="Point Cloud"
    )
    publish: PublishersModel = Field(
        default_factory=PublishersModel,
        title="Publish Plugins")


DEFAULT_VALUES = {
    "render_settings": DEFAULT_RENDER_SETTINGS,
    "PointCloud": {
        "attribute": [
            {"name": "Age", "value": "age"},
            {"name": "Radius", "value": "radius"},
            {"name": "Position", "value": "position"},
            {"name": "Rotation", "value": "rotation"},
            {"name": "Scale", "value": "scale"},
            {"name": "Velocity", "value": "velocity"},
            {"name": "Color", "value": "color"},
            {"name": "TextureCoordinate", "value": "texcoord"},
            {"name": "MaterialID", "value": "matid"},
            {"name": "custFloats", "value": "custFloats"},
            {"name": "custVecs", "value": "custVecs"},
        ]
    },
    "publish": DEFAULT_PUBLISH_SETTINGS

}
