from openpype.api import (
    Logger
)

import pyblish.api

log = Logger.get_logger(__name__)


class OpenPypePyblishPluginMixin:

    @classmethod
    def get_family_attribute_defs(cls, family):
        return None
