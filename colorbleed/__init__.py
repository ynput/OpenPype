import os
from pyblish import api as pyblish
from avalon import api, pipeline

PACKAGE_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")


def install():
    publish_path = os.path.join(PLUGINS_DIR, "publish")
    print("Registering global plug-ins..")

    pyblish.register_plugin_path(publish_path)


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)


def register_launcher_actions():
    """Register specific actions which should be accessible in the launcher"""

    # Register fusion actions
    from .fusion import rendernode
    pipeline.register_plugin(api.Action, rendernode.FusionRenderNode)

