from pydantic import Field
from ayon_server.settings import BaseSettingsModel


# Creator Plugins
class CreatorModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    default_variants: list[str] = Field(
        title="Default Products",
        default_factory=list,
    )


class CreateArnoldAssModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    default_variants: list[str] = Field(
        title="Default Products",
        default_factory=list,
    )
    ext: str = Field(Title="Extension")


class CreateStaticMeshModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    default_variants: list[str] = Field(
        default_factory=list,
        title="Default Products"
    )
    static_mesh_prefixes: str = Field("S", title="Static Mesh Prefix")
    collision_prefixes: list[str] = Field(
        default_factory=list,
        title="Collision Prefixes"
    )


class CreatePluginsModel(BaseSettingsModel):
    CreateAlembicCamera: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Alembic Camera")
    CreateArnoldAss: CreateArnoldAssModel = Field(
        default_factory=CreateArnoldAssModel,
        title="Create Arnold Ass")
    CreateArnoldRop: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Arnold ROP")
    CreateCompositeSequence: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Composite (Image Sequence)")
    CreateHDA: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Houdini Digital Asset")
    CreateKarmaROP: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Karma ROP")
    CreateMantraROP: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Mantra ROP")
    CreatePointCache: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create PointCache (Abc)")
    CreateBGEO: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create PointCache (Bgeo)")
    CreateRedshiftProxy: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Redshift Proxy")
    CreateRedshiftROP: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Redshift ROP")
    CreateReview: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create Review")
    # "-" is not compatible in the new model
    CreateStaticMesh: CreateStaticMeshModel = Field(
        default_factory=CreateStaticMeshModel,
        title="Create Static Mesh")
    CreateUSD: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create USD (experimental)")
    CreateUSDRender: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create USD render (experimental)")
    CreateVDBCache: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create VDB Cache")
    CreateVrayROP: CreatorModel = Field(
        default_factory=CreatorModel,
        title="Create VRay ROP")


DEFAULT_HOUDINI_CREATE_SETTINGS = {
    "CreateAlembicCamera": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateArnoldAss": {
        "enabled": True,
        "default_variants": ["Main"],
        "ext": ".ass"
    },
    "CreateArnoldRop": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateCompositeSequence": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateHDA": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateKarmaROP": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateMantraROP": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreatePointCache": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateBGEO": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateRedshiftProxy": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateRedshiftROP": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateReview": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateStaticMesh": {
        "enabled": True,
        "default_variants": [
            "Main"
        ],
        "static_mesh_prefix": "S",
        "collision_prefixes": [
            "UBX",
            "UCP",
            "USP",
            "UCX"
        ]
    },
    "CreateUSD": {
        "enabled": False,
        "default_variants": ["Main"]
    },
    "CreateUSDRender": {
        "enabled": False,
        "default_variants": ["Main"]
    },
    "CreateVDBCache": {
        "enabled": True,
        "default_variants": ["Main"]
    },
    "CreateVrayROP": {
        "enabled": True,
        "default_variants": ["Main"]
    },
}
