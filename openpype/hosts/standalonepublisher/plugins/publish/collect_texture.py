import os
import copy
import re
import opentimelineio as otio
import pyblish.api
from openpype import lib as plib
import json

class CollectTextures(pyblish.api.ContextPlugin):
    """Collect workfile (and its resource_files) and textures."""

    order = pyblish.api.CollectorOrder
    label = "Collect Textures"
    hosts = ["standalonepublisher"]
    families = ["texture_batch"]
    actions = []

    main_workfile_extensions = ['mra']
    other_workfile_extensions = ['spp', 'psd']
    texture_extensions = ["exr", "dpx", "jpg", "jpeg", "png", "tiff", "tga",
                          "gif", "svg"]

    color_space = ["lin_srgb", "raw", "acesg"]

    version_regex = re.compile(r"^(.+)_v([0-9]+)")
    udim_regex = re.compile(r"_1[0-9]{3}\.")

    def process(self, context):
        self.context = context
        import json
        def convertor(value):
            return str(value)

        workfile_subset = "texturesMainWorkfile"
        resource_files = {}
        workfile_files = {}
        representations = {}
        version_data = {}
        asset_builds = set()
        asset = None
        for instance in context:
            if not asset:
                asset = instance.data["asset"]  # selected from SP

            self.log.info("instance.data:: {}".format(
                json.dumps(instance.data, indent=4, default=convertor)))
            processed_instance = False
            for repre in instance.data["representations"]:
                ext = repre["ext"].replace('.', '')
                asset_build = version = None
                if ext in self.main_workfile_extensions or \
                    ext in self.other_workfile_extensions:
                    self.log.info('workfile')
                    asset_build, version = \
                        self._parse_asset_build(repre["files"],
                                                self.version_regex)
                    asset_builds.add((asset_build, version,
                                      workfile_subset, 'workfile'))
                    processed_instance = True

                    if not representations.get(workfile_subset):
                        representations[workfile_subset] = []

                    # asset_build must be here to tie workfile and texture
                    if not workfile_files.get(asset_build):
                        workfile_files[asset_build] = []

                if ext in self.main_workfile_extensions:
                    representations[workfile_subset].append(repre)
                    workfile_files[asset_build].append(repre["files"])

                if ext in self.other_workfile_extensions:
                    self.log.info("other")
                    # add only if not added already from main
                    if not representations.get(workfile_subset):
                        representations[workfile_subset].append(repre)

                    if not workfile_files.get(asset_build):
                        workfile_files[asset_build].append(repre["files"])

                    if not resource_files.get(workfile_subset):
                        resource_files[workfile_subset] = []
                    item = {
                        "files": [os.path.join(repre["stagingDir"],
                                               repre["files"])],
                        "source": "standalone publisher"
                    }
                    resource_files[workfile_subset].append(item)

                if ext in self.texture_extensions:
                    c_space = self._get_color_space(repre["files"][0],
                                                    self.color_space)
                    subset = "texturesMain_{}".format(c_space)

                    asset_build, version = \
                        self._parse_asset_build(repre["files"][0],
                                                self.version_regex)

                    if not representations.get(subset):
                        representations[subset] = []
                    representations[subset].append(repre)

                    udim = self._parse_udim(repre["files"][0], self.udim_regex)

                    if not version_data.get(subset):
                        version_data[subset] = []
                    ver_data = {
                        "color_space": c_space,
                        "UDIM": udim,
                    }
                    version_data[subset].append(ver_data)

                    asset_builds.add(
                        (asset_build, version, subset, "textures"))
                    processed_instance = True

            if processed_instance:
                self.context.remove(instance)

        self.log.info("asset_builds:: {}".format(asset_builds))
        self._create_new_instances(context,
                                   asset,
                                   asset_builds,
                                   resource_files,
                                   representations,
                                   version_data,
                                   workfile_files)

    def _create_new_instances(self, context, asset, asset_builds,
                              resource_files, representations,
                              version_data, workfile_files):
        """Prepare new instances from collected data.

            Args:
                context (ContextPlugin)
                asset (string): selected asset from SP
                asset_builds (set) of tuples
                    (asset_build, version, subset, family)
                resource_files (list) of resource dicts
                representations (dict) of representation files, key is
                    asset_build
        """
        for asset_build, version, subset, family in asset_builds:

            self.log.info("resources:: {}".format(resource_files))
            self.log.info("-"*25)
            self.log.info("representations:: {}".format(representations))
            self.log.info("-"*25)
            self.log.info("workfile_files:: {}".format(workfile_files))

            new_instance = context.create_instance(subset)
            new_instance.data.update(
                {
                    "subset": subset,
                    "asset": asset,
                    "label": subset,
                    "name": subset,
                    "family": family,
                    "version": int(version),
                    "representations": representations.get(subset),
                    "families": [family]
                }
            )
            if resource_files.get(subset):
                new_instance.data.update({
                    "resources": resource_files.get(subset)
                })

            repre = representations.get(subset)[0]
            new_instance.context.data["currentFile"] = os.path.join(
                repre["stagingDir"], repre["files"][0])

            ver_data = version_data.get(subset)
            if ver_data:
                ver_data = ver_data[0]
                if workfile_files.get(asset_build):
                    ver_data['workfile'] = workfile_files.get(asset_build)[0]

                new_instance.data.update(
                    {"versionData": ver_data}
                )

            self.log.info("new instance:: {}".format(json.dumps(new_instance.data, indent=4)))

    def _parse_asset_build(self, name, version_regex):
        regex_result = version_regex.findall(name)
        asset_name = None  # ??
        version_number = 1
        if regex_result:
            asset_name, version_number = regex_result[0]

        return asset_name, version_number

    def _parse_udim(self, name, udim_regex):
        regex_result = udim_regex.findall(name)
        udim = None
        if not regex_result:
            self.log.warning("Didn't find UDIM in {}".format(name))
        else:
            udim = re.sub("[^0-9]", '', regex_result[0])

        return udim

    def _get_color_space(self, name, color_spaces):
        """Looks for color_space from a list in a file name."""
        color_space = None
        found = [cs for cs in color_spaces if
                 re.search("_{}_".format(cs), name)]

        if not found:
            self.log.warning("No color space found in {}".format(name))
        else:
            if len(found) > 1:
                msg = "Multiple color spaces found in {}->{}".format(name,
                                                                     found)
                self.log.warning(msg)

            color_space = found[0]

        return color_space
