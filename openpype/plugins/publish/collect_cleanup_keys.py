"""
Requires:
    None
Provides:
    context
        - cleanupFullPaths (list)
        - cleanupEmptyDirs (list)
"""

import pyblish.api


class CollectCleanupKeys(pyblish.api.ContextPlugin):
    """Prepare keys for 'ExplicitCleanUp' plugin."""

    label = "Collect Cleanup Keys"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        context.data["cleanupFullPaths"] = []
        context.data["cleanupEmptyDirs"] = []
