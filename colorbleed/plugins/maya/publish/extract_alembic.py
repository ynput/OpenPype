import os

from maya import cmds
import avalon.maya
import colorbleed.api
from colorbleed.maya.lib import extract_alembic


class ExtractColorbleedAlembic(colorbleed.api.Extractor):
    """Extract Alembic Cache

    This extracts an Alembic cache using the `-selection` flag to minimize
    the extracted content to solely what was Collected into the instance.

    """
    label = "Alembic"
    families = ["colorbleed.model",
                "colorbleed.pointcache",
                "colorbleed.proxy"]

    def process(self, instance):

        parent_dir = self.staging_dir(instance)
        filename = "%s.abc" % instance.name
        path = os.path.join(parent_dir, filename)
        options = dict()

        # Collect the start and end including handles if any provided
        # otherwise assume frame 1 as startFrame and the same as endFrame
        start = instance.data.get("startFrame", 1)
        end = instance.data.get("endFrame", start)
        handles = instance.data.get("handles", 0)
        if handles:
            start -= handles
            end += handles
        options['frameRange'] = (start, end)

        # Default verbosity to False
        options['verbose'] = instance.data.get("verbose", False)

        # Collect instance options if found in `instance.data`
        # for specific settings (for user customization)
        for key in ["renderableOnly", "writeColorSets"]:
            if key in instance.data:
                options[key] = instance.data[key]

        with avalon.maya.suspended_refresh():
            with avalon.maya.maintained_selection():
                nodes = instance[:]
                cmds.select(nodes, replace=True, noExpand=True)
                extract_alembic(file=path, **options)
