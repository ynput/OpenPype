from openpype.pipeline import install_host
from openpype.hosts.blender import api


def register():
    install_host(api)


def unregister():
    pass
