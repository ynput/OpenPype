import json
from pydantic import Field
from ayon_server.exceptions import BadRequestException
from ayon_server.settings import BaseSettingsModel
from ayon_server.types import (
    ColorRGBA_float,
    ColorRGB_uint8
)


def validate_json_dict(value):
    if not value.strip():
        return "{}"
    try:
        converted_value = json.loads(value)
        success = isinstance(converted_value, dict)
    except json.JSONDecodeError:
        success = False

    if not success:
        raise BadRequestException(
            "Environment's can't be parsed as json object"
        )
    return value


class Vector2d(BaseSettingsModel):
    _layout = "compact"

    x: float = Field(1.0, title="X")
    y: float = Field(1.0, title="Y")


class Vector3d(BaseSettingsModel):
    _layout = "compact"

    x: float = Field(1.0, title="X")
    y: float = Field(1.0, title="Y")
    z: float = Field(1.0, title="Z")


def formatable_knob_type_enum():
    return [
        {"value": "text", "label": "Text"},
        {"value": "number", "label": "Number"},
        {"value": "decimal_number", "label": "Decimal number"},
        {"value": "2d_vector", "label": "2D vector"},
        # "3D vector"
    ]


class Formatable(BaseSettingsModel):
    _layout = "compact"

    template: str = Field(
        "",
        placeholder="""{{key}} or {{key}};{{key}}""",
        title="Template"
    )
    to_type: str = Field(
        "Text",
        title="To Knob type",
        enum_resolver=formatable_knob_type_enum,
    )


knob_types_enum = [
    {"value": "text", "label": "Text"},
    {"value": "formatable", "label": "Formate from template"},
    {"value": "color_gui", "label": "Color GUI"},
    {"value": "boolean", "label": "Boolean"},
    {"value": "number", "label": "Number"},
    {"value": "decimal_number", "label": "Decimal number"},
    {"value": "vector_2d", "label": "2D vector"},
    {"value": "vector_3d", "label": "3D vector"},
    {"value": "color", "label": "Color"},
    {"value": "expression", "label": "Expression"}
]


class KnobModel(BaseSettingsModel):
    """# TODO: new data structure
    - v3 was having type, name, value but
    ayon is not able to make it the same. Current model is
    defining `type` as `text` and instead of `value` the key is `text`.
    So if `type` is `boolean` then key is `boolean` (value).
    """
    _layout = "expanded"

    type: str = Field(
        title="Type",
        description="Switch between different knob types",
        enum_resolver=lambda: knob_types_enum,
        conditionalEnum=True
    )

    name: str = Field(
        title="Name",
        placeholder="Name"
    )
    text: str = Field("", title="Value")
    color_gui: ColorRGB_uint8 = Field(
        (0, 0, 255),
        title="RGB Uint8",
    )
    boolean: bool = Field(False, title="Value")
    number: int = Field(0, title="Value")
    decimal_number: float = Field(0.0, title="Value")
    vector_2d: Vector2d = Field(
        default_factory=Vector2d,
        title="Value"
    )
    vector_3d: Vector3d = Field(
        default_factory=Vector3d,
        title="Value"
    )
    color: ColorRGBA_float = Field(
        (0.0, 0.0, 1.0, 1.0),
        title="RGBA Float"
    )
    formatable: Formatable = Field(
        default_factory=Formatable,
        title="Formatable"
    )
    expression: str = Field(
        "",
        title="Expression"
    )
