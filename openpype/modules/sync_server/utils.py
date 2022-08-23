import time
from openpype.api import Logger
log = Logger().get_logger("SyncServer")


class ResumableError(Exception):
    """Error which could be temporary, skip current loop, try next time"""
    pass


class SiteAlreadyPresentError(Exception):
    """Representation has already site skeleton present."""
    pass


class SyncStatus:
    DO_NOTHING = 0
    DO_UPLOAD = 1
    DO_DOWNLOAD = 2


def time_function(method):
    """ Decorator to print how much time function took.
        For debugging.
        Depends on presence of 'log' object
    """

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            log.debug('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result

    return timed


class EditableScopes:
    SYSTEM = 0
    PROJECT = 1
    LOCAL = 2
