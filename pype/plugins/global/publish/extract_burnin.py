import os
import re
import json
import copy

import pype.api
import pyblish


class ExtractBurnin(pype.api.Extractor):
    """
    Extractor to create video with pre-defined burnins from
    existing extracted video representation.

    It will work only on represenations having `burnin = True` or
    `tags` including `burnin`
    """

    label = "Extract burnins"
    order = pyblish.api.ExtractorOrder + 0.03
    families = ["review", "burnin"]
    hosts = [
        "nuke",
        "maya",
        "shell",
        "nukestudio",
        "premiere",
        "standalonepublisher",
        "harmony"
    ]
    optional = True

    positions = [
        "top_left", "top_centered", "top_right",
        "bottom_right", "bottom_centered", "bottom_left"
    ]
    # Default options for burnins for cases that are not set in presets.
    default_options = {
        "opacity": 1,
        "x_offset": 5,
        "y_offset": 5,
        "bg_padding": 5,
        "bg_opacity": 0.5,
        "font_size": 42
    }

    # Preset attributes
    profiles = None
    options = None
    fields = None

    def process(self, instance):
        # ffmpeg doesn't support multipart exrs
        if instance.data.get("multipartExr") is True:
            instance_label = (
                getattr(instance, "label", None)
                or instance.data.get("label")
                or instance.data.get("name")
            )
            self.log.info((
                "Instance \"{}\" contain \"multipartExr\". Skipped."
            ).format(instance_label))
            return

        # QUESTION what is this for and should we raise an exception?
        if "representations" not in instance.data:
            raise RuntimeError("Burnin needs already created mov to work on.")

        if self.use_legacy_code(instance):
            return self.legacy_process(instance)
        self.main_process(instance)

        # Remove any representations tagged for deletion.
        # QUESTION Is possible to have representation with "delete" tag?
        for repre in tuple(instance.data["representations"]):
            if "delete" in repre.get("tags", []):
                self.log.debug("Removing representation: {}".format(repre))
                instance.data["representations"].remove(repre)

        self.log.debug(instance.data["representations"])

    def use_legacy_code(self, instance):
        presets = instance.context.data.get("presets")
        if presets is None and self.profiles is None:
            return True
        return "burnins" in (presets.get("tools") or {})

    def main_process(self, instance):
        # TODO get these data from context
        host_name = os.environ["AVALON_APP"]
        task_name = os.environ["AVALON_TASK"]
        family = self.main_family_from_instance(instance)

        # Find profile most matching current host, task and instance family
        profile = self.find_matching_profile(host_name, task_name, family)
        if not profile:
            self.log.info((
                "Skipped instance. None of profiles in presets are for"
                " Host: \"{}\" | Family: \"{}\" | Task \"{}\""
            ).format(host_name, family, task_name))
            return

        # Pre-filter burnin definitions by instance families
        burnin_defs = self.filter_burnins_by_families(profile, instance)
        if not burnin_defs:
            self.log.info((
                "Skipped instance. Burnin definitions are not set for profile"
                " Host: \"{}\" | Family: \"{}\" | Task \"{}\" | Profile \"{}\""
            ).format(host_name, family, task_name, profile))
            return

        # Prepare burnin options
        profile_options = copy.deepcopy(self.default_options)
        for key, value in (self.options or {}).items():
            if value is not None:
                profile_options[key] = value

        # Prepare global burnin values from presets
        profile_burnins = {}
        for key, value in (self.fields or {}).items():
            key_low = key.lower()
            if key_low in self.positions:
                if value is not None:
                    profile_burnins[key_low] = value

        # Prepare basic data for processing
        _burnin_data, _temp_data = self.prepare_basic_data(instance)

        anatomy = instance.context.data["anatomy"]
        scriptpath = self.burnin_script_path()
        executable = self.python_executable_path()

        for idx, repre in enumerate(tuple(instance.data["representations"])):
            self.log.debug("repre ({}): `{}`".format(idx + 1, repre["name"]))
            if not self.repres_is_valid(repre):
                continue

            # Filter output definition by representation tags (optional)
            repre_burnin_defs = self.filter_burnins_by_tags(
                burnin_defs, repre["tags"]
            )
            if not repre_burnin_defs:
                self.log.info((
                    "Skipped representation. All burnin definitions from"
                    " selected profile does not match to representation's"
                    " tags. \"{}\""
                ).format(str(repre["tags"])))
                continue

            # Create copy of `_burnin_data` and `_temp_data` for repre.
            burnin_data = copy.deepcopy(_burnin_data)
            temp_data = copy.deepcopy(_temp_data)

            # Prepare representation based data.
            self.prepare_repre_data(instance, repre, burnin_data, temp_data)

            # Add anatomy keys to burnin_data.
            filled_anatomy = anatomy.format_all(burnin_data)
            burnin_data["anatomy"] = filled_anatomy.get_solved()

            first_output = True

            files_to_delete = []
            for filename_suffix, burnin_def in repre_burnin_defs.items():
                new_repre = copy.deepcopy(repre)

                # Keep "ftrackreview" tag only on first output
                if first_output:
                    first_output = False
                elif "ftrackreview" in new_repre["tags"]:
                    new_repre["tags"].remove("ftrackreview")

                burnin_options = copy.deepcopy(profile_options)
                burnin_values = copy.deepcopy(profile_burnins)

                # Options overrides
                for key, value in (burnin_def.get("options") or {}).items():
                    # Set or override value if is valid
                    if value is not None:
                        burnin_options[key] = value

                # Burnin values overrides
                for key, value in burnin_def.items():
                    key_low = key.lower()
                    if key_low in self.positions:
                        if value is not None:
                            # Set or override value if is valid
                            burnin_values[key_low] = value

                        elif key_low in burnin_values:
                            # Pop key if value is set to None (null in json)
                            burnin_values.pop(key_low)

                # Remove "delete" tag from new representation
                if "delete" in new_repre["tags"]:
                    new_repre["tags"].remove("delete")

                # Update name and outputName to be able have multiple outputs
                # Join previous "outputName" with filename suffix
                new_name = "_".join([new_repre["outputName"], filename_suffix])
                new_repre["name"] = new_name
                new_repre["outputName"] = new_name

                # Prepare paths and files for process.
                self.input_output_paths(new_repre, temp_data, filename_suffix)

                # Data for burnin script
                script_data = {
                    "input": temp_data["full_input_path"],
                    "output": temp_data["full_output_path"],
                    "burnin_data": burnin_data,
                    "options": burnin_options,
                    "values": burnin_values
                }

                self.log.debug(
                    "script_data: {}".format(json.dumps(script_data, indent=4))
                )

                # Dump data to string
                dumped_script_data = json.dumps(script_data)

                # Prepare subprocess arguments
                args = [executable, scriptpath, dumped_script_data]
                self.log.debug("Executing: {}".format(args))

                # Run burnin script
                output = pype.api.subprocess(args, shell=True)
                self.log.debug("Output: {}".format(output))

                for filepath in temp_data["full_input_paths"]:
                    filepath = filepath.replace("\\", "/")
                    if filepath not in files_to_delete:
                        files_to_delete.append(filepath)

                # Add new representation to instance
                instance.data["representations"].append(new_repre)

            # Remove source representation
            # NOTE we maybe can keep source representation if necessary
            instance.data["representations"].remove(repre)

            # Delete input files
            for filepath in files_to_delete:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    self.log.debug("Removed: \"{}\"".format(filepath))

    def prepare_basic_data(self, instance):
        """Pick data from instance for processing and for burnin strings.

        Args:
            instance (Instance): Currently processed instance.

        Returns:
            tuple: `(burnin_data, temp_data)` - `burnin_data` contain data for
                filling burnin strings. `temp_data` are for repre pre-process
                preparation.
        """
        self.log.debug("Prepring basic data for burnins")
        context = instance.context

        version = instance.data.get("version")
        if version is None:
            version = context.data.get("version")

        frame_start = instance.data.get("frameStart")
        if frame_start is None:
            self.log.warning(
                "Key \"frameStart\" is not set. Setting to \"0\"."
            )
            frame_start = 0
        frame_start = int(frame_start)

        frame_end = instance.data.get("frameEnd")
        if frame_end is None:
            self.log.warning(
                "Key \"frameEnd\" is not set. Setting to \"1\"."
            )
            frame_end = 1
        frame_end = int(frame_end)

        handles = instance.data.get("handles")
        if handles is None:
            handles = context.data.get("handles")
            if handles is None:
                handles = 0

        handle_start = instance.data.get("handleStart")
        if handle_start is None:
            handle_start = context.data.get("handleStart")
            if handle_start is None:
                handle_start = handles

        handle_end = instance.data.get("handleEnd")
        if handle_end is None:
            handle_end = context.data.get("handleEnd")
            if handle_end is None:
                handle_end = handles

        frame_start_handle = frame_start - handle_start
        frame_end_handle = frame_end + handle_end

        burnin_data = copy.deepcopy(instance.data["anatomyData"])

        if "slate.farm" in instance.data["families"]:
            frame_start_handle += 1

        burnin_data.update({
            "version": int(version),
            "comment": context.data.get("comment") or ""
        })

        intent_label = context.data.get("intent")
        if intent_label and isinstance(intent_label, dict):
            intent_label = intent_label.get("label")

        if intent_label:
            burnin_data["intent"] = intent_label

        temp_data = {
            "frame_start": frame_start,
            "frame_end": frame_end,
            "frame_start_handle": frame_start_handle,
            "frame_end_handle": frame_end_handle
        }

        self.log.debug(
            "Basic burnin_data: {}".format(json.dumps(burnin_data, indent=4))
        )

        return burnin_data, temp_data

    def repres_is_valid(self, repre):
        """Validation if representaion should be processed.

        Args:
            repre (dict): Representation which should be checked.

        Returns:
            bool: False if can't be processed else True.
        """

        if "burnin" not in (repre.get("tags") or []):
            self.log.info((
                "Representation \"{}\" don't have \"burnin\" tag. Skipped."
            ).format(repre["name"]))
            return False
        return True

    def filter_burnins_by_tags(self, burnin_defs, tags):
        """Filter burnin definitions by entered representation tags.

        Burnin definitions without tags filter are marked as valid.

        Args:
            outputs (list): Contain list of burnin definitions from presets.
            tags (list): Tags of processed representation.

        Returns:
            list: Containg all burnin definitions matching entered tags.
        """
        filtered_burnins = {}
        repre_tags_low = [tag.lower() for tag in tags]
        for filename_suffix, burnin_def in burnin_defs.items():
            valid = True
            output_filters = burnin_def.get("filter")
            if output_filters:
                # Check tag filters
                tag_filters = output_filters.get("tags")
                if tag_filters:
                    tag_filters_low = [tag.lower() for tag in tag_filters]
                    valid = False
                    for tag in repre_tags_low:
                        if tag in tag_filters_low:
                            valid = True
                            break

                    if not valid:
                        continue

            if valid:
                filtered_burnins[filename_suffix] = burnin_def

        return filtered_burnins

    def input_output_paths(self, new_repre, temp_data, filename_suffix):
        """Prepare input and output paths for representation.

        Store data to `temp_data` for keys "full_input_path" which is full path
        to source files optionally with sequence formatting,
        "full_output_path" full path to otput with optionally with sequence
        formatting, "full_input_paths" list of all source files which will be
        deleted when burnin script ends, "repre_files" list of output
        filenames.

        Args:
            new_repre (dict): Currently processed new representation.
            temp_data (dict): Temp data of representation process.
            filename_suffix (str): Filename suffix added to inputl filename.

        Returns:
            None: This is processing method.
        """
        # TODO we should find better way to know if input is sequence
        is_sequence = (
            "sequence" in new_repre["tags"]
            and isinstance(new_repre["files"], (tuple, list))
        )
        if is_sequence:
            input_filename = new_repre["sequence_file"]
        else:
            input_filename = new_repre["files"]

        filepart_start, ext = os.path.splitext(input_filename)
        dir_path, basename = os.path.split(filepart_start)

        if is_sequence:
            # NOTE modified to keep name when multiple dots are in name
            basename_parts = basename.split(".")
            frame_part = basename_parts.pop(-1)

            basename_start = ".".join(basename_parts) + filename_suffix
            new_basename = ".".join((basename_start, frame_part))
            output_filename = new_basename + ext

        else:
            output_filename = basename + filename_suffix + ext

        if dir_path:
            output_filename = os.path.join(dir_path, output_filename)

        stagingdir = new_repre["stagingDir"]
        full_input_path = os.path.join(
            os.path.normpath(stagingdir), input_filename
        ).replace("\\", "/")
        full_output_path = os.path.join(
            os.path.normpath(stagingdir), output_filename
        ).replace("\\", "/")

        temp_data["full_input_path"] = full_input_path
        temp_data["full_output_path"] = full_output_path

        self.log.debug("full_input_path: {}".format(full_input_path))
        self.log.debug("full_output_path: {}".format(full_output_path))

        # Prepare full paths to input files and filenames for reprensetation
        full_input_paths = []
        if is_sequence:
            repre_files = []
            for frame_index in range(1, temp_data["duration"] + 1):
                repre_files.append(output_filename % frame_index)
                full_input_paths.append(full_input_path % frame_index)

        else:
            full_input_paths.append(full_input_path)
            repre_files = output_filename

        temp_data["full_input_paths"] = full_input_paths
        new_repre["files"] = repre_files

    def prepare_repre_data(self, instance, repre, burnin_data, temp_data):
        """Prepare data for representation.

        Args:
            instance (Instance): Currently processed Instance.
            repre (dict): Currently processed representation.
            burnin_data (dict): Copy of basic burnin data based on instance
                data.
            temp_data (dict): Copy of basic temp data
        """
        # Add representation name to burnin data
        burnin_data["representation"] = repre["name"]

        # no handles switch from profile tags
        if "no-handles" in repre["tags"]:
            burnin_frame_start = temp_data["frame_start"]
            burnin_frame_end = temp_data["frame_end"]

        else:
            burnin_frame_start = temp_data["frame_start_handle"]
            burnin_frame_end = temp_data["frame_end_handle"]

        burnin_duration = burnin_frame_end - burnin_frame_start + 1

        burnin_data.update({
            "frame_start": burnin_frame_start,
            "frame_end": burnin_frame_end,
            "duration": burnin_duration,
        })
        temp_data["duration"] = burnin_duration

        # Add values for slate frames
        burnin_slate_frame_start = burnin_frame_start

        # Move frame start by 1 frame when slate is used.
        if (
            "slate" in instance.data["families"]
            and "slate-frame" in repre["tags"]
        ):
            burnin_slate_frame_start -= 1

        self.log.debug("burnin_slate_frame_start: {}".format(
            burnin_slate_frame_start
        ))

        burnin_data.update({
            "slate_frame_start": burnin_slate_frame_start,
            "slate_frame_end": burnin_frame_end,
            "slate_duration": (
                burnin_frame_end - burnin_slate_frame_start + 1
            )
        })

    def find_matching_profile(self, host_name, task_name, family):
        """ Filter profiles by Host name, Task name and main Family.

        Filtering keys are "hosts" (list), "tasks" (list), "families" (list).
        If key is not find or is empty than it's expected to match.

        Args:
            profiles (list): Profiles definition from presets.
            host_name (str): Current running host name.
            task_name (str): Current context task name.
            family (str): Main family of current Instance.

        Returns:
            dict/None: Return most matching profile or None if none of profiles
                match at least one criteria.
        """

        matching_profiles = None
        highest_points = -1
        for profile in self.profiles or tuple():
            profile_points = 0
            profile_value = []

            # Host filtering
            host_names = profile.get("hosts")
            match = self.validate_value_by_regexes(host_name, host_names)
            if match == -1:
                continue
            profile_points += match
            profile_value.append(bool(match))

            # Task filtering
            task_names = profile.get("tasks")
            match = self.validate_value_by_regexes(task_name, task_names)
            if match == -1:
                continue
            profile_points += match
            profile_value.append(bool(match))

            # Family filtering
            families = profile.get("families")
            match = self.validate_value_by_regexes(family, families)
            if match == -1:
                continue
            profile_points += match
            profile_value.append(bool(match))

            if profile_points > highest_points:
                matching_profiles = []
                highest_points = profile_points

            if profile_points == highest_points:
                profile["__value__"] = profile_value
                matching_profiles.append(profile)

        if not matching_profiles:
            return

        if len(matching_profiles) == 1:
            return matching_profiles[0]

        return self.profile_exclusion(matching_profiles)

    def profile_exclusion(self, matching_profiles):
        """Find out most matching profile by host, task and family match.

        Profiles are selectivelly filtered. Each profile should have
        "__value__" key with list of booleans. Each boolean represents
        existence of filter for specific key (host, taks, family).
        Profiles are looped in sequence. In each sequence are split into
        true_list and false_list. For next sequence loop are used profiles in
        true_list if there are any profiles else false_list is used.

        Filtering ends when only one profile left in true_list. Or when all
        existence booleans loops passed, in that case first profile from left
        profiles is returned.

        Args:
            matching_profiles (list): Profiles with same values.

        Returns:
            dict: Most matching profile.
        """
        self.log.info(
            "Search for first most matching profile in match order:"
            " Host name -> Task name -> Family."
        )
        # Filter all profiles with highest points value. First filter profiles
        # with matching host if there are any then filter profiles by task
        # name if there are any and lastly filter by family. Else use first in
        # list.
        idx = 0
        final_profile = None
        while True:
            profiles_true = []
            profiles_false = []
            for profile in matching_profiles:
                value = profile["__value__"]
                # Just use first profile when idx is greater than values.
                if not idx < len(value):
                    final_profile = profile
                    break

                if value[idx]:
                    profiles_true.append(profile)
                else:
                    profiles_false.append(profile)

            if final_profile is not None:
                break

            if profiles_true:
                matching_profiles = profiles_true
            else:
                matching_profiles = profiles_false

            if len(matching_profiles) == 1:
                final_profile = matching_profiles[0]
                break
            idx += 1

        final_profile.pop("__value__")
        return final_profile

    def filter_burnins_by_families(self, profile, instance):
        """Filter outputs that are not supported for instance families.

        Output definitions without families filter are marked as valid.

        Args:
            profile (dict): Profile from presets matching current context.
            families (list): All families of current instance.

        Returns:
            list: Containg all output definitions matching entered families.
        """
        filtered_burnin_defs = {}

        burnin_defs = profile.get("burnins")
        if not burnin_defs:
            return filtered_burnin_defs

        # Prepare families
        families = self.families_from_instance(instance)
        families = [family.lower() for family in families]

        for filename_suffix, burnin_def in burnin_defs.items():
            burnin_filter = burnin_def.get("filter")
            # When filters not set then skip filtering process
            if burnin_filter:
                families_filters = burnin_filter.get("families")
                if not self.families_filter_validation(
                    families, families_filters
                ):
                    continue

            filtered_burnin_defs[filename_suffix] = burnin_def
        return filtered_burnin_defs

    def families_filter_validation(self, families, output_families_filter):
        """Determines if entered families intersect with families filters.

        All family values are lowered to avoid unexpected results.
        """
        if not output_families_filter:
            return True

        for family_filter in output_families_filter:
            if not family_filter:
                continue

            if not isinstance(family_filter, (list, tuple)):
                if family_filter.lower() not in families:
                    continue
                return True

            valid = True
            for family in family_filter:
                if family.lower() not in families:
                    valid = False
                    break

            if valid:
                return True
        return False

    def compile_list_of_regexes(self, in_list):
        """Convert strings in entered list to compiled regex objects."""
        regexes = []
        if not in_list:
            return regexes

        for item in in_list:
            if not item:
                continue

            try:
                regexes.append(re.compile(item))
            except TypeError:
                self.log.warning((
                    "Invalid type \"{}\" value \"{}\"."
                    " Expected string based object. Skipping."
                ).format(str(type(item)), str(item)))

        return regexes

    def validate_value_by_regexes(self, value, in_list):
        """Validates in any regexe from list match entered value.

        Args:
            in_list (list): List with regexes.
            value (str): String where regexes is checked.

        Returns:
            int: Returns `0` when list is not set or is empty. Returns `1` when
                any regex match value and returns `-1` when none of regexes
                match value entered.
        """
        if not in_list:
            return 0

        output = -1
        regexes = self.compile_list_of_regexes(in_list)
        for regex in regexes:
            if re.match(regex, value):
                output = 1
                break
        return output

    def main_family_from_instance(self, instance):
        """Returns main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family

    def families_from_instance(self, instance):
        """Returns all families of entered instance."""
        families = []
        family = instance.data.get("family")
        if family:
            families.append(family)

        for family in (instance.data.get("families") or tuple()):
            if family not in families:
                families.append(family)
        return families

    def burnin_script_path(self):
        """Returns path to python script for burnin processing."""
        # TODO maybe convert to Plugin's attribute
        # Get script path.
        module_path = os.environ["PYPE_MODULE_ROOT"]

        # There can be multiple paths in PYPE_MODULE_ROOT, in which case
        # we just take first one.
        if os.pathsep in module_path:
            module_path = module_path.split(os.pathsep)[0]

        scriptpath = os.path.normpath(
            os.path.join(
                module_path,
                "pype",
                "scripts",
                "otio_burnin.py"
            )
        )

        self.log.debug("scriptpath: {}".format(scriptpath))

        return scriptpath

    def python_executable_path(self):
        """Returns path to Python 3 executable."""
        # TODO maybe convert to Plugin's attribute
        # Get executable.
        executable = os.getenv("PYPE_PYTHON_EXE")

        # There can be multiple paths in PYPE_PYTHON_EXE, in which case
        # we just take first one.
        if os.pathsep in executable:
            executable = executable.split(os.pathsep)[0]

        self.log.debug("executable: {}".format(executable))
        return executable

    def legacy_process(self, instance):
        self.log.warning("Legacy burnin presets are used.")

        context_data = instance.context.data

        version = instance.data.get(
            'version', instance.context.data.get('version'))
        frame_start = int(instance.data.get("frameStart") or 0)
        frame_end = int(instance.data.get("frameEnd") or 1)
        handle_start = instance.data.get("handleStart",
                                         context_data.get("handleStart"))
        handle_end = instance.data.get("handleEnd",
                                       context_data.get("handleEnd"))

        frame_start_handle = frame_start - handle_start
        frame_end_handle = frame_end + handle_end
        duration = frame_end_handle - frame_start_handle + 1

        prep_data = copy.deepcopy(instance.data["anatomyData"])

        if "slate.farm" in instance.data["families"]:
            frame_start_handle += 1
            duration -= 1

        prep_data.update({
            "frame_start": frame_start_handle,
            "frame_end": frame_end_handle,
            "duration": duration,
            "version": int(version),
            "comment": instance.context.data.get("comment", "")
        })

        intent_label = instance.context.data.get("intent")
        if intent_label and isinstance(intent_label, dict):
            intent_label = intent_label.get("label")

        if intent_label:
            prep_data["intent"] = intent_label

        # get anatomy project
        anatomy = instance.context.data['anatomy']

        self.log.debug("__ prep_data: {}".format(prep_data))
        for i, repre in enumerate(instance.data["representations"]):
            self.log.debug("__ i: `{}`, repre: `{}`".format(i, repre))

            if instance.data.get("multipartExr") is True:
                # ffmpeg doesn't support multipart exrs
                continue

            if "burnin" not in repre.get("tags", []):
                continue

            is_sequence = "sequence" in repre.get("tags", [])

            # no handles switch from profile tags
            no_handles = "no-handles" in repre.get("tags", [])

            stagingdir = repre["stagingDir"]
            filename = "{0}".format(repre["files"])

            if is_sequence:
                filename = repre["sequence_file"]

            name = "_burnin"
            ext = os.path.splitext(filename)[1]
            movieFileBurnin = filename.replace(ext, "") + name + ext

            if is_sequence:
                fn_splt = filename.split(".")
                movieFileBurnin = ".".join(
                    ((fn_splt[0] + name), fn_splt[-2], fn_splt[-1]))

            self.log.debug("__ movieFileBurnin: `{}`".format(movieFileBurnin))

            full_movie_path = os.path.join(
                os.path.normpath(stagingdir), filename)
            full_burnin_path = os.path.join(
                os.path.normpath(stagingdir), movieFileBurnin)

            self.log.debug("__ full_movie_path: {}".format(full_movie_path))
            self.log.debug("__ full_burnin_path: {}".format(full_burnin_path))

            # create copy of prep_data for anatomy formatting
            _prep_data = copy.deepcopy(prep_data)
            _prep_data["representation"] = repre["name"]
            filled_anatomy = anatomy.format_all(_prep_data)
            _prep_data["anatomy"] = filled_anatomy.get_solved()

            # copy frame range variables
            frame_start_cp = frame_start_handle
            frame_end_cp = frame_end_handle
            duration_cp = duration

            if no_handles:
                frame_start_cp = frame_start
                frame_end_cp = frame_end
                duration_cp = frame_end_cp - frame_start_cp + 1
                _prep_data.update({
                    "frame_start": frame_start_cp,
                    "frame_end": frame_end_cp,
                    "duration": duration_cp,
                })

            # dealing with slates
            slate_frame_start = frame_start_cp
            slate_frame_end = frame_end_cp
            slate_duration = duration_cp

            # exception for slate workflow
            if "slate" in instance.data["families"]:
                if "slate-frame" in repre.get("tags", []):
                    slate_frame_start = frame_start_cp - 1
                    slate_frame_end = frame_end_cp
                    slate_duration = duration_cp + 1

            self.log.debug("__1 slate_frame_start: {}".format(
                slate_frame_start))

            _prep_data.update({
                "slate_frame_start": slate_frame_start,
                "slate_frame_end": slate_frame_end,
                "slate_duration": slate_duration
            })

            burnin_data = {
                "input": full_movie_path.replace("\\", "/"),
                "codec": repre.get("codec", []),
                "output": full_burnin_path.replace("\\", "/"),
                "burnin_data": _prep_data
            }

            self.log.debug("__ burnin_data2: {}".format(burnin_data))

            json_data = json.dumps(burnin_data)

            # Get script path.
            module_path = os.environ['PYPE_MODULE_ROOT']

            # There can be multiple paths in PYPE_MODULE_ROOT, in which case
            # we just take first one.
            if os.pathsep in module_path:
                module_path = module_path.split(os.pathsep)[0]

            scriptpath = os.path.normpath(
                os.path.join(
                    module_path,
                    "pype",
                    "scripts",
                    "otio_burnin.py"
                )
            )

            self.log.debug("__ scriptpath: {}".format(scriptpath))

            # Get executable.
            executable = os.getenv("PYPE_PYTHON_EXE")

            # There can be multiple paths in PYPE_PYTHON_EXE, in which case
            # we just take first one.
            if os.pathsep in executable:
                executable = executable.split(os.pathsep)[0]

            self.log.debug("__ EXE: {}".format(executable))

            args = [executable, scriptpath, json_data]
            self.log.debug("Executing: {}".format(args))
            output = pype.api.subprocess(args, shell=True)
            self.log.debug("Output: {}".format(output))

            repre_update = {
                "files": movieFileBurnin,
                "name": repre["name"],
                "tags": [x for x in repre["tags"] if x != "delete"]
            }

            if is_sequence:
                burnin_seq_files = list()
                for frame_index in range(_prep_data["duration"] + 1):
                    if frame_index == 0:
                        continue
                    burnin_seq_files.append(movieFileBurnin % frame_index)
                repre_update.update({
                    "files": burnin_seq_files
                })

            instance.data["representations"][i].update(repre_update)

            # removing the source mov file
            if is_sequence:
                for frame_index in range(_prep_data["duration"] + 1):
                    if frame_index == 0:
                        continue
                    rm_file = full_movie_path % frame_index
                    os.remove(rm_file)
                    self.log.debug("Removed: `{}`".format(rm_file))
            else:
                os.remove(full_movie_path)
                self.log.debug("Removed: `{}`".format(full_movie_path))

        # Remove any representations tagged for deletion.
        for repre in instance.data["representations"]:
            if "delete" in repre.get("tags", []):
                self.log.debug("Removing representation: {}".format(repre))
                instance.data["representations"].remove(repre)

        self.log.debug(instance.data["representations"])
