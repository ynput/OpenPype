import os

from maya import cmds

from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import (
    extract_alembic,
    suspended_refresh,
    maintained_selection,
    iter_visible_nodes_in_range
)


class ExtractProxyAlembic(publish.Extractor):
    """Produce an alembic for bounding box geometry
    """

    label = "Extract Proxy (Alembic)"
    hosts = ["maya"]
    families = ["proxyAbc"]

    def process(self, instance):
        name_suffix = instance.data.get("nameSuffix")
        # Collect the start and end including handles
        start = float(instance.data.get("frameStartHandle", 1))
        end = float(instance.data.get("frameEndHandle", 1))

        attrs = instance.data.get("attr", "").split(";")
        attrs = [value for value in attrs if value.strip()]
        attrs += ["cbId"]

        attr_prefixes = instance.data.get("attrPrefix", "").split(";")
        attr_prefixes = [value for value in attr_prefixes if value.strip()]

        self.log.debug("Extracting Proxy Alembic..")
        dirname = self.staging_dir(instance)

        filename = "{name}.abc".format(**instance.data)
        path = os.path.join(dirname, filename)

        proxy_root = self.create_proxy_geometry(instance,
                                                name_suffix,
                                                start,
                                                end)

        options = {
            "step": instance.data.get("step", 1.0),
            "attr": attrs,
            "attrPrefix": attr_prefixes,
            "writeVisibility": True,
            "writeCreases": True,
            "writeColorSets": instance.data.get("writeColorSets", False),
            "writeFaceSets": instance.data.get("writeFaceSets", False),
            "uvWrite": True,
            "selection": True,
            "worldSpace": instance.data.get("worldSpace", True),
            "root": proxy_root
        }

        if int(cmds.about(version=True)) >= 2017:
            # Since Maya 2017 alembic supports multiple uv sets - write them.
            options["writeUVSets"] = True

        with suspended_refresh():
            with maintained_selection():
                cmds.select(proxy_root, hi=True, noExpand=True)
                extract_alembic(file=path,
                                startFrame=start,
                                endFrame=end,
                                **options)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'abc',
            'ext': 'abc',
            'files': filename,
            "stagingDir": dirname
        }
        instance.data["representations"].append(representation)

        if not instance.data.get("stagingDir_persistent", False):
            instance.context.data["cleanupFullPaths"].append(path)

        self.log.debug("Extracted {} to {}".format(instance, dirname))
        # remove the bounding box
        bbox_master = cmds.ls("bbox_grp")
        cmds.delete(bbox_master)

    def create_proxy_geometry(self, instance, name_suffix, start, end):
        nodes = instance[:]
        nodes = list(iter_visible_nodes_in_range(nodes,
                                                 start=start,
                                                 end=end))

        inst_selection = cmds.ls(nodes, long=True)
        cmds.geomToBBox(inst_selection,
                        nameSuffix=name_suffix,
                        keepOriginal=True,
                        single=False,
                        bakeAnimation=True,
                        startTime=start,
                        endTime=end)
        # create master group for bounding
        # boxes as the main root
        master_group = cmds.group(name="bbox_grp")
        bbox_sel = cmds.ls(master_group, long=True)
        self.log.debug("proxy_root: {}".format(bbox_sel))
        return bbox_sel
