# -*- coding: utf-8 -*-
"""Creator plugin for creating TyCache."""
from openpype.hosts.max.api import plugin


class CreateTyCache(plugin.MaxCacheCreator):
    """Creator plugin for TyCache."""
    identifier = "io.openpype.creators.max.tyflow"
    label = "TyFlow"
    product_type = "tyflow"
    icon = "gear"
