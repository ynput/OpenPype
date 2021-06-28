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

    version_regex = re.compile(r"v([0-9]+)")
    udim_regex = re.compile(r"_1[0-9]{3}\.")

    #currently implemented placeholders ["color_space"]
    input_naming_patterns = {
        # workfile: ctr_envCorridorMain_texturing_v005.mra >
        #   expected groups: [(asset),(filler),(version)]
        # texture: T_corridorMain_aluminium1_BaseColor_lin_srgb_1029.exr
        #   expected groups: [(asset), (filler),(color_space),(udim)]
        r'^ctr_env([^.]+)_(.+)_v([0-9]{3,}).+':
            r'^T_([^_.]+)_(.*)_({color_space})_(1[0-9]{3}).+'
    }

    workfile_subset_template = "textures{}Workfile"
    # implemented keys: ["color_space", "channel", "subset"]
    texture_subset_template = "textures{subset}_{channel}"

    version_regex = re.compile(r"^(.+)_v([0-9]+)")
    udim_regex = re.compile(r"_1[0-9]{3}\.")

    def process(self, context):
        self.context = context

        import json
        def convertor(value):
            return str(value)

        resource_files = {}
        workfile_files = {}
        representations = {}
        version_data = {}
        asset_builds = set()
        asset = None
        for instance in context:
            if not self.input_naming_patterns:
                raise ValueError("Naming patterns are not configured. \n"
                                 "Ask admin to provide naming conventions "
                                 "for workfiles and textures.")

            if not asset:
                asset = instance.data["asset"]  # selected from SP

            parsed_subset = instance.data["subset"].replace(
                instance.data["family"], '')
            workfile_subset = self.workfile_subset_template.format(
                parsed_subset)

            self.log.info("instance.data:: {}".format(
                json.dumps(instance.data, indent=4, default=convertor)))
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

                    asset_build = self._get_asset_build(
                        repre_file,
                        self.input_naming_patterns.keys(),
                        self.color_space
                    )
                    version = self._get_version(repre_file, self.version_regex)
                    asset_builds.add((asset_build, version,
                                      workfile_subset, 'workfile'))
                    processed_instance = True

                    if not representations.get(workfile_subset):
                        representations[workfile_subset] = []

                if ext in self.main_workfile_extensions:
                    representations[workfile_subset].append(repre)
                    workfile_files[asset_build] = repre_file

                if ext in self.other_workfile_extensions:
                    self.log.info("other")
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
                    c_space = self._get_color_space(
                        repre_file,
                        self.color_space
                    )

                    channel = self._get_channel_name(
                        repre_file,
                        list(self.input_naming_patterns.values()),
                        self.color_space
                    )

                    formatting_data = {
                        "color_space": c_space,
                        "channel": channel,
                        "subset": parsed_subset
                    }
                    self.log.debug("data::{}".format(formatting_data))
                    subset = format_template_with_optional_keys(
                        formatting_data, self.texture_subset_template)

                    asset_build = self._get_asset_build(
                        repre_file,
                        self.input_naming_patterns.values(),
                        self.color_space
                    )
                    version = self._get_version(repre_file, self.version_regex)

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
        # sort workfile first
        asset_builds = sorted(asset_builds,
                              key=lambda tup: tup[3], reverse=True)

        # workfile must have version, textures might
        main_version = None
        for asset_build, version, subset, family in asset_builds:
            if not main_version:
                main_version = version
            new_instance = context.create_instance(subset)
            new_instance.data.update(
                {
                    "subset": subset,
                    "asset": asset,
                    "label": subset,
                    "name": subset,
                    "family": family,
                    "version": int(version or main_version),
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
                    {"versionData": ver_data}
                )

            upd_representations = representations.get(subset)
            if upd_representations and family != 'workfile':
                upd_representations = self._update_representations(
                    upd_representations)

            new_instance.data["representations"] = upd_representations

    def _get_asset_build(self, name, input_naming_patterns, color_spaces):
        """Loops through configured workfile patterns to find asset name.

            Asset name used to bind workfile and its textures.

            Args:
                name (str): workfile name
                input_naming_patterns (list):
                    [workfile_pattern] or [texture_pattern]
        """
        for input_pattern in input_naming_patterns:
            for cs in color_spaces:
                pattern = input_pattern.replace('{color_space}', cs)
                regex_result = re.findall(pattern, name)

                if regex_result:
                    asset_name = regex_result[0][0].lower()
                    return asset_name

        raise ValueError("Couldnt find asset name in {}".format(name))

    def _get_version(self, name, version_regex):
        found = re.search(version_regex, name)
        if found:
            return found.group().replace("v", "")

        self.log.info("No version found in the name {}".format(name))

    def _get_udim(self, name, udim_regex):
        """Parses from 'name' udim value with 'udim_regex'."""
        regex_result = udim_regex.findall(name)
        udim = None
        if not regex_result:
            self.log.warning("Didn't find UDIM in {}".format(name))
        else:
            udim = re.sub("[^0-9]", '', regex_result[0])

        return udim

    def _get_color_space(self, name, color_spaces):
        """Looks for color_space from a list in a file name.

            Color space seems not to be recognizable by regex pattern, set of
            known space spaces must be provided.
        """
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

    def _get_channel_name(self, name, input_naming_patterns, color_spaces):
        """Return parsed channel name.

            Unknown format of channel name and color spaces >> cs are known
            list - 'color_space' used as a placeholder
        """
        for texture_pattern in input_naming_patterns:
            for cs in color_spaces:
                pattern = texture_pattern.replace('{color_space}', cs)
                ret = re.findall(pattern, name)
                if ret:
                    return ret.pop()[1]

    def _update_representations(self, upd_representations):
        """Frames dont have sense for textures, add collected udims instead."""
        udims = []
        for repre in upd_representations:
            repre.pop("frameStart", None)
            repre.pop("frameEnd", None)
            repre.pop("fps", None)

            files = repre.get("files", [])
            if not isinstance(files, list):
                files = [files]

            for file_name in files:
                udim = self._get_udim(file_name, self.udim_regex)
                udims.append(udim)

            repre["udim"] = udims  # must be this way, used for filling path

        return upd_representations

