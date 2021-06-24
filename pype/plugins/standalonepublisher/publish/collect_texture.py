import os
import re
import pyblish.api
import json

from avalon.api import format_template_with_optional_keys


class CollectTextures(pyblish.api.ContextPlugin):
    """Collect workfile (and its resource_files) and textures.

        Provides:
            1 instance per workfile (with 'resources' filled if needed)
                (workfile family)
            1 instance per group of textures
                (textures family)
    """

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

    workfile_subset_template = "textures{}Workfile"
    # implemented keys: ["color_space", "channel", "subset"]
    texture_subset_template = "textures{subset}_{channel}"

    version_regex = re.compile(r"^(.+)_v([0-9]+)")
    udim_regex = re.compile(r"_1[0-9]{3}\.")

    def process(self, context):
        self.context = context

        resource_files = {}
        workfile_files = {}
        representations = {}
        version_data = {}
        asset_builds = set()
        asset = None
        for instance in context:
            if not asset:
                asset = instance.data["asset"]  # selected from SP

            parsed_subset = instance.data["subset"].replace(
                instance.data["family"], '')
            workfile_subset = self.workfile_subset_template.format(
                parsed_subset)

            processed_instance = False
            for repre in instance.data["representations"]:
                ext = repre["ext"].replace('.', '')
                asset_build = version = None

                if isinstance(repre["files"], list):
                    repre_file = repre["files"][0]
                else:
                    repre_file = repre["files"]

                if ext in self.main_workfile_extensions or \
                        ext in self.other_workfile_extensions:

                    asset_build, version = \
                        self._parse_asset_build(repre_file,
                                                self.version_regex)
                    asset_builds.add((asset_build, version,
                                      workfile_subset, 'workfile'))
                    processed_instance = True

                    if not representations.get(workfile_subset):
                        representations[workfile_subset] = []

                if ext in self.main_workfile_extensions:
                    representations[workfile_subset].append(repre)
                    workfile_files[asset_build] = repre_file

                if ext in self.other_workfile_extensions:
                    # add only if not added already from main
                    if not representations.get(workfile_subset):
                        representations[workfile_subset].append(repre)

                    # only overwrite if not present
                    if not workfile_files.get(asset_build):
                        workfile_files[asset_build] = repre_file

                    if not resource_files.get(workfile_subset):
                        resource_files[workfile_subset] = []
                    item = {
                        "files": [os.path.join(repre["stagingDir"],
                                               repre["files"])],
                        "source": "standalone publisher"
                    }
                    resource_files[workfile_subset].append(item)

                if ext in self.texture_extensions:
                    c_space = self._get_color_space(repre_file,
                                                    self.color_space)

                    channel = self._get_channel_name(repre_file,
                                                     self.color_space)

                    formatting_data = {
                        "color_space": c_space,
                        "channel": channel,
                        "subset": parsed_subset
                    }
                    self.log.debug("data::{}".format(formatting_data))
                    subset = format_template_with_optional_keys(
                        formatting_data, self.texture_subset_template)

                    asset_build, version = \
                        self._parse_asset_build(repre_file,
                                                self.version_regex)

                    if not representations.get(subset):
                        representations[subset] = []
                    representations[subset].append(repre)

                    udim = self._parse_udim(repre_file, self.udim_regex)

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

            upd_representations = representations.get(subset)
            if upd_representations and family != 'workfile':
                for repre in upd_representations:
                    repre.pop("frameStart", None)
                    repre.pop("frameEnd", None)
                    repre.pop("fps", None)

            new_instance = context.create_instance(subset)
            new_instance.data.update(
                {
                    "subset": subset,
                    "asset": asset,
                    "label": subset,
                    "name": subset,
                    "family": family,
                    "version": int(version),
                    "representations": upd_representations,
                    "families": []
                }
            )
            if resource_files.get(subset):
                new_instance.data.update({
                    "resources": resource_files.get(subset)
                })

            workfile = workfile_files.get(asset_build)

            # store origin
            if family == 'workfile':
                new_instance.data["source"] = "standalone publisher"
            else:
                repre = representations.get(subset)[0]
                new_instance.context.data["currentFile"] = os.path.join(
                    repre["stagingDir"], workfile)

            # add data for version document
            ver_data = version_data.get(subset)
            if ver_data:
                ver_data = ver_data[0]
                if workfile:
                    ver_data['workfile'] = workfile

                new_instance.data.update(
                    {"versionData": ver_data,
                     "udim": ver_data["UDIM"]}
                )

            self.log.debug("new instance:: {}".format(
                json.dumps(new_instance.data, indent=4)))

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

    def _get_channel_name(self, name, color_spaces):
        """Return parsed channel name.

            Unknown format of channel name and color spaces >> cs are known
            list, channel between version and cs.
        """
        pattern = "(v[0-9]+_)(.*)(_{})"
        for cs in color_spaces:
            ret = re.findall(pattern.format(cs), name)
            if ret:
                return ret.pop()[1]

