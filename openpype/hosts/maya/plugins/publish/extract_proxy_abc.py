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

        self.log.info("Extracting Proxy Alembic..")
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

        instance.context.data["cleanupFullPaths"].append(path)

        self.log.info("Extracted {} to {}".format(instance, dirname))
#TODO: clean up the bounding box
        remove_bb = instance.data.get("removeBoundingBoxAfterPublish")
        if remove_bb:
            for bbox in proxy_root:
                bounding_box = cmds.listRelatives(bbox, parent=True)
                cmds.delete(bounding_box)

    def create_proxy_geometry(self, instance, name_suffix, start, end):
        nodes = instance[:]
        if instance.data.get("visibleOnly", False):
            nodes = list(iter_visible_nodes_in_range(nodes,
                                                     start=start,
                                                     end=end))
        inst_selection = cmds.ls(nodes, long=True)
        proxy_root = []
        bbox = cmds.geomToBBox(inst_selection,
                               nameSuffix=name_suffix,
                               keepOriginal=True,
                               single=False,
                               bakeAnimation=True,
                               startTime=start,
                               endTime=end)
        for b in bbox:
            dep_node = cmds.ls(b, dag=True, shapes=False,
                               noIntermediate=True, sn=True)

            for dep in dep_node:
                if "Shape" in dep:
                    continue
                proxy_root.append(dep)
            self.log.debug("proxy_root: {}".format(proxy_root))
        return proxy_root
