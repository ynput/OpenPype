# -*- coding: utf-8 -*-
from openpype.hosts.unreal.api.plugin import (
    UnrealAssetCreator,
)


class CreateStaticMeshFBX(UnrealAssetCreator):
    """Create Static Meshes as FBX geometry."""

    identifier = "io.ayon.creators.unreal.staticmeshfbx"
    label = "Static Mesh (FBX)"
    family = "unrealStaticMesh"
    icon = "cube"
