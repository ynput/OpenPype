import os
import sys
import re
from pype.vendor import ftrack_api
from pype.ftrack import BaseEvent


class Test_Event(BaseEvent):

    ignore_me = True

    priority = 10000

    def launch(self, session, event):

        '''just a testing event'''

        # self.log.info(event)

        return True


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    Test_Event(session, plugins_presets).register()
