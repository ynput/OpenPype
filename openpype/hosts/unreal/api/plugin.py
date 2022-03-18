# -*- coding: utf-8 -*-
from abc import ABC

from openpype.pipeline import (
    LegacyCreator,
    LoaderPlugin,
)


class Creator(LegacyCreator):
    """This serves as skeleton for future OpenPype specific functionality"""
    defaults = ['Main']
    maintain_selection = False


class Loader(LoaderPlugin, ABC):
    """This serves as skeleton for future OpenPype specific functionality"""
    pass
