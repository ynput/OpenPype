import os

from maya import cmds

from openpype.pipeline import publish
from openpype.hosts.maya.api.alembic import extract_alembic
from openpype.hosts.maya.api.lib import (
    suspended_refresh,
    maintained_selection,
    iter_visible_nodes_in_range,
)
from openpype.lib import (
    BoolDef,
    TextDef,
    NumberDef,
    EnumDef,
    UISeparatorDef,
    UILabelDef,
)
from openpype.pipeline.publish import OpenPypePyblishPluginMixin


class ExtractAlembic(publish.Extractor, OpenPypePyblishPluginMixin):
    """Produce an alembic of just point positions and normals.

    Positions and normals, uvs, creases are preserved, but nothing more,
    for plain and predictable point caches.

    Plugin can run locally or remotely (on a farm - if instance is marked with
    "farm" it will be skipped in local processing, but processed on farm)
    """

    label = "Extract Pointcache (Alembic)"
    hosts = ["maya"]
    families = ["pointcache", "model", "vrayproxy.alembic"]
    targets = ["local", "remote"]
    flags = []
    attr = []
    attrPrefix = []
    dataFormat = "ogawa"
    melPerFrameCallback = ""
    melPostJobCallback = ""
    preRollStartFrame = 0
    pythonPerFrameCallback = ""
    pythonPostJobCallback = ""
    userAttr = ""
    userAttrPrefix = ""
    visibleOnly = False
    overrides = []

    def process(self, instance):
        if instance.data.get("farm"):
            self.log.debug("Should be processed on farm, skipping.")
            return

        nodes, roots = self.get_members_and_roots(instance)

        # Collect the start and end including handles
        start = float(instance.data.get("frameStartHandle", 1))
        end = float(instance.data.get("frameEndHandle", 1))

        attribute_values = self.get_attr_values_from_data(
            instance.data
        )

        attrs = [
            attr.strip()
            for attr in attribute_values.get("attr", "").split(";")
            if attr.strip()
        ]
        attrs += instance.data.get("userDefinedAttributes", [])
        attrs += ["cbId"]

        attr_prefixes = [
            attr.strip()
            for attr in attribute_values.get("attrPrefix", "").split(";")
            if attr.strip()
        ]

        self.log.debug("Extracting pointcache...")
        dirname = self.staging_dir(instance)

        parent_dir = self.staging_dir(instance)
        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(parent_dir, filename)

        root = None
        if not instance.data.get("includeParentHierarchy", True):
            # Set the root nodes if we don't want to include parents
            # The roots are to be considered the ones that are the actual
            # direct members of the set
            root = roots

        args = {
            "file": path,
            "attr": attrs,
            "attrPrefix": attr_prefixes,
            "dataFormat": attribute_values.get("dataFormat", "ogawa"),
            "endFrame": end,
            "eulerFilter": False,
            "noNormals": False,
            "preRoll": False,
            "preRollStartFrame": attribute_values.get(
                "preRollStartFrame", 0
            ),
            "renderableOnly": False,
            "root": root,
            "selection": True,
            "startFrame": start,
            "step": instance.data.get(
                "creator_attributes", {}
            ).get("step", 1.0),
            "stripNamespaces": False,
            "uvWrite": False,
            "verbose": False,
            "wholeFrameGeo": False,
            "worldSpace": False,
            "writeColorSets": False,
            "writeCreases": False,
            "writeFaceSets": False,
            "writeUVSets": False,
            "writeVisibility": False,
        }

        # Export flags are defined as default enabled flags plus publisher
        # enabled flags.
        non_exposed_flags = list(set(self.flags) - set(self.overrides))
        flags = attribute_values["flags"] + non_exposed_flags
        for flag in flags:
            args[flag] = True

        if instance.data.get("visibleOnly", False):
            # If we only want to include nodes that are visible in the frame
            # range then we need to do our own check. Alembic's `visibleOnly`
            # flag does not filter out those that are only hidden on some
            # frames as it counts "animated" or "connected" visibilities as
            # if it's always visible.
            nodes = list(
                iter_visible_nodes_in_range(nodes, start=start, end=end)
            )

        suspend = not instance.data.get("refresh", False)
        with suspended_refresh(suspend=suspend):
            with maintained_selection():
                cmds.select(nodes, noExpand=True)
                self.log.debug(
                    "Running `extract_alembic` with the arguments: {}".format(
                        args
                    )
                )
                extract_alembic(**args)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "abc",
            "ext": "abc",
            "files": filename,
            "stagingDir": dirname,
        }
        instance.data["representations"].append(representation)

        if not instance.data.get("stagingDir_persistent", False):
            instance.context.data["cleanupFullPaths"].append(path)

        self.log.debug("Extracted {} to {}".format(instance, dirname))

        # Extract proxy.
        if not instance.data.get("proxy"):
            self.log.debug("No proxy nodes found. Skipping proxy extraction.")
            return

        path = path.replace(".abc", "_proxy.abc")
        args["file"] = path
        if not instance.data.get("includeParentHierarchy", True):
            # Set the root nodes if we don't want to include parents
            # The roots are to be considered the ones that are the actual
            # direct members of the set
            args["root"] = instance.data["proxyRoots"]

        with suspended_refresh(suspend=suspend):
            with maintained_selection():
                cmds.select(instance.data["proxy"])
                extract_alembic(**args)

        representation = {
            "name": "proxy",
            "ext": "abc",
            "files": os.path.basename(path),
            "stagingDir": dirname,
            "outputName": "proxy",
        }
        instance.data["representations"].append(representation)

    def get_members_and_roots(self, instance):
        return instance[:], instance.data.get("setMembers")

    @classmethod
    def get_attribute_defs(cls):
        override_defs = {
            "attr": {
                "def": TextDef,
                "kwargs": {
                    "label": "Custom Attributes",
                    "placeholder": "attr1; attr2; ...",
                }
            },
            "attrPrefix": {
                "def": TextDef,
                "kwargs": {
                    "label": "Custom Attributes Prefix",
                    "placeholder": "prefix1; prefix2; ...",
                }
            },
            "dataFormat": {
                "def": EnumDef,
                "kwargs": {
                    "label": "Data Format",
                    "items": ["ogawa", "HDF"],
                }
            },
            "melPerFrameCallback": {
                "def": TextDef,
                "kwargs": {
                    "label": "melPerFrameCallback",
                }
            },
            "melPostJobCallback": {
                "def": TextDef,
                "kwargs": {
                    "label": "melPostJobCallback",
                }
            },
            "preRollStartFrame": {
                "def": NumberDef,
                "kwargs": {
                    "label": "Start frame for preroll",
                    "tooltip": (
                        "The frame to start scene evaluation at. This is used"
                        " to set the starting frame for time dependent "
                        "translations and can be used to evaluate run-up that"
                        " isn't actually translated."
                    ),
                }
            },
            "pythonPerFrameCallback": {
                "def": TextDef,
                "kwargs": {
                    "label": "pythonPerFrameCallback",
                }
            },
            "pythonPostJobCallback": {
                "def": TextDef,
                "kwargs": {
                    "label": "pythonPostJobCallback",
                }
            },
            "userAttr": {
                "def": TextDef,
                "kwargs": {
                    "label": "userAttr",
                }
            },
            "userAttrPrefix": {
                "def": TextDef,
                "kwargs": {
                    "label": "userAttrPrefix",
                }
            },
            "visibleOnly": {
                "def": BoolDef,
                "kwargs": {
                    "label": "Visible Only",
                }
            }
        }

        defs = super(ExtractAlembic, cls).get_attribute_defs()

        defs.extend([
            UISeparatorDef("sep_alembic_options"),
            UILabelDef("Alembic Options"),
        ])

        # The Arguments that can be modified by the Publisher
        overrides = set(getattr(cls, "overrides", set()))

        # What we have set in the Settings as defaults.
        flags = set(getattr(cls, "flags", set()))

        enabled_flags = [x for x in flags if x in overrides]
        flags = overrides - set(override_defs.keys())
        if flags:
            defs.append(
                EnumDef(
                    "flags",
                    flags,
                    default=enabled_flags,
                    multiselection=True,
                    label="Export Flags",
                )
            )

        for key, value in override_defs.items():
            if key not in overrides:
                continue

            kwargs = value["kwargs"]
            kwargs["default"] = getattr(cls, key, None)
            defs.append(
                value["def"](key, **value["kwargs"])
            )

        defs.append(
            UISeparatorDef("sep_alembic_options")
        )

        return defs


class ExtractAnimation(ExtractAlembic):
    label = "Extract Animation (Alembic)"
    families = ["animation"]

    def get_members_and_roots(self, instance):
        # Collect the out set nodes
        out_sets = [node for node in instance if node.endswith("out_SET")]
        if len(out_sets) != 1:
            raise RuntimeError(
                "Couldn't find exactly one out_SET: " "{0}".format(out_sets)
            )
        out_set = out_sets[0]
        roots = cmds.sets(out_set, query=True)

        # Include all descendants
        nodes = (
            roots
            + cmds.listRelatives(roots, allDescendents=True, fullPath=True)
            or []
        )

        return nodes, roots
