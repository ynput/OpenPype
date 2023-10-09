from pydantic import validator, Field
from ayon_server.settings import (
    BaseSettingsModel,
    ensure_unique_names,
    task_types_enum
)
from .common import KnobModel, validate_json_dict


def nuke_render_publish_types_enum():
    """Return all nuke render families available in creators."""
    return [
        {"value": "render", "label": "Render"},
        {"value": "prerender", "label": "Prerender"},
        {"value": "image", "label": "Image"}
    ]


def nuke_product_types_enum():
    """Return all nuke families available in creators."""
    return [
        {"value": "nukenodes", "label": "Nukenodes"},
        {"value": "model", "label": "Model"},
        {"value": "camera", "label": "Camera"},
        {"value": "gizmo", "label": "Gizmo"},
        {"value": "source", "label": "Source"}
    ] + nuke_render_publish_types_enum()


class NodeModel(BaseSettingsModel):
    name: str = Field(
        title="Node name"
    )
    nodeclass: str = Field(
        "",
        title="Node class"
    )
    dependent: str = Field(
        "",
        title="Incoming dependency"
    )
    knobs: list[KnobModel] = Field(
        default_factory=list,
        title="Knobs",
    )

    @validator("knobs")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class ThumbnailRepositionNodeModel(BaseSettingsModel):
    node_class: str = Field(title="Node class")
    knobs: list[KnobModel] = Field(title="Knobs", default_factory=list)

    @validator("knobs")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CollectInstanceDataModel(BaseSettingsModel):
    sync_workfile_version_on_product_types: list[str] = Field(
        default_factory=list,
        enum_resolver=nuke_product_types_enum,
        title="Sync workfile versions for familes"
    )


class OptionalPluginModel(BaseSettingsModel):
    enabled: bool = Field(True)
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")


class ValidateKnobsModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    knobs: str = Field(
        "{}",
        title="Knobs",
        widget="textarea",
    )

    @validator("knobs")
    def validate_json(cls, value):
        return validate_json_dict(value)


class ExtractThumbnailModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    use_rendered: bool = Field(title="Use rendered images")
    bake_viewer_process: bool = Field(title="Bake view process")
    bake_viewer_input_process: bool = Field(title="Bake viewer input process")

    nodes: list[NodeModel] = Field(
        default_factory=list,
        title="Nodes (deprecated)"
    )
    reposition_nodes: list[ThumbnailRepositionNodeModel] = Field(
        title="Reposition nodes",
        default_factory=list
    )


class ExtractReviewDataModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")


class ExtractReviewDataLutModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")


class BakingStreamFilterModel(BaseSettingsModel):
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    product_types: list[str] = Field(
        default_factory=list,
        enum_resolver=nuke_render_publish_types_enum,
        title="Sync workfile versions for familes"
    )
    product_names: list[str] = Field(
        default_factory=list, title="Product names")


class ReformatNodesRepositionNodes(BaseSettingsModel):
    node_class: str = Field(title="Node class")
    knobs: list[KnobModel] = Field(
        default_factory=list,
        title="Node knobs")


class ReformatNodesConfigModel(BaseSettingsModel):
    """Only reposition nodes supported.

    You can add multiple reformat nodes and set their knobs.
    Order of reformat nodes is important. First reformat node will
    be applied first and last reformat node will be applied last.
    """
    enabled: bool = Field(False)
    reposition_nodes: list[ReformatNodesRepositionNodes] = Field(
        default_factory=list,
        title="Reposition knobs"
    )


class IntermediateOutputModel(BaseSettingsModel):
    name: str = Field(title="Output name")
    filter: BakingStreamFilterModel = Field(
        title="Filter", default_factory=BakingStreamFilterModel)
    read_raw: bool = Field(title="Read raw switch")
    viewer_process_override: str = Field(title="Viewer process override")
    bake_viewer_process: bool = Field(title="Bake view process")
    bake_viewer_input_process: bool = Field(title="Bake viewer input process")
    reformat_nodes_config: ReformatNodesConfigModel = Field(
        default_factory=ReformatNodesConfigModel,
        title="Reformat Nodes")
    extension: str = Field(title="File extension")
    add_custom_tags: list[str] = Field(
        title="Custom tags", default_factory=list)


class ExtractReviewDataMovModel(BaseSettingsModel):
    """[deprecated] use Extract Review Data Baking
    Streams instead.
    """
    enabled: bool = Field(title="Enabled")
    viewer_lut_raw: bool = Field(title="Viewer lut raw")
    outputs: list[IntermediateOutputModel] = Field(
        default_factory=list,
        title="Baking streams"
    )


class ExtractReviewIntermediatesModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    viewer_lut_raw: bool = Field(title="Viewer lut raw")
    outputs: list[IntermediateOutputModel] = Field(
        default_factory=list,
        title="Baking streams"
    )


class FSubmissionNoteModel(BaseSettingsModel):
    enabled: bool = Field(title="enabled")
    template: str = Field(title="Template")


class FSubmistingForModel(BaseSettingsModel):
    enabled: bool = Field(title="enabled")
    template: str = Field(title="Template")


class FVFXScopeOfWorkModel(BaseSettingsModel):
    enabled: bool = Field(title="enabled")
    template: str = Field(title="Template")


class ExctractSlateFrameParamModel(BaseSettingsModel):
    f_submission_note: FSubmissionNoteModel = Field(
        title="f_submission_note",
        default_factory=FSubmissionNoteModel
    )
    f_submitting_for: FSubmistingForModel = Field(
        title="f_submitting_for",
        default_factory=FSubmistingForModel
    )
    f_vfx_scope_of_work: FVFXScopeOfWorkModel = Field(
        title="f_vfx_scope_of_work",
        default_factory=FVFXScopeOfWorkModel
    )


class ExtractSlateFrameModel(BaseSettingsModel):
    viewer_lut_raw: bool = Field(title="Viewer lut raw")
    key_value_mapping: ExctractSlateFrameParamModel = Field(
        title="Key value mapping",
        default_factory=ExctractSlateFrameParamModel
    )


class IncrementScriptVersionModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")


class PublishPuginsModel(BaseSettingsModel):
    CollectInstanceData: CollectInstanceDataModel = Field(
        title="Collect Instance Version",
        default_factory=CollectInstanceDataModel,
        section="Collectors"
    )
    ValidateCorrectAssetName: OptionalPluginModel = Field(
        title="Validate Correct Folder Name",
        default_factory=OptionalPluginModel,
        section="Validators"
    )
    ValidateContainers: OptionalPluginModel = Field(
        title="Validate Containers",
        default_factory=OptionalPluginModel
    )
    ValidateKnobs: ValidateKnobsModel = Field(
        title="Validate Knobs",
        default_factory=ValidateKnobsModel
    )
    ValidateOutputResolution: OptionalPluginModel = Field(
        title="Validate Output Resolution",
        default_factory=OptionalPluginModel
    )
    ValidateGizmo: OptionalPluginModel = Field(
        title="Validate Gizmo",
        default_factory=OptionalPluginModel
    )
    ValidateBackdrop: OptionalPluginModel = Field(
        title="Validate Backdrop",
        default_factory=OptionalPluginModel
    )
    ValidateScript: OptionalPluginModel = Field(
        title="Validate Script",
        default_factory=OptionalPluginModel
    )
    ExtractThumbnail: ExtractThumbnailModel = Field(
        title="Extract Thumbnail",
        default_factory=ExtractThumbnailModel,
        section="Extractors"
    )
    ExtractReviewData: ExtractReviewDataModel = Field(
        title="Extract Review Data",
        default_factory=ExtractReviewDataModel
    )
    ExtractReviewDataLut: ExtractReviewDataLutModel = Field(
        title="Extract Review Data Lut",
        default_factory=ExtractReviewDataLutModel
    )
    ExtractReviewDataMov: ExtractReviewDataMovModel = Field(
        title="Extract Review Data Mov",
        default_factory=ExtractReviewDataMovModel
    )
    ExtractReviewIntermediates: ExtractReviewIntermediatesModel = Field(
        title="Extract Review Intermediates",
        default_factory=ExtractReviewIntermediatesModel
    )
    ExtractSlateFrame: ExtractSlateFrameModel = Field(
        title="Extract Slate Frame",
        default_factory=ExtractSlateFrameModel
    )
    IncrementScriptVersion: IncrementScriptVersionModel = Field(
        title="Increment Workfile Version",
        default_factory=IncrementScriptVersionModel,
        section="Integrators"
    )


DEFAULT_PUBLISH_PLUGIN_SETTINGS = {
    "CollectInstanceData": {
        "sync_workfile_version_on_product_types": [
            "nukenodes",
            "camera",
            "gizmo",
            "source",
            "render",
            "write"
        ]
    },
    "ValidateCorrectAssetName": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateContainers": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateKnobs": {
        "enabled": False,
        "knobs": "\n".join([
            '{',
            '    "render": {',
            '        "review": true',
            '    }',
            '}'
        ])
    },
    "ValidateOutputResolution": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateGizmo": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateBackdrop": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateScript": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ExtractThumbnail": {
        "enabled": True,
        "use_rendered": True,
        "bake_viewer_process": True,
        "bake_viewer_input_process": True,
        "nodes": [
            {
                "name": "Reformat01",
                "nodeclass": "Reformat",
                "dependency": "",
                "knobs": [
                    {
                        "type": "text",
                        "name": "type",
                        "text": "to format"
                    },
                    {
                        "type": "text",
                        "name": "format",
                        "text": "HD_1080"
                    },
                    {
                        "type": "text",
                        "name": "filter",
                        "text": "Lanczos6"
                    },
                    {
                        "type": "boolean",
                        "name": "black_outside",
                        "boolean": True
                    },
                    {
                        "type": "boolean",
                        "name": "pbb",
                        "boolean": False
                    }
                ]
            }
        ],
        "reposition_nodes": [
            {
                "node_class": "Reformat",
                "knobs": [
                    {
                        "type": "text",
                        "name": "type",
                        "text": "to format"
                    },
                    {
                        "type": "text",
                        "name": "format",
                        "text": "HD_1080"
                    },
                    {
                        "type": "text",
                        "name": "filter",
                        "text": "Lanczos6"
                    },
                    {
                        "type": "bool",
                        "name": "black_outside",
                        "boolean": True
                    },
                    {
                        "type": "bool",
                        "name": "pbb",
                        "boolean": False
                    }
                ]
            }
        ]
    },
    "ExtractReviewData": {
        "enabled": False
    },
    "ExtractReviewDataLut": {
        "enabled": False
    },
    "ExtractReviewDataMov": {
        "enabled": True,
        "viewer_lut_raw": False,
        "outputs": [
            {
                "name": "baking",
                "filter": {
                    "task_types": [],
                    "product_types": [],
                    "product_names": []
                },
                "read_raw": False,
                "viewer_process_override": "",
                "bake_viewer_process": True,
                "bake_viewer_input_process": True,
                "reformat_nodes_config": {
                    "enabled": False,
                    "reposition_nodes": [
                        {
                            "node_class": "Reformat",
                            "knobs": [
                                {
                                    "type": "text",
                                    "name": "type",
                                    "text": "to format"
                                },
                                {
                                    "type": "text",
                                    "name": "format",
                                    "text": "HD_1080"
                                },
                                {
                                    "type": "text",
                                    "name": "filter",
                                    "text": "Lanczos6"
                                },
                                {
                                    "type": "bool",
                                    "name": "black_outside",
                                    "boolean": True
                                },
                                {
                                    "type": "bool",
                                    "name": "pbb",
                                    "boolean": False
                                }
                            ]
                        }
                    ]
                },
                "extension": "mov",
                "add_custom_tags": []
            }
        ]
    },
    "ExtractReviewIntermediates": {
        "enabled": True,
        "viewer_lut_raw": False,
        "outputs": [
            {
                "name": "baking",
                "filter": {
                    "task_types": [],
                    "product_types": [],
                    "product_names": []
                },
                "read_raw": False,
                "viewer_process_override": "",
                "bake_viewer_process": True,
                "bake_viewer_input_process": True,
                "reformat_nodes_config": {
                    "enabled": False,
                    "reposition_nodes": [
                        {
                            "node_class": "Reformat",
                            "knobs": [
                                {
                                    "type": "text",
                                    "name": "type",
                                    "text": "to format"
                                },
                                {
                                    "type": "text",
                                    "name": "format",
                                    "text": "HD_1080"
                                },
                                {
                                    "type": "text",
                                    "name": "filter",
                                    "text": "Lanczos6"
                                },
                                {
                                    "type": "bool",
                                    "name": "black_outside",
                                    "boolean": True
                                },
                                {
                                    "type": "bool",
                                    "name": "pbb",
                                    "boolean": False
                                }
                            ]
                        }
                    ]
                },
                "extension": "mov",
                "add_custom_tags": []
            }
        ]
    },
    "ExtractSlateFrame": {
        "viewer_lut_raw": False,
        "key_value_mapping": {
            "f_submission_note": {
                "enabled": True,
                "template": "{comment}"
            },
            "f_submitting_for": {
                "enabled": True,
                "template": "{intent[value]}"
            },
            "f_vfx_scope_of_work": {
                "enabled": False,
                "template": ""
            }
        }
    },
    "IncrementScriptVersion": {
        "enabled": True,
        "optional": True,
        "active": True
    }
}
