"""
Requires:
    None
Provides:
    context -> comment (str)
"""

import pyblish.api
from openpype.lib.attribute_definitions import TextDef
from openpype.pipeline.publish import OpenPypePyblishPluginMixin


class CollectInstanceCommentDef(
    pyblish.api.ContextPlugin,
    OpenPypePyblishPluginMixin
):
    label = "Comment per instance"
    targets = ["local"]
    # Disable plugin by default
    families = ["*"]
    enabled = True

    def process(self, instance):
        pass

    @classmethod
    def get_attribute_defs(cls):
        return [
            TextDef("comment", label="Comment")
        ]


class CollectComment(pyblish.api.ContextPlugin):
    """This plug-ins displays the comment dialog box per default"""

    label = "Collect Comment"
    order = pyblish.api.CollectorOrder

    def process(self, context):
        comment = (context.data.get("comment") or "").strip()
        context.data["comment"] = comment
