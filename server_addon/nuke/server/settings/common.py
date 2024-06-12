import json
from ayon_server.exceptions import BadRequestException
from ayon_server.settings import BaseSettingsModel, SettingsField
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

    x: float = SettingsField(1.0, title="X")
    y: float = SettingsField(1.0, title="Y")


class Vector3d(BaseSettingsModel):
    _layout = "compact"

    x: float = SettingsField(1.0, title="X")
    y: float = SettingsField(1.0, title="Y")
    z: float = SettingsField(1.0, title="Z")


class Box(BaseSettingsModel):
    _layout = "compact"

    x: float = SettingsField(1.0, title="X")
    y: float = SettingsField(1.0, title="Y")
    r: float = SettingsField(1.0, title="R")
    t: float = SettingsField(1.0, title="T")


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

    template: str = SettingsField(
        "",
        placeholder="""{{key}} or {{key}};{{key}}""",
        title="Template"
    )
    to_type: str = SettingsField(
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
    {"value": "box", "label": "Box"},
    {"value": "expression", "label": "Expression"}
]


class KnobModel(BaseSettingsModel):
    _layout = "expanded"

    type: str = SettingsField(
        title="Type",
        description="Switch between different knob types",
        enum_resolver=lambda: knob_types_enum,
        conditionalEnum=True
    )

    name: str = SettingsField(
        title="Name",
        placeholder="Name"
    )
    text: str = SettingsField("", title="Value")
    color_gui: ColorRGB_uint8 = SettingsField(
        (0, 0, 255),
        title="RGB Uint8",
    )
    boolean: bool = SettingsField(False, title="Value")
    number: int = SettingsField(0, title="Value")
    decimal_number: float = SettingsField(0.0, title="Value")
    vector_2d: Vector2d = SettingsField(
        default_factory=Vector2d,
        title="Value"
    )
    vector_3d: Vector3d = SettingsField(
        default_factory=Vector3d,
        title="Value"
    )
    color: ColorRGBA_float = SettingsField(
        (0.0, 0.0, 1.0, 1.0),
        title="RGBA Float"
    )
    box: Box = SettingsField(
        default_factory=Box,
        title="Value"
    )
    formatable: Formatable = SettingsField(
        default_factory=Formatable,
        title="Formatable"
    )
    expression: str = SettingsField(
        "",
        title="Expression"
    )
