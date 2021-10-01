import re

import pyblish
from avalon.tvpaint import lib


class CollectTVPaintInfo(pyblish.api.ContextPlugin):
    label = "Collect TVPaint Info"
    order = pyblish.api.CollectorOrder
    hosts = ["tvpaint"]

    def process(self, context):
        tv_version = lib.execute_george("tv_version")
        pattern = re.compile(r"[0-9]+.[0-9]+.[0-9]+")
        result = pattern.search(tv_version)
        host_version = result.group(0)
        major, minor, patch = host_version.split(".")
        host_type, host_language = tv_version.split(host_version)

        # Remove space between host version and the rest.
        host_type = host_type[:-1]
        host_language = host_language[1:]

        # Remove quotation marks on host_type.
        host_type = host_type[1:-1]

        context.data["hostInfo"] = {
            "type": host_type,
            "version": {
                "major": major,
                "minor": minor,
                "patch": patch
            },
            "language": host_language
        }
