import os
import six
import json
import contextlib

from maya import cmds

import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import maintained_selection


@contextlib.contextmanager
def usd_export_attributes(nodes, attrs=None, attr_prefixes=None, mapping=None):
    """Define attributes for the given nodes that should be exported.

    MayaUSDExport will export custom attributes if the Maya node has a
    string attribute `USD_UserExportedAttributesJson` that provides an
    export mapping for the maya attributes. This context manager will try
    to autogenerate such an attribute during the export to include attributes
    for the export.

    Arguments:
        nodes (List[str]): Nodes to process.
        attrs (Optional[List[str]]): Full name of attributes to include.
        attr_prefixes (Optional[List[str]]): Prefixes of attributes to include.
        mapping (Optional[Dict[Dict]]): A mapping per attribute name for the
            conversion to a USD attribute, including renaming, defining type,
            converting attribute precision, etc. This match the usual
            `USD_UserExportedAttributesJson` json mapping of `mayaUSDExport`.
            When no mapping provided for an attribute it will use `{}` as
            value.

    Examples:
          >>> with usd_export_attributes(
          >>>     ["pCube1"], attrs="myDoubleAttributeAsFloat", mapping={
          >>>         "myDoubleAttributeAsFloat": {
          >>>           "usdAttrName": "my:namespace:attrib",
          >>>           "translateMayaDoubleToUsdSinglePrecision": True,
          >>>         }
          >>> })

    """
    # todo: this might be better done with a custom export chaser
    #   see `chaser` argument for `mayaUSDExport`

    import maya.api.OpenMaya as om

    if not attrs and not attr_prefixes:
        # context manager does nothing
        yield
        return

    if attrs is None:
        attrs = []
    if attr_prefixes is None:
        attr_prefixes = []
    if mapping is None:
        mapping = {}

    usd_json_attr = "USD_UserExportedAttributesJson"
    strings = attrs + ["{}*".format(prefix) for prefix in attr_prefixes]
    context_state = {}
    for node in set(nodes):
        node_attrs = cmds.listAttr(node, st=strings)
        if not node_attrs:
            # Nothing to do for this node
            continue

        node_attr_data = {}
        for node_attr in set(node_attrs):
            node_attr_data[node_attr] = mapping.get(node_attr, {})

        if cmds.attributeQuery(usd_json_attr, node=node, exists=True):
            existing_node_attr_value = cmds.getAttr(
                "{}.{}".format(node, usd_json_attr)
            )
            if existing_node_attr_value and existing_node_attr_value != "{}":
                # Any existing attribute mappings in an existing
                # `USD_UserExportedAttributesJson` attribute always take
                # precedence over what this function tries to imprint
                existing_node_attr_data = json.loads(existing_node_attr_value)
                node_attr_data.update(existing_node_attr_data)

        context_state[node] = json.dumps(node_attr_data)

    sel = om.MSelectionList()
    dg_mod = om.MDGModifier()
    fn_string = om.MFnStringData()
    fn_typed = om.MFnTypedAttribute()
    try:
        for node, value in context_state.items():
            data = fn_string.create(value)
            sel.clear()
            if cmds.attributeQuery(usd_json_attr, node=node, exists=True):
                # Set the attribute value
                sel.add("{}.{}".format(node, usd_json_attr))
                plug = sel.getPlug(0)
                dg_mod.newPlugValue(plug, data)
            else:
                # Create attribute with the value as default value
                sel.add(node)
                node_obj = sel.getDependNode(0)
                attr_obj = fn_typed.create(usd_json_attr,
                                           usd_json_attr,
                                           om.MFnData.kString,
                                           data)
                dg_mod.addAttribute(node_obj, attr_obj)
        dg_mod.doIt()
        yield
    finally:
        dg_mod.undoIt()


class ExtractMayaUsd(publish.Extractor):
    """Extractor for Maya USD Asset data.

    Upon publish a .usd (or .usdz) asset file will typically be written.
    """

    label = "Extract Maya USD Asset"
    hosts = ["maya"]
    families = ["mayaUsd"]

    @property
    def options(self):
        """Overridable options for Maya USD Export

        Given in the following format
            - {NAME: EXPECTED TYPE}

        If the overridden option's type does not match,
        the option is not included and a warning is logged.

        """

        # TODO: Support more `mayaUSDExport` parameters
        return {
            "defaultUSDFormat": str,
            "stripNamespaces": bool,
            "mergeTransformAndShape": bool,
            "exportDisplayColor": bool,
            "exportColorSets": bool,
            "exportInstances": bool,
            "exportUVs": bool,
            "exportVisibility": bool,
            "exportComponentTags": bool,
            "exportRefsAsInstanceable": bool,
            "eulerFilter": bool,
            "renderableOnly": bool,
            # "worldspace": bool,
        }

    @property
    def default_options(self):
        """The default options for Maya USD Export."""

        # TODO: Support more `mayaUSDExport` parameters
        return {
            "defaultUSDFormat": "usdc",
            "stripNamespaces": False,
            "mergeTransformAndShape": False,
            "exportDisplayColor": False,
            "exportColorSets": True,
            "exportInstances": True,
            "exportUVs": True,
            "exportVisibility": True,
            "exportComponentTags": True,
            "exportRefsAsInstanceable": False,
            "eulerFilter": True,
            "renderableOnly": False,
            # "worldspace": False
        }

    def parse_overrides(self, instance, options):
        """Inspect data of instance to determine overridden options"""

        for key in instance.data:
            if key not in self.options:
                continue

            # Ensure the data is of correct type
            value = instance.data[key]
            if isinstance(value, six.text_type):
                value = str(value)
            if not isinstance(value, self.options[key]):
                self.log.warning(
                    "Overridden attribute {key} was of "
                    "the wrong type: {invalid_type} "
                    "- should have been {valid_type}".format(
                        key=key,
                        invalid_type=type(value).__name__,
                        valid_type=self.options[key].__name__))
                continue

            options[key] = value

        return options

    def filter_members(self, members):
        # Can be overridden by inherited classes
        return members

    def process(self, instance):

        # Load plugin first
        cmds.loadPlugin("mayaUsdPlugin", quiet=True)

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_name = "{0}.usd".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        # Parse export options
        options = self.default_options
        options = self.parse_overrides(instance, options)
        self.log.debug("Export options: {0}".format(options))

        # Perform extraction
        self.log.debug("Performing extraction ...")

        members = instance.data("setMembers")
        self.log.debug('Collected objects: {}'.format(members))
        members = self.filter_members(members)
        if not members:
            self.log.error('No members!')
            return

        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

        def parse_attr_str(attr_str):
            result = list()
            for attr in attr_str.split(","):
                attr = attr.strip()
                if not attr:
                    continue
                result.append(attr)
            return result

        attrs = parse_attr_str(instance.data.get("attr", ""))
        attrs += instance.data.get("userDefinedAttributes", [])
        attrs += ["cbId"]
        attr_prefixes = parse_attr_str(instance.data.get("attrPrefix", ""))

        self.log.debug('Exporting USD: {} / {}'.format(file_path, members))
        with maintained_selection():
            with usd_export_attributes(instance[:],
                                       attrs=attrs,
                                       attr_prefixes=attr_prefixes):
                cmds.mayaUSDExport(file=file_path,
                                   frameRange=(start, end),
                                   frameStride=instance.data.get("step", 1.0),
                                   exportRoots=members,
                                   **options)

        representation = {
            'name': "usd",
            'ext': "usd",
            'files': file_name,
            'stagingDir': staging_dir
        }
        instance.data.setdefault("representations", []).append(representation)

        self.log.debug(
            "Extracted instance {} to {}".format(instance.name, file_path)
        )


class ExtractMayaUsdAnim(ExtractMayaUsd):
    """Extractor for Maya USD Animation Sparse Cache data.

    This will extract the sparse cache data from the scene and generate a
    USD file with all the animation data.

    Upon publish a .usd sparse cache will be written.
    """
    label = "Extract Maya USD Animation Sparse Cache"
    families = ["animation", "mayaUsd"]
    match = pyblish.api.Subset

    def filter_members(self, members):
        out_set = next((i for i in members if i.endswith("out_SET")), None)

        if out_set is None:
            self.log.warning("Expecting out_SET")
            return None

        members = cmds.ls(cmds.sets(out_set, query=True), long=True)
        return members
