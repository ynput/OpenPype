# -*- coding: utf-8 -*-
from openassetio import hostApi
from openassetio.pluginSystem import P

__all__ = ['Manager']


class Manager(hostApi.Manager):

    @staticmethod
    def identifier():
        return "io.openpype.openassetio.manager"

