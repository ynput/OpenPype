import os
import shutil
import copy

from maya import cmds

import pyblish.api
from openpype.hosts.maya.api import current_file
from openpype.hosts.maya.api.lib import extract_alembic
from openpype.pipeline import publish
from openpype.lib import StringTemplate


class ExtractWorkfileXgen(publish.Extractor):
    """Extract Workfile Xgen."""

    # Offset to run before workfile scene save.
    order = pyblish.api.ExtractorOrder - 0.499
    label = "Extract Workfile Xgen"
    families = ["workfile"]
    hosts = ["maya"]

    def process(self, instance):
        transfers = []

        # Validate there is any palettes in the scene.
        if not cmds.ls(type="xgmPalette"):
            self.log.debug(
                "No collections found in the scene. Abort Xgen extraction."
            )
            return
        else:
            import xgenm

        # Validate to extract only when we are publishing a renderlayer as
        # well.
        renderlayer = False
        start_frame = None
        end_frame = None
        for i in instance.context:
            is_renderlayer = (
                "renderlayer" in i.data.get("families", []) or
                i.data["family"] == "renderlayer"
            )
            if is_renderlayer and i.data["publish"]:
                renderlayer = True

                if start_frame is None:
                    start_frame = i.data["frameStart"]
                if end_frame is None:
                    end_frame = i.data["frameEnd"]

                if i.data["frameStart"] < start_frame:
                    start_frame = i.data["frameStart"]
                if i.data["frameEnd"] > end_frame:
                    end_frame = i.data["frameEnd"]

                break

        if not renderlayer:
            self.log.debug(
                "No publishable renderlayers found in context. Abort Xgen"
                " extraction."
            )
            return

        # We decrement start frame and increment end frame so motion blur will
        # render correctly.
        start_frame -= 1
        end_frame += 1

        # Extract patches alembic.
        basename, _ = os.path.splitext(current_file())
        dirname = os.path.dirname(current_file())
        kwargs = {"attrPrefix": ["xgen"], "stripNamespaces": True}
        alembic_files = []
        for palette in cmds.ls(type="xgmPalette"):
            patch_names = []
            for description in xgenm.descriptions(palette):
                for name in xgenm.boundGeometry(palette, description):
                    patch_names.append(name)

            alembic_file = os.path.join(
                dirname,
                "{}__{}.abc".format(basename, palette.replace(":", "__ns__"))
            )
            extract_alembic(
                alembic_file,
                root=patch_names,
                selection=False,
                startFrame=float(start_frame),
                endFrame=float(end_frame),
                verbose=True,
                **kwargs
            )
            alembic_files.append(alembic_file)

        template_data = copy.deepcopy(instance.data["anatomyData"])
        published_maya_path = StringTemplate(
            instance.context.data["anatomy"].templates["publish"]["file"]
        ).format(template_data)
        published_basename, _ = os.path.splitext(published_maya_path)

        for source in alembic_files:
            destination = os.path.join(
                os.path.dirname(instance.data["resourcesDir"]),
                os.path.basename(source.replace(basename, published_basename))
            )
            transfers.append((source, destination))

        # Validate that we are using the published workfile.
        deadline_settings = instance.context.get("deadline")
        if deadline_settings:
            publish_settings = deadline_settings["publish"]
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
                        path = os.path.dirname(instance.data["resourcesDir"])
                        line = "\txgProjectPath\t\t{}/".format(
                            path.replace("\\", "/")
                        )

                    lines.append(line)

            with open(destination, "w") as f:
                f.write("\n".join(lines))

            sources.append(destination)

        # Add resource files to workfile instance.
        for source in sources:
            basename = os.path.basename(source)
            destination = os.path.join(
                os.path.dirname(instance.data["resourcesDir"]), basename
            )
            transfers.append((source, destination))

        destination_dir = os.path.join(
            instance.data["resourcesDir"], "collections"
        )
        for palette in cmds.ls(type="xgmPalette"):
            project_path = xgenm.getAttr("xgProjectPath", palette)
            data_path = xgenm.getAttr("xgDataPath", palette)
            data_path = data_path.replace("${PROJECT}", project_path)
            for path in data_path.split(os.pathsep):
                for root, _, files in os.walk(path):
                    for f in files:
                        source = os.path.join(root, f)
                        destination = "{}/{}{}".format(
                            destination_dir,
                            palette.replace(":", "__ns__"),
                            source.replace(path, "")
                        )
                        transfers.append((source, destination))

        for source, destination in transfers:
            self.log.debug("Transfer: {} > {}".format(source, destination))

        instance.data["transfers"] = transfers

        # Set palette attributes in preparation for workfile publish.
        attrs = {"xgFileName": None, "xgBaseFile": ""}
        data = {}
        for palette in cmds.ls(type="xgmPalette"):
            attrs["xgFileName"] = "resources/{}.xgen".format(
                palette.replace(":", "__ns__")
            )
            for attr, value in attrs.items():
                node_attr = palette + "." + attr

                old_value = cmds.getAttr(node_attr)
                try:
                    data[palette][attr] = old_value
                except KeyError:
                    data[palette] = {attr: old_value}

                cmds.setAttr(node_attr, value, type="string")
                self.log.info(
                    "Setting \"{}\" on \"{}\"".format(value, node_attr)
                )

            cmds.setAttr(palette + "." + "xgExportAsDelta", False)

        instance.data["xgenAttributes"] = data
