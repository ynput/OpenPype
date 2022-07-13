import os
import re
import pyblish.api
import json

from openpype.lib import (
    prepare_template_data,
    StringTemplate,
)


class CollectTextures(pyblish.api.ContextPlugin):
    """Collect workfile (and its resource_files) and textures.

        Currently implements use case with Mari and Substance Painter, where
        one workfile is main (.mra - Mari) with possible additional workfiles
        (.spp - Substance)


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

    # from presets
    main_workfile_extensions = ['mra']
    other_workfile_extensions = ['spp', 'psd']
    texture_extensions = ["exr", "dpx", "jpg", "jpeg", "png", "tiff", "tga",
                          "gif", "svg"]

    # additional families (ftrack etc.)
    workfile_families = []
    textures_families = []

    color_space = ["linsRGB", "raw", "acesg"]

    # currently implemented placeholders ["color_space"]
    # describing patterns in file names splitted by regex groups
    input_naming_patterns = {
        # workfile: corridorMain_v001.mra >
        # texture: corridorMain_aluminiumID_v001_baseColor_linsRGB_1001.exr
        "workfile": r'^([^.]+)(_[^_.]*)?_v([0-9]{3,}).+',
        "textures": r'^([^_.]+)_([^_.]+)_v([0-9]{3,})_([^_.]+)_({color_space})_(1[0-9]{3}).+', # noqa
    }
    # matching regex group position to 'input_naming_patterns'
    input_naming_groups = {
        "workfile": ('asset', 'filler', 'version'),
        "textures": ('asset', 'shader', 'version', 'channel', 'color_space',
                     'udim')
    }

    workfile_subset_template = "textures{Subset}Workfile"
    # implemented keys: ["color_space", "channel", "subset", "shader"]
    texture_subset_template = "textures{Subset}_{Shader}_{Channel}"

    def process(self, context):
        self.context = context

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

            explicit_data = {
                "subset": parsed_subset
            }

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

                    formatting_data = self._get_parsed_groups(
                        repre_file,
                        self.input_naming_patterns["workfile"],
                        self.input_naming_groups["workfile"],
                        self.color_space
                    )
                    self.log.info("Parsed groups from workfile "
                                  "name '{}': {}".format(repre_file,
                                                         formatting_data))

                    formatting_data.update(explicit_data)
                    fill_pairs = prepare_template_data(formatting_data)
                    workfile_subset = StringTemplate.format_strict_template(
                        self.workfile_subset_template, fill_pairs
                    )

                    asset_build = self._get_asset_build(
                        repre_file,
                        self.input_naming_patterns["workfile"],
                        self.input_naming_groups["workfile"],
                        self.color_space
                    )
                    version = self._get_version(
                        repre_file,
                        self.input_naming_patterns["workfile"],
                        self.input_naming_groups["workfile"],
                        self.color_space
                    )
                    asset_builds.add((asset_build, version,
                                      workfile_subset, 'workfile'))
                    processed_instance = True

                    if not representations.get(workfile_subset):
                        representations[workfile_subset] = []

                if ext in self.main_workfile_extensions:
                    # workfiles can have only single representation
                    # currently OP is not supporting different extensions in
                    # representation files
                    representations[workfile_subset] = [repre]

                    workfile_files[asset_build] = repre_file

                if ext in self.other_workfile_extensions:
                    # add only if not added already from main
                    if not representations.get(workfile_subset):
                        representations[workfile_subset] = [repre]

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
                    formatting_data = self._get_parsed_groups(
                        repre_file,
                        self.input_naming_patterns["textures"],
                        self.input_naming_groups["textures"],
                        self.color_space
                    )

                    self.log.info("Parsed groups from texture "
                                  "name '{}': {}".format(repre_file,
                                                         formatting_data))

                    c_space = self._get_color_space(
                        repre_file,
                        self.color_space
                    )

                    # optional value
                    channel = self._get_channel_name(
                        repre_file,
                        self.input_naming_patterns["textures"],
                        self.input_naming_groups["textures"],
                        self.color_space
                    )

                    # optional value
                    shader = self._get_shader_name(
                        repre_file,
                        self.input_naming_patterns["textures"],
                        self.input_naming_groups["textures"],
                        self.color_space
                    )

                    explicit_data = {
                        "color_space": c_space or '',  # None throws exception
                        "channel": channel or '',
                        "shader": shader or '',
                        "subset": parsed_subset or ''
                    }

                    formatting_data.update(explicit_data)

                    fill_pairs = prepare_template_data(formatting_data)
                    subset = StringTemplate.format_strict_template(
                        self.texture_subset_template, fill_pairs
                    )

                    asset_build = self._get_asset_build(
                        repre_file,
                        self.input_naming_patterns["textures"],
                        self.input_naming_groups["textures"],
                        self.color_space
                    )
                    version = self._get_version(
                        repre_file,
                        self.input_naming_patterns["textures"],
                        self.input_naming_groups["textures"],
                        self.color_space
                    )
                    if not representations.get(subset):
                        representations[subset] = []
                    representations[subset].append(repre)

                    ver_data = {
                        "color_space": c_space or '',
                        "channel_name": channel or '',
                        "shader_name": shader or ''
                    }
                    version_data[subset] = ver_data

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
                resource_files (list) of resource dicts - to store additional
                  files to main workfile
                representations (list) of dicts - to store workfile info OR
                   all collected texture files, key is asset_build
                version_data (dict) - prepared to store into version doc in DB
                workfile_files (dict) - to store workfile to add to textures
                    key is asset_build
        """
        # sort workfile first
        asset_builds = sorted(asset_builds,
                              key=lambda tup: tup[3], reverse=True)

        # workfile must have version, textures might
        main_version = None
        for asset_build, version, subset, family in asset_builds:
            if not main_version:
                main_version = version

            try:
                version_int = int(version or main_version or 1)
            except ValueError:
                self.log.error("Parsed version {} is not "
                               "an number".format(version))

            new_instance = context.create_instance(subset)
            new_instance.data.update(
                {
                    "subset": subset,
                    "asset": asset,
                    "label": subset,
                    "name": subset,
                    "family": family,
                    "version": version_int,
                    "asset_build": asset_build  # remove in validator
                }
            )

            workfile = workfile_files.get(asset_build)

            if resource_files.get(subset):
                # add resources only when workfile is main style
                for ext in self.main_workfile_extensions:
                    if ext in workfile:
                        new_instance.data.update({
                            "resources": resource_files.get(subset)
                        })
                        break

            # store origin
            if family == 'workfile':
                families = self.workfile_families
                families.append("texture_batch_workfile")

                new_instance.data["source"] = "standalone publisher"
            else:
                families = self.textures_families

                repre = representations.get(subset)[0]
                new_instance.context.data["currentFile"] = os.path.join(
                    repre["stagingDir"], workfile or 'dummy.txt')

            new_instance.data["families"] = families

            # add data for version document
            ver_data = version_data.get(subset)
            if ver_data:
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

            self.log.debug("new instance - {}:: {}".format(
                family,
                json.dumps(new_instance.data, indent=4)))

    def _get_asset_build(self, name,
                         input_naming_patterns, input_naming_groups,
                         color_spaces):
        """Loops through configured workfile patterns to find asset name.

            Asset name used to bind workfile and its textures.

            Args:
                name (str): workfile name
                input_naming_patterns (list):
                    [workfile_pattern] or [texture_pattern]
                input_naming_groups (list)
                    ordinal position of regex groups matching to input_naming..
                color_spaces (list) - predefined color spaces
        """
        asset_name = "NOT_AVAIL"

        return (self._parse_key(name, input_naming_patterns,
                                input_naming_groups, color_spaces, 'asset') or
                asset_name)

    def _get_version(self, name, input_naming_patterns, input_naming_groups,
                     color_spaces):
        found = self._parse_key(name, input_naming_patterns,
                                input_naming_groups, color_spaces, 'version')

        if found:
            return found.replace('v', '')

        self.log.info("No version found in the name {}".format(name))

    def _get_udim(self, name, input_naming_patterns, input_naming_groups,
                  color_spaces):
        """Parses from 'name' udim value."""
        found = self._parse_key(name, input_naming_patterns,
                                input_naming_groups, color_spaces, 'udim')
        if found:
            return found

        self.log.warning("Didn't find UDIM in {}".format(name))

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

    def _get_shader_name(self, name, input_naming_patterns,
                         input_naming_groups, color_spaces):
        """Return parsed shader name.

            Shader name is needed for overlapping udims (eg. udims might be
            used for different materials, shader needed to not overwrite).

            Unknown format of channel name and color spaces >> cs are known
            list - 'color_space' used as a placeholder
        """
        found = None
        try:
            found = self._parse_key(name, input_naming_patterns,
                                    input_naming_groups, color_spaces,
                                    'shader')
        except ValueError:
            self.log.warning("Didn't find shader in {}".format(name))

        return found

    def _get_channel_name(self, name, input_naming_patterns,
                          input_naming_groups, color_spaces):
        """Return parsed channel name.

            Unknown format of channel name and color spaces >> cs are known
            list - 'color_space' used as a placeholder
        """
        found = None
        try:
            found = self._parse_key(name, input_naming_patterns,
                                    input_naming_groups, color_spaces,
                                    'channel')
        except ValueError:
            self.log.warning("Didn't find channel in {}".format(name))

        return found

    def _parse_key(self, name, input_naming_patterns, input_naming_groups,
                   color_spaces, key):
        """Universal way to parse 'name' with configurable regex groups.

            Args:
                name (str): workfile name
                input_naming_patterns (list):
                    [workfile_pattern] or [texture_pattern]
                input_naming_groups (list)
                    ordinal position of regex groups matching to input_naming..
                color_spaces (list) - predefined color spaces

            Raises:
                ValueError - if broken 'input_naming_groups'
        """
        parsed_groups = self._get_parsed_groups(name,
                                                input_naming_patterns,
                                                input_naming_groups,
                                                color_spaces)

        try:
            parsed_value = parsed_groups[key]
            return parsed_value
        except (IndexError, KeyError):
            msg = ("'Textures group positions' must " +
                   "have '{}' key".format(key))
            raise ValueError(msg)

    def _get_parsed_groups(self, name, input_naming_patterns,
                           input_naming_groups, color_spaces):
        """Universal way to parse 'name' with configurable regex groups.

        Args:
            name (str): workfile name or texture name
            input_naming_patterns (list):
                [workfile_pattern] or [texture_pattern]
            input_naming_groups (list)
                ordinal position of regex groups matching to input_naming..
            color_spaces (list) - predefined color spaces

        Returns:
            (dict) {group_name:parsed_value}
        """
        for input_pattern in input_naming_patterns:
            for cs in color_spaces:
                pattern = input_pattern.replace('{color_space}', cs)
                regex_result = re.findall(pattern, name)
                if regex_result:
                    if len(regex_result[0]) == len(input_naming_groups):
                        return dict(zip(input_naming_groups, regex_result[0]))
                    else:
                        self.log.warning("No of parsed groups doesn't match "
                                         "no of group labels")

        raise ValueError("Name '{}' cannot be parsed by any "
                         "'{}' patterns".format(name, input_naming_patterns))

    def _update_representations(self, upd_representations):
        """Frames dont have sense for textures, add collected udims instead."""
        udims = []
        for repre in upd_representations:
            repre.pop("frameStart", None)
            repre.pop("frameEnd", None)
            repre.pop("fps", None)

            # ignore unique name from SP, use extension instead
            # SP enforces unique name, here different subsets >> unique repres
            repre["name"] = repre["ext"].replace('.', '')

            files = repre.get("files", [])
            if not isinstance(files, list):
                files = [files]

            for file_name in files:
                udim = self._get_udim(file_name,
                                      self.input_naming_patterns["textures"],
                                      self.input_naming_groups["textures"],
                                      self.color_space)
                udims.append(udim)

            repre["udim"] = udims  # must be this way, used for filling path

        return upd_representations
