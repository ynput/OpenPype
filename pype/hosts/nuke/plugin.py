import re
import avalon.api
import avalon.nuke
from pype.api import config

class PypeCreator(avalon.nuke.pipeline.Creator):
    """Pype Nuke Creator class wrapper
    """
    def __init__(self, *args, **kwargs):
        super(PypeCreator, self).__init__(*args, **kwargs)
        self.presets = config.get_presets()['plugins']["nuke"]["create"].get(
            self.__class__.__name__, {}
        )
