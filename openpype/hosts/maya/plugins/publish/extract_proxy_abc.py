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

        nodes, roots = self.get_members_and_roots(instance)
        self.log.info("nodes:{}".format(nodes))
        self.log.info("roots:{}".format(roots))
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
            "worldSpace": instance.data.get("worldSpace", True)
        }

        if not instance.data.get("includeParentHierarchy", True):
            options["root"] = roots
            self.log.info("{}".format(options["root"]))

        if int(cmds.about(version=True)) >= 2017:
            # Since Maya 2017 alembic supports multiple uv sets - write them.
            options["writeUVSets"] = True

        if instance.data.get("visibleOnly", False):
            nodes = list(iter_visible_nodes_in_range(nodes,
                                                     start=start,
                                                     end=end))
        with suspended_refresh():
            with maintained_selection():
                self.create_proxy_geometry(instance,
                                           nodes,
                                           start,
                                           end)
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

    def get_members_and_roots(self, instance):
        return instance[:], instance.data.get("setMembers")

    def create_proxy_geometry(self, instance, node, start, end):
        inst_selection = cmds.ls(node, long=True)
        name_suffix = instance.data.get("nameSuffix")
        bbox = cmds.geomToBBox(inst_selection,
                               name=instance.name,
                               nameSuffix=name_suffix,
                               single=instance.data.get("single", False),
                               keepOriginal=True,
                               bakeAnimation=True,
                               startTime=start,
                               endTime=end)
        return cmds.select(bbox, noExpand=True)

