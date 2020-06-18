import pype.lib
from pype.api import Logger


class PhotoshopPrelaunch(pype.lib.PypeHook):
    """This hook will check for the existence of PyWin

    PyWin is a requirement for the Photoshop integration.
    """
    project_code = None

    def __init__(self, logger=None):
        if not logger:
            self.log = Logger().get_logger(self.__class__.__name__)
        else:
            self.log = logger

        self.signature = "( {} )".format(self.__class__.__name__)

    def execute(self, *args, env: dict = None) -> bool:
        output = pype.lib._subprocess(["pip", "install", "pywin32==227"])
        self.log.info(output)
        return True
