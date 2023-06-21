"""
Requires:
    instance     -> currentFile
    instance     -> source

Provides:
    instance    -> originalBasename
    instance    -> originalDirname
"""

import os

import pyblish.api


class CollectSourceForSource(pyblish.api.InstancePlugin):
    """Collects source location of file for instance.

    Used for 'source' template name which handles in place publishing.
    For this kind of publishing files are present with correct file name
    pattern and correct location.
    """

    label = "Collect Source"
    order = pyblish.api.CollectorOrder + 0.495

    def process(self, instance):
        # parse folder name and file name for online and source templates
        # currentFile comes from hosts workfiles
        # source comes from Publisher
        current_file = instance.data.get("currentFile")
        source = instance.data.get("source")
        source_file = current_file or source
        if source_file:
            self.log.debug("Parsing paths for {}".format(source_file))
            if not instance.data.get("originalBasename"):
                instance.data["originalBasename"] = \
                    os.path.basename(source_file)

            if not instance.data.get("originalDirname"):
                instance.data["originalDirname"] = \
                    os.path.dirname(source_file)
