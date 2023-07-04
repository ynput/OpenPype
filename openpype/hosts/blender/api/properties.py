import bpy
from bpy.utils import register_classes_factory

class OpenpypeContext(bpy.types.PropertyGroup):
    pass

classes = []  # [OpenpypeContext]

factory_register, factory_unregister = register_classes_factory(classes)

def register():
    """Register the properties."""
    factory_register()

    bpy.types.Scene.openpype_context = {}
    # bpy.types.Scene.openpype_context = bpy.props.CollectionProperty(
    #     name="OpenPype Context", type=OpenpypeContext, options={"HIDDEN"}
    # )

def unregister():
    """Unregister the properties."""
    factory_unregister()

    del bpy.types.Scene.openpype_context
