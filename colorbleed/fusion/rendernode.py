import os
from avalon import api, lib

# TODO: get fusion render node exe from somewhere else
FRN = "C:/Program Files/Blackmagic Design/Fusion Render Node 9/FusionRenderNode.exe"


class FusionRenderNode(api.Action):

    name = "fusionrendernode"
    label = "F9 Render Node"
    icon = "object-group"
    order = 997

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        return True

    def process(self, session, **kwargs):
        """Implement the behavior for when the action is triggered"""
        return lib.launch(executable=FRN,
                          args=[],
                          environment=os.environ.update(session))
