from maya import cmds

from openpype.hosts.maya.api import (
    lib,
    plugin
)


class CreatePointCache(plugin.Creator):
    """Alembic pointcache for animated data"""

    name = "pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"
    includeUserDefinedAttributes = False
    eulerFilter = True
    noNormals = False
    preRoll = False
    renderableOnly = False
    uvWrite = True
    writeColorSets = False
    writeFaceSets = False
    wholeFrameGeo = False
    worldSpace = True
    writeVisibility = True
    writeUVSets = True
    writeCreases = False
    dataFormat = "ogawa"
    step = 1.0
    attr = ""
    attrPrefix = ""
    stripNamespaces = True
    verbose = False
    preRollStartFrame = 0
    farm = False
    priority = 50
    includeParentHierarchy = False  # Include parent groups
    refresh = False  # Default to suspend refresh.
    visibleOnly = False  # only nodes that are visible

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        # Add animation data
        self.data.update(lib.collect_animation_data())

        attrs = [
            "includeUserDefinedAttributes",
            "eulerFilter",
            "noNormals",
            "preRoll",
            "renderableOnly",
            "uvWrite",
            "writeColorSets",
            "writeFaceSets",
            "wholeFrameGeo",
            "worldSpace",
            "writeVisibility",
            "writeUVSets",
            "writeCreases",
            "dataFormat",
            "step",
            "attr",
            "attrPrefix",
            "stripNamespaces",
            "verbose",
            "preRollStartFrame",
            "farm",
            "priority",
            "includeParentHierarchy",
            "refresh",
            "visibleOnly"
        ]
        for attr in attrs:
            self.data[attr] = getattr(self, attr)

    def process(self):
        instance = super(CreatePointCache, self).process()

        assProxy = cmds.sets(name=instance + "_proxy_SET", empty=True)
        cmds.sets(assProxy, forceElement=instance)
