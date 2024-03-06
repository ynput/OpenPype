from ayon_server.settings import BaseSettingsModel, SettingsField


class SimpleCreatorPlugin(BaseSettingsModel):
    _layout = "expanded"
    product_type: str = SettingsField("", title="Product type")
    # TODO add placeholder
    identifier: str = SettingsField("", title="Identifier")
    label: str = SettingsField("", title="Label")
    icon: str = SettingsField("", title="Icon")
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Variants"
    )
    description: str = SettingsField(
        "",
        title="Description",
        widget="textarea"
    )
    detailed_description: str = SettingsField(
        "",
        title="Detailed Description",
        widget="textarea"
    )
    allow_sequences: bool = SettingsField(
        False,
        title="Allow sequences"
    )
    allow_multiple_items: bool = SettingsField(
        False,
        title="Allow multiple items"
    )
    allow_version_control: bool = SettingsField(
        False,
        title="Allow version control"
    )
    extensions: list[str] = SettingsField(
        default_factory=list,
        title="Extensions"
    )


DEFAULT_SIMPLE_CREATORS = [
    {
        "product_type": "workfile",
        "identifier": "",
        "label": "Workfile",
        "icon": "fa.file",
        "default_variants": [
            "Main"
        ],
        "description": "Backup of a working scene",
        "detailed_description": "Workfiles are full scenes from any application that are directly edited by artists. They represent a state of work on a task at a given point and are usually not directly referenced into other scenes.",
        "allow_sequences": False,
        "allow_multiple_items": False,
        "allow_version_control": False,
        "extensions": [
            ".ma",
            ".mb",
            ".nk",
            ".hrox",
            ".hip",
            ".hiplc",
            ".hipnc",
            ".blend",
            ".scn",
            ".tvpp",
            ".comp",
            ".zip",
            ".prproj",
            ".drp",
            ".psd",
            ".psb",
            ".aep"
        ]
    },
    {
        "product_type": "model",
        "identifier": "",
        "label": "Model",
        "icon": "fa.cubes",
        "default_variants": [
            "Main",
            "Proxy",
            "Sculpt"
        ],
        "description": "Clean models",
        "detailed_description": "Models should only contain geometry data, without any extras like cameras, locators or bones.\n\nKeep in mind that models published from tray publisher are not validated for correctness. ",
        "allow_sequences": False,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": [
            ".ma",
            ".mb",
            ".obj",
            ".abc",
            ".fbx",
            ".bgeo",
            ".bgeogz",
            ".bgeosc",
            ".usd",
            ".blend"
        ]
    },
    {
        "product_type": "pointcache",
        "identifier": "",
        "label": "Pointcache",
        "icon": "fa.gears",
        "default_variants": [
            "Main"
        ],
        "description": "Geometry Caches",
        "detailed_description": "Alembic or bgeo cache of animated data",
        "allow_sequences": True,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": [
            ".abc",
            ".bgeo",
            ".bgeogz",
            ".bgeosc"
        ]
    },
    {
        "product_type": "plate",
        "identifier": "",
        "label": "Plate",
        "icon": "mdi.camera-image",
        "default_variants": [
            "Main",
            "BG",
            "Animatic",
            "Reference",
            "Offline"
        ],
        "description": "Footage Plates",
        "detailed_description": "Any type of image seqeuence coming from outside of the studio. Usually camera footage, but could also be animatics used for reference.",
        "allow_sequences": True,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": [
            ".exr",
            ".png",
            ".dpx",
            ".jpg",
            ".tiff",
            ".tif",
            ".mov",
            ".mp4",
            ".avi"
        ]
    },
    {
        "product_type": "render",
        "identifier": "",
        "label": "Render",
        "icon": "mdi.folder-multiple-image",
        "default_variants": [],
        "description": "Rendered images or video",
        "detailed_description": "Sequence or single file renders",
        "allow_sequences": True,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": [
            ".exr",
            ".png",
            ".dpx",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".tif",
            ".mov",
            ".mp4",
            ".avi"
        ]
    },
    {
        "product_type": "camera",
        "identifier": "",
        "label": "Camera",
        "icon": "fa.video-camera",
        "default_variants": [],
        "description": "3d Camera",
        "detailed_description": "Ideally this should be only camera itself with baked animation, however, it can technically also include helper geometry.",
        "allow_sequences": False,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": [
            ".abc",
            ".ma",
            ".hip",
            ".blend",
            ".fbx",
            ".usd"
        ]
    },
    {
        "product_type": "image",
        "identifier": "",
        "label": "Image",
        "icon": "fa.image",
        "default_variants": [
            "Reference",
            "Texture",
            "Concept",
            "Background"
        ],
        "description": "Single image",
        "detailed_description": "Any image data can be published as image product type. References, textures, concept art, matte paints. This is a fallback 2d product type for everything that doesn't fit more specific product type.",
        "allow_sequences": False,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": [
            ".exr",
            ".jpg",
            ".jpeg",
            ".dpx",
            ".bmp",
            ".tif",
            ".tiff",
            ".png",
            ".psb",
            ".psd"
        ]
    },
    {
        "product_type": "vdb",
        "identifier": "",
        "label": "VDB Volumes",
        "icon": "fa.cloud",
        "default_variants": [],
        "description": "Sparse volumetric data",
        "detailed_description": "Hierarchical data structure for the efficient storage and manipulation of sparse volumetric data discretized on three-dimensional grids",
        "allow_sequences": True,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": [
            ".vdb"
        ]
    },
    {
        "product_type": "matchmove",
        "identifier": "",
        "label": "Matchmove",
        "icon": "fa.empire",
        "default_variants": [
            "Camera",
            "Object",
            "Mocap"
        ],
        "description": "Matchmoving script",
        "detailed_description": "Script exported from matchmoving application to be later processed into a tracked camera with additional data",
        "allow_sequences": False,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": []
    },
    {
        "product_type": "rig",
        "identifier": "",
        "label": "Rig",
        "icon": "fa.wheelchair",
        "default_variants": [],
        "description": "CG rig file",
        "detailed_description": "CG rigged character or prop. Rig should be clean of any extra data and directly loadable into it's respective application\t",
        "allow_sequences": False,
        "allow_multiple_items": False,
        "allow_version_control": False,
        "extensions": [
            ".ma",
            ".blend",
            ".hip",
            ".hda"
        ]
    },
    {
        "product_type": "simpleUnrealTexture",
        "identifier": "",
        "label": "Simple UE texture",
        "icon": "fa.image",
        "default_variants": [],
        "description": "Simple Unreal Engine texture",
        "detailed_description": "Texture files with Unreal Engine naming conventions",
        "allow_sequences": False,
        "allow_multiple_items": True,
        "allow_version_control": False,
        "extensions": []
    },
    {
        "product_type": "audio",
        "identifier": "",
        "label": "Audio ",
        "icon": "fa5s.file-audio",
        "default_variants": [
            "Main"
        ],
        "description": "Audio product",
        "detailed_description": "Audio files for review or final delivery",
        "allow_sequences": False,
        "allow_multiple_items": False,
        "allow_version_control": False,
        "extensions": [
            ".wav"
        ]
    }
]
