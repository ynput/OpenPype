from openpype.pipeline import install_host
from openpype.hosts.blender.api import BlenderHost


def register():
    install_host(BlenderHost())


def unregister():
    pass
