import avalon.api
import avalon.nuke
from pype.api import (
    get_current_project_settings,
    PypeCreatorMixin
)
from .lib import check_subsetname_exists
import nuke


class PypeCreator(PypeCreatorMixin, avalon.nuke.pipeline.Creator):
    """Pype Nuke Creator class wrapper
    """
    def __init__(self, *args, **kwargs):
        super(PypeCreator, self).__init__(*args, **kwargs)
        self.presets = get_current_project_settings()["nuke"]["create"].get(
            self.__class__.__name__, {}
        )
        if check_subsetname_exists(
                nuke.allNodes(),
                self.data["subset"]):
            msg = ("The subset name `{0}` is already used on a node in"
                   "this workfile.".format(self.data["subset"]))
            self.log.error(msg + '\n\nPlease use other subset name!')
            raise NameError("`{0}: {1}".format(__name__, msg))
        return
