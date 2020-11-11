from pype.lib import abstract_collect_render
import pyblish.api
from abc import ABCMeta
import pyblish.api
import six

from avalon import aftereffects

@six.add_metaclass(ABCMeta)
class CollectRender(abstract_collect_render.AbstractCollectRender):

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"
    sync_workfile_version = False

    def get_instances(self, context):
        import web_pdb
        web_pdb.set_trace()
        print("hello {}".format(context))
        return aftereffects.stub().get_metadata()

    def get_expected_files(self, render_instance):
        import web_pdb
        web_pdb.set_trace()

        return []