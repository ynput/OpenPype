import os

from openpype.api import Logger
log = Logger().get_logger(__name__)


def clear_rendered(dir_path):
    for _f in os.listdir(dir_path):
        _f_path = os.path.join(dir_path, _f)
        log.info("Removing: `{}`".format(_f_path))
        os.remove(_f_path)
