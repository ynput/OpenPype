from pype.lib import RenderInstance, AbstractCollectRender
import pyblish.api

from avalon import aftereffects

class CollectRender(AbstractCollectRender):

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"
    sync_workfile_version = False

    def get_instances(self):
        print("hello")
        return aftereffects.stub().get_metadata()