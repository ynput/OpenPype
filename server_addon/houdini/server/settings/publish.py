from pydantic import Field
from ayon_server.settings import BaseSettingsModel


# Publish Plugins
class CollectAssetHandlesModel(BaseSettingsModel):
    """Collect Frame Range
    Disable this if you want the publisher to
    ignore start and end handles specified in the
    asset data for publish instances
    """
    use_asset_handles: bool = Field(
        title="Use asset handles")


class ValidateWorkfilePathsModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    node_types: list[str] = Field(
        default_factory=list,
        title="Node Types"
    )
    prohibited_vars: list[str] = Field(
        default_factory=list,
        title="Prohibited Variables"
    )


class BasicValidateModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")


class PublishPluginsModel(BaseSettingsModel):
    CollectRopFrameRange: CollectRopFrameRangeModel = Field(
        default_factory=CollectRopFrameRangeModel,
        title="Collect Rop Frame Range.",
        section="Collectors"
    )
    ValidateContainers: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Latest Containers.",
        section="Validators")
    ValidateMeshIsStatic: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Mesh is Static.")
    ValidateReviewColorspace: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Review Colorspace.")
    ValidateSubsetName: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Subset Name.")
    ValidateUnrealStaticMeshName: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Unreal Static Mesh Name.")
    ValidateWorkfilePaths: ValidateWorkfilePathsModel = Field(
        default_factory=ValidateWorkfilePathsModel,
        title="Validate workfile paths settings.")


DEFAULT_HOUDINI_PUBLISH_SETTINGS = {
    "CollectRopFrameRange": {
        "use_asset_handles": True
    },
    "ValidateContainers": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateMeshIsStatic": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateReviewColorspace": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateSubsetName": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateUnrealStaticMeshName": {
        "enabled": False,
        "optional": True,
        "active": True
    },
    "ValidateWorkfilePaths": {
        "enabled": True,
        "optional": True,
        "node_types": [
            "file",
            "alembic"
        ],
        "prohibited_vars": [
            "$HIP",
            "$JOB"
        ]
    }
}
