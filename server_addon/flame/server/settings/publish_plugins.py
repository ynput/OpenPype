from ayon_server.settings import Field, BaseSettingsModel, task_types_enum


class XMLPresetAttrsFromCommentsModel(BaseSettingsModel):
    _layout = "expanded"
    name: str = Field("", title="Attribute name")
    type: str = Field(
        default_factory=str,
        title="Attribute type",
        enum_resolver=lambda: ["number", "float", "string"]
    )


class AddTasksModel(BaseSettingsModel):
    _layout = "expanded"
    name: str = Field("", title="Task name")
    type: str = Field(
        default_factory=str,
        title="Task type",
        enum_resolver=task_types_enum
    )
    create_batch_group: bool = Field(
        True,
        title="Create batch group"
    )


class CollectTimelineInstancesModel(BaseSettingsModel):
    _isGroup = True

    xml_preset_attrs_from_comments: list[XMLPresetAttrsFromCommentsModel] = Field(
        default_factory=list,
        title="XML presets attributes parsable from segment comments"
    )
    add_tasks: list[AddTasksModel] = Field(
        default_factory=list,
        title="Add tasks"
    )


class ExportPresetsMappingModel(BaseSettingsModel):
    _layout = "expanded"

    name: str = Field(
        ...,
        title="Name"
    )
    active: bool = Field(True, title="Is active")
    export_type: str = Field(
        "File Sequence",
        title="Eport clip type",
        enum_resolver=lambda: ["Movie", "File Sequence", "Sequence Publish"]
    )
    ext: str = Field("exr", title="Output extension")
    xml_preset_file: str = Field(
        "OpenEXR (16-bit fp DWAA).xml",
        title="XML preset file (with ext)"
    )
    colorspace_out: str = Field(
        "ACES - ACEScg",
        title="Output color (imageio)"
    )
    # TODO remove when resolved or v3 is not a thing anymore
    # NOTE next 4 attributes were grouped under 'other_parameters' but that
    #   created inconsistency with v3 settings and harder conversion handling
    #   - it can be moved back but keep in mind that it must be handled in v3
    #       conversion script too
    xml_preset_dir: str = Field(
        "",
        title="XML preset directory"
    )
    parsed_comment_attrs: bool = Field(
        True,
        title="Parsed comment attributes"
    )
    representation_add_range: bool = Field(
        True,
        title="Add range to representation name"
    )
    representation_tags: list[str] = Field(
        default_factory=list,
        title="Representation tags"
    )
    load_to_batch_group: bool = Field(
        True,
        title="Load to batch group reel"
    )
    batch_group_loader_name: str = Field(
        "LoadClipBatch",
        title="Use loader name"
    )
    filter_path_regex: str = Field(
        ".*",
        title="Regex in clip path"
    )


class ExtractProductResourcesModel(BaseSettingsModel):
    _isGroup = True

    keep_original_representation: bool = Field(
        False,
        title="Publish clip's original media"
    )
    export_presets_mapping: list[ExportPresetsMappingModel] = Field(
        default_factory=list,
        title="Export presets mapping"
    )


class IntegrateBatchGroupModel(BaseSettingsModel):
    enabled: bool = Field(
        False,
        title="Enabled"
    )


class PublishPuginsModel(BaseSettingsModel):
    CollectTimelineInstances: CollectTimelineInstancesModel = Field(
        default_factory=CollectTimelineInstancesModel,
        title="Collect Timeline Instances"
    )

    ExtractProductResources: ExtractProductResourcesModel = Field(
        default_factory=ExtractProductResourcesModel,
        title="Extract Product Resources"
    )

    IntegrateBatchGroup: IntegrateBatchGroupModel = Field(
        default_factory=IntegrateBatchGroupModel,
        title="IntegrateBatchGroup"
    )


DEFAULT_PUBLISH_SETTINGS = {
    "CollectTimelineInstances": {
        "xml_preset_attrs_from_comments": [
            {
                "name": "width",
                "type": "number"
            },
            {
                "name": "height",
                "type": "number"
            },
            {
                "name": "pixelRatio",
                "type": "float"
            },
            {
                "name": "resizeType",
                "type": "string"
            },
            {
                "name": "resizeFilter",
                "type": "string"
            }
        ],
        "add_tasks": [
            {
                "name": "compositing",
                "type": "Compositing",
                "create_batch_group": True
            }
        ]
    },
    "ExtractProductResources": {
        "keep_original_representation": False,
        "export_presets_mapping": [
            {
                "name": "exr16fpdwaa",
                "active": True,
                "export_type": "File Sequence",
                "ext": "exr",
                "xml_preset_file": "OpenEXR (16-bit fp DWAA).xml",
                "colorspace_out": "ACES - ACEScg",
                "xml_preset_dir": "",
                "parsed_comment_attrs": True,
                "representation_add_range": True,
                "representation_tags": [],
                "load_to_batch_group": True,
                "batch_group_loader_name": "LoadClipBatch",
                "filter_path_regex": ".*"
            }
        ]
    },
    "IntegrateBatchGroup": {
        "enabled": False
    }
}
