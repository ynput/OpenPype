"""Load and assign extracted particles."""

import bpy

from openpype.hosts.blender.api import plugin


class BlenderParticlesLoader(plugin.AssetLoader):
    """Load and assign extracted particles from .blend file."""

    representations = ["blend"]

    color = "orange"
    no_namespace = True

    bl_types = frozenset({bpy.types.ParticleSettings, bpy.types.Object})


class LinkBlenderParticlesLoader(BlenderParticlesLoader):
    """Link particles from a .blend file."""

    families = ["blender.particles"]

    label = "Link Particles"
    icon = "link"
    order = 0

    load_type = "LINK"


class AppendBlenderParticlesLoader(BlenderParticlesLoader):
    """Append particles from a .blend file."""

    families = ["blender.particles"]

    label = "Append Particles"
    icon = "paperclip"
    order = 1

    load_type = "APPEND"
