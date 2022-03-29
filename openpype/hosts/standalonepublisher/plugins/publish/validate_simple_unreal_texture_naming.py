# -*- coding: utf-8 -*-
"""Validator for correct file naming."""
import pyblish.api
import openpype.api
from openpype.pipeline import PublishXmlValidationError


class ValidateSimpleUnrealTextureNaming(pyblish.api.InstancePlugin):
    label = "Validate Unreal Texture Names"
    hosts = ["standalonepublisher"]
    families = ["simpleUnrealTexture"]
    order = openpype.api.ValidateContentsOrder

    def process(self, instance):
        ...