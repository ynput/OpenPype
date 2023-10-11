from pydantic import Field
from ayon_server.settings import BaseSettingsModel


# Publish Plugins
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
    ValidateWorkfilePaths: ValidateWorkfilePathsModel = Field(
        default_factory=ValidateWorkfilePathsModel,
        title="Validate workfile paths settings.")
    ValidateReviewColorspace: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Review Colorspace.")
    ValidateContainers: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Latest Containers.")
    ValidateSubsetName: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Subset Name.")
    ValidateMeshIsStatic: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Mesh is Static.")
    ValidateUnrealStaticMeshName: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Unreal Static Mesh Name.")


DEFAULT_HOUDINI_PUBLISH_SETTINGS = {
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
    },
    "ValidateReviewColorspace": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateContainers": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateSubsetName": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateMeshIsStatic": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateUnrealStaticMeshName": {
        "enabled": False,
        "optional": True,
        "active": True
    }
}
