import os
import sys
import re
import ftrack_api
from pype.modules.ftrack import BaseEvent


class TestEvent(BaseEvent):

    ignore_me = True

    priority = 10000

    def launch(self, session, event):

        '''just a testing event'''

        # self.log.info(event)

        return True


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    TestEvent(session, plugins_presets).register()
