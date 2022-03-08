# -*- coding: utf-8 -*-
from abc import ABC

from openpype.pipeline import LegacyCreator
import avalon.api


class Creator(LegacyCreator):
    """This serves as skeleton for future OpenPype specific functionality"""
    defaults = ['Main']


class Loader(avalon.api.Loader, ABC):
    """This serves as skeleton for future OpenPype specific functionality"""
    pass
