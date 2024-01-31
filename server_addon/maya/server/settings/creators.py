from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum,
)


class CreateLookModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    make_tx: bool = SettingsField(title="Make tx files")
    rs_tex: bool = SettingsField(title="Make Redshift texture files")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default Products"
    )


class BasicCreatorModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Products"
    )


class CreateUnrealStaticMeshModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Products"
    )
    static_mesh_prefix: str = SettingsField("S", title="Static Mesh Prefix")
    collision_prefixes: list[str] = SettingsField(
        default_factory=list,
        title="Collision Prefixes"
    )


class CreateUnrealSkeletalMeshModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default Products")
    joint_hints: str = SettingsField("jnt_org", title="Joint root hint")


class CreateMultiverseLookModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    publish_mip_map: bool = SettingsField(title="publish_mip_map")


class BasicExportMeshModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    write_color_sets: bool = SettingsField(title="Write Color Sets")
    write_face_sets: bool = SettingsField(title="Write Face Sets")
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Products"
    )


def alembic_booleans_enum():
    return [
        "autoSubd",
        "dontSkipUnwritten",
        "eulerFilter",
        "noNormals",
        "preRoll",
        "renderableOnly",
        "selection",
        "stripNamespaces",
        "uvWrite",
        "uvsOnly",
        "verbose",
        "wholeFrameGeo",
        "worldSpace",
        "writeColorSets",
        "writeCreases",
        "writeFaceSets",
        "writeUVSets",
        "writeVisibility",
    ]

def alembic_arguments_enum():
    return [
        "attr",
        "attrPrefix",
        "autoSubd",
        "dataFormat",
        "dontSkipUnwrittenFrames",
        "endFrame",
        "eulerFilter",
        "frameRange",
        "frameRelativeSample",
        "melPerFrameCallback",
        "melPostJobCallback",
        "noNormals",
        "preRoll",
        "preRollStartFrame",
        "pythonPerFrameCallback",
        "pythonPostJobCallback",
        "renderableOnly",
        "root",
        "selection",
        "startFrame",
        "step",
        "stripNamespaces",
        "userAttr",
        "userAttrPrefix",
        "uvWrite",
        "uvsOnly",
        "verbose",
        "wholeFrameGeo",
        "worldSpace",
        "writeColorSets",
        "writeCreases",
        "writeFaceSets",
        "writeUVSets",
        "writeVisibility",
    ]

AlembicDataFormat = Literal["ogawa", "hdf5"]

def alembic_data_formats():
    return [
        "ogawa",
        "hdf5"
    ]

class CreateAnimationModel(BaseSettingsModel):
    write_color_sets: bool = SettingsField(title="Write Color Sets")
    write_face_sets: bool = SettingsField(title="Write Face Sets")
    include_parent_hierarchy: bool = SettingsField(
        title="Include Parent Hierarchy")
    include_user_defined_attributes: bool = SettingsField(
        title="Include User Defined Attributes")
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Products"
    )
    priority: int = Field(
        title="Farm Job Priority")
    pre_roll_start_frame: int = Field(title="Pre Roll Start Frame")
    refresh: bool = Field(
        title="Refresh")
    step: int = Field(title="Step")
    farm: bool = Field(
        title="Submit to the Farm")
    attr: str = Field(title="Attributes")
    attr_prefix: str = Field(title="Attributes Prefix")
    data_format: AlembicDataFormat = Field(
        enum_resolver=alembic_data_formats,
        title="Data Format",
    )
    abc_boolean_args: list[str] = Field(
        default_factory=list,
        enum_resolver=alembic_booleans_enum,
        title="Alembic Boolean Args",
    )
    abc_args_overrides: list[str] = Field(
        default_factory=list,
        enum_resolver=alembic_arguments_enum,
        title="Alembic Arguments Overrides",
    )


class CreatePointCacheModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    write_color_sets: bool = SettingsField(title="Write Color Sets")
    write_face_sets: bool = SettingsField(title="Write Face Sets")
    include_user_defined_attributes: bool = SettingsField(
        title="Include User Defined Attributes"
    )
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Products"
    )
    priority: int = SettingsField(
        title="Farm Job Priority")
    pre_roll_start_frame: int = SettingsField(title="Pre Roll Start Frame")
    refresh: bool = SettingsField(
        title="Refresh")
    step: int = SettingsField(title="Step")
    farm: bool = SettingsField(
        title="Submit to the Farm")
    attr: str = SettingsField(title="Attributes")
    attr_prefix: str = SettingsField(title="Attributes Prefix")
    data_format: AlembicDataFormat = SettingsField(
        enum_resolver=alembic_data_formats,
        title="Data Format",
    )
    abc_boolean_args: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=alembic_booleans_enum,
        title="Alembic Boolean Args",
    )
    abc_args_overrides: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=alembic_arguments_enum,
        title="Alembic Arguments Overrides",
    )


class CreateProxyAlembicModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    write_color_sets: bool = SettingsField(title="Write Color Sets")
    write_face_sets: bool = SettingsField(title="Write Face Sets")
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Products"
    )


class CreateAssModel(BasicCreatorModel):
    expandProcedurals: bool = SettingsField(title="Expand Procedurals")
    motionBlur: bool = SettingsField(title="Motion Blur")
    motionBlurKeys: int = SettingsField(2, title="Motion Blur Keys")
    motionBlurLength: float = SettingsField(0.5, title="Motion Blur Length")
    maskOptions: bool = SettingsField(title="Mask Options")
    maskCamera: bool = SettingsField(title="Mask Camera")
    maskLight: bool = SettingsField(title="Mask Light")
    maskShape: bool = SettingsField(title="Mask Shape")
    maskShader: bool = SettingsField(title="Mask Shader")
    maskOverride: bool = SettingsField(title="Mask Override")
    maskDriver: bool = SettingsField(title="Mask Driver")
    maskFilter: bool = SettingsField(title="Mask Filter")
    maskColor_manager: bool = SettingsField(title="Mask Color Manager")
    maskOperator: bool = SettingsField(title="Mask Operator")


class CreateReviewModel(BasicCreatorModel):
    useMayaTimeline: bool = SettingsField(
        title="Use Maya Timeline for Frame Range."
    )


class CreateVrayProxyModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)
    vrmesh: bool = SettingsField(title="VrMesh")
    alembic: bool = SettingsField(title="Alembic")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default Products")


class CreateMultishotLayout(BasicCreatorModel):
    shotParent: str = SettingsField(title="Shot Parent Folder")
    groupLoadedAssets: bool = SettingsField(title="Group Loaded Assets")
    task_type: list[str] = SettingsField(
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_name: str = SettingsField(title="Task name (regex)")


class CreatorsModel(BaseSettingsModel):
    CreateLook: CreateLookModel = SettingsField(
        default_factory=CreateLookModel,
        title="Create Look"
    )
    CreateRender: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Render"
    )
    # "-" is not compatible in the new model
    CreateUnrealStaticMesh: CreateUnrealStaticMeshModel = SettingsField(
        default_factory=CreateUnrealStaticMeshModel,
        title="Create Unreal_Static Mesh"
    )
    # "-" is not compatible in the new model
    CreateUnrealSkeletalMesh: CreateUnrealSkeletalMeshModel = SettingsField(
        default_factory=CreateUnrealSkeletalMeshModel,
        title="Create Unreal_Skeletal Mesh"
    )
    CreateMultiverseLook: CreateMultiverseLookModel = SettingsField(
        default_factory=CreateMultiverseLookModel,
        title="Create Multiverse Look"
    )
    CreateAnimation: CreateAnimationModel = SettingsField(
        default_factory=CreateAnimationModel,
        title="Create Animation"
    )
    CreateModel: BasicExportMeshModel = SettingsField(
        default_factory=BasicExportMeshModel,
        title="Create Model"
    )
    CreatePointCache: CreatePointCacheModel = SettingsField(
        default_factory=CreatePointCacheModel,
        title="Create Point Cache"
    )
    CreateProxyAlembic: CreateProxyAlembicModel = SettingsField(
        default_factory=CreateProxyAlembicModel,
        title="Create Proxy Alembic"
    )
    CreateMultiverseUsd: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Multiverse USD"
    )
    CreateMultiverseUsdComp: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Multiverse USD Composition"
    )
    CreateMultiverseUsdOver: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Multiverse USD Override"
    )
    CreateAss: CreateAssModel = SettingsField(
        default_factory=CreateAssModel,
        title="Create Ass"
    )
    CreateAssembly: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Assembly"
    )
    CreateCamera: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Camera"
    )
    CreateLayout: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Layout"
    )
    CreateMayaScene: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Maya Scene"
    )
    CreateRenderSetup: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Render Setup"
    )
    CreateReview: CreateReviewModel = SettingsField(
        default_factory=CreateReviewModel,
        title="Create Review"
    )
    CreateRig: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Rig"
    )
    CreateSetDress: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Set Dress"
    )
    CreateVrayProxy: CreateVrayProxyModel = SettingsField(
        default_factory=CreateVrayProxyModel,
        title="Create VRay Proxy"
    )
    CreateVRayScene: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create VRay Scene"
    )
    CreateYetiRig: BasicCreatorModel = SettingsField(
        default_factory=BasicCreatorModel,
        title="Create Yeti Rig"
    )


DEFAULT_CREATORS_SETTINGS = {
    "CreateLook": {
        "enabled": True,
        "make_tx": True,
        "rs_tex": False,
        "default_variants": [
            "Main"
        ]
    },
    "CreateRender": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateUnrealStaticMesh": {
        "enabled": True,
        "default_variants": [
            "",
            "_Main"
        ],
        "static_mesh_prefix": "S",
        "collision_prefixes": [
            "UBX",
            "UCP",
            "USP",
            "UCX"
        ]
    },
    "CreateUnrealSkeletalMesh": {
        "enabled": True,
        "default_variants": [
            "Main",
        ],
        "joint_hints": "jnt_org"
    },
    "CreateMultiverseLook": {
        "enabled": True,
        "publish_mip_map": True
    },
    "CreateAnimation": {
        "write_color_sets": False,
        "write_face_sets": False,
        "include_parent_hierarchy": False,
        "default_variants": [
            "Main"
        ],
        "step": 1.0,
        "abc_boolean_args": [
            "writeColorSets",
            "visibleOnly",
            "worldSpace",
            "writeNormals"
        ],
        "abc_args_overrides": [
            "step",
            "includeParentHierarchy",
            "writeNormals",
            "includeUserDefinedAttributes",
            "attr",
            "attrPrefix"
        ],
        "farm": False,
        "priority": 50,
        "attr": "",
        "attr_prefix": "",
        "data_format": "ogawa",
        "pre_roll_start_frame": 0,
        "refresh": False,
    },
    "CreateModel": {
        "enabled": True,
        "write_color_sets": False,
        "write_face_sets": False,
        "default_variants": [
            "Main",
            "Proxy",
            "Sculpt"
        ]
    },
    "CreatePointCache": {
        "enabled": True,
        "write_color_sets": False,
        "write_face_sets": False,
        "default_variants": [
            "Main"
        ],
        "step": 1.0,
        "abc_boolean_args": [
            "selection",
            "uvWrite",
            "writeCreases",
            "writeVisibility"
        ],
        "abc_args_overrides": [
            "attr",
            "attrPrefix",
            "step",
            "writeColorSets",
            "writeFaceSets",
            "renderableOnly",
            "worldSpace"
        ],
        "include_parent_hierarchy": False,
        "farm": False,
        "priority": 50,
        "attr": "cbId",
        "attr_prefix": "",
        "data_format": "ogawa",
        "pre_roll_start_frame": 0,
        "refresh": False
    },
    "CreateProxyAlembic": {
        "enabled": True,
        "write_color_sets": False,
        "write_face_sets": False,
        "default_variants": [
            "Main"
        ]
    },
    "CreateMultiverseUsd": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateMultiverseUsdComp": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateMultiverseUsdOver": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateAss": {
        "enabled": True,
        "default_variants": [
            "Main"
        ],
        "expandProcedurals": False,
        "motionBlur": True,
        "motionBlurKeys": 2,
        "motionBlurLength": 0.5,
        "maskOptions": False,
        "maskCamera": False,
        "maskLight": False,
        "maskShape": False,
        "maskShader": False,
        "maskOverride": False,
        "maskDriver": False,
        "maskFilter": False,
        "maskColor_manager": False,
        "maskOperator": False
    },
    "CreateAssembly": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateCamera": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateLayout": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateMayaScene": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateRenderSetup": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateReview": {
        "enabled": True,
        "default_variants": [
            "Main"
        ],
        "useMayaTimeline": True
    },
    "CreateRig": {
        "enabled": True,
        "default_variants": [
            "Main",
            "Sim",
            "Cloth"
        ]
    },
    "CreateSetDress": {
        "enabled": True,
        "default_variants": [
            "Main",
            "Anim"
        ]
    },
    "CreateVrayProxy": {
        "enabled": True,
        "vrmesh": True,
        "alembic": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateVRayScene": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    },
    "CreateYetiRig": {
        "enabled": True,
        "default_variants": [
            "Main"
        ]
    }
}
