import os
import shutil

from maya import cmds

import pyblish.api
from openpype.hosts.maya.api import current_file
from openpype.pipeline import publish


class ExtractWorkfileXgen(publish.Extractor):
    """Extract Workfile Xgen."""

    # Offset to run before workfile scene save.
    order = pyblish.api.ExtractorOrder - 0.499
    label = "Extract Workfile Xgen"
    families = ["workfile"]
    hosts = ["maya"]

    def process(self, instance):
        # Validate to extract only when we are publishing a renderlayer as
        # well.
        renderlayer = False
        for i in instance.context:
            is_renderlayer = (
                "renderlayer" in i.data.get("families", []) or
                i.data["family"] == "renderlayer"
            )
            if is_renderlayer and i.data["publish"]:
                renderlayer = True
                break

        if not renderlayer:
            self.log.debug(
                "No publishable renderlayers found in context. Abort Xgen"
                " extraction."
            )
            return

        publish_settings = instance.context["deadline"]["publish"]
        if not publish_settings["MayaSubmitDeadline"]["use_published"]:
            self.log.debug(
                "Not using the published workfile. Abort Xgen extraction."
            )
            return

        # Collect Xgen and Delta files.
        xgen_files = []
        sources = []
        file_path = current_file()
        current_dir = os.path.dirname(file_path)
        attrs = ["xgFileName", "xgBaseFile"]
        for palette in cmds.ls(type="xgmPalette"):
            for attr in attrs:
                source = os.path.join(
                    current_dir, cmds.getAttr(palette + "." + attr)
                )
                if not os.path.exists(source):
                    continue

                ext = os.path.splitext(source)[1]
                if ext == ".xgen":
                    xgen_files.append(source)
                if ext == ".xgd":
                    sources.append(source)

        # Copy .xgen file to temporary location and modify.
        staging_dir = self.staging_dir(instance)
        for source in xgen_files:
            destination = os.path.join(staging_dir, os.path.basename(source))
            shutil.copy(source, destination)

            lines = []
            with open(destination, "r") as f:
                for line in [line.rstrip() for line in f]:
                    if line.startswith("\txgProjectPath"):
                        line = "\txgProjectPath\t\t{}/".format(
                            instance.data["resourcesDir"].replace("\\", "/")
                        )

                    lines.append(line)

            with open(destination, "w") as f:
                f.write("\n".join(lines))

            sources.append(destination)

        # Add resource files to workfile instance.
        transfers = []
        for source in sources:
            basename = os.path.basename(source)
            destination = os.path.join(instance.data["resourcesDir"], basename)
            transfers.append((source, destination))

        import xgenm
        for palette in cmds.ls(type="xgmPalette"):
            relative_data_path = xgenm.getAttr(
                "xgDataPath", palette.replace("|", "")
            ).split(os.pathsep)[0]
            absolute_data_path = relative_data_path.replace(
                "${PROJECT}",
                xgenm.getAttr("xgProjectPath", palette.replace("|", ""))
            )

            for root, _, files in os.walk(absolute_data_path):
                for file in files:
                    source = os.path.join(root, file).replace("\\", "/")
                    destination = os.path.join(
                        instance.data["resourcesDir"],
                        relative_data_path.replace("${PROJECT}", ""),
                        source.replace(absolute_data_path, "")[1:]
                    )
                    transfers.append((source, destination.replace("\\", "/")))

        for source, destination in transfers:
            self.log.debug("Transfer: {} > {}".format(source, destination))

        instance.data["transfers"] = transfers

        # Set palette attributes in preparation for workfile publish.
        attrs = ["xgFileName", "xgBaseFile"]
        data = {}
        for palette in cmds.ls(type="xgmPalette"):
            for attr in attrs:
                value = cmds.getAttr(palette + "." + attr)
                if value:
                    new_value = "resources/{}".format(value)
                    node_attr = "{}.{}".format(palette, attr)
                    self.log.info(
                        "Setting \"{}\" on \"{}\"".format(new_value, node_attr)
                    )
                    cmds.setAttr(node_attr, new_value, type="string")
                    try:
                        data[palette][attr] = value
                    except KeyError:
                        data[palette] = {attr: value}

        instance.data["xgenAttributes"] = data
