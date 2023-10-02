# -*- coding: utf-8 -*-
from openpype.hosts.unreal.api.plugin import (
    UnrealActorCreator,
)


class CreateLayout(UnrealActorCreator):
    """Layout output for character rigs."""

    identifier = "io.ayon.creators.unreal.layout"
    label = "Layout"
    family = "layout"
    icon = "cubes"
