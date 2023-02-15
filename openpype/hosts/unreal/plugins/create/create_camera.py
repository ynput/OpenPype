# -*- coding: utf-8 -*-
from openpype.hosts.unreal.api.plugin import (
    UnrealActorCreator,
)


class CreateCamera(UnrealActorCreator):
    """Create Camera."""

    identifier = "io.openpype.creators.unreal.camera"
    label = "Camera"
    family = "camera"
    icon = "fa.camera"
