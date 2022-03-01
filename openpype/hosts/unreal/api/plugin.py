# -*- coding: utf-8 -*-
from abc import ABC

import openpype.api
import avalon.api


class Creator(openpype.api.Creator):
    """This serves as skeleton for future OpenPype specific functionality"""
    defaults = ['Main']


class Loader(avalon.api.Loader, ABC):
    """This serves as skeleton for future OpenPype specific functionality"""
    pass
