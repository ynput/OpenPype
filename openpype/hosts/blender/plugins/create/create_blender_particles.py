"""Create a blender particles asset."""
import bpy

from openpype.hosts.blender.api import plugin


class CreateBlenderParticles(plugin.Creator):
    """A grouped package of loaded content"""

    name = "blenderParticlesMain"
    label = "Blender Particles"
    family = "blender.particles"
    icon = "microchip"  # TODO

    bl_types = frozenset({bpy.types.ParticleSettings, bpy.types.Object})
