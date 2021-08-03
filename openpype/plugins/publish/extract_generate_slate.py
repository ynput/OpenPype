import os
import re
import json
import pyblish
import platform
from pprint import pformat

from openpype.scripts import slates


# class ExtractGenerateSlate(openpype.api.Extractor):
class ExtractGenerateSlate(pyblish.api.InstancePlugin):
    """ Extractor for dynamically generating slates.

    Slates are generated from previous representation file
    """

    label = "Extract generated slates"
    order = pyblish.api.ValidatorOrder - 0.1
    # families = ["review"]
    hosts = [
        "nuke",
        "standalonepublisher"
    ]
    optional = True

    # Preset attributes
    profiles = None
    options = None

    def process(self, instance):
        formating_data = {}
        # get context data
        context = instance.context
        anatomy_data = instance.data["anatomyData"]

        # get filtering data
        host_name = anatomy_data["app"]
        task_name = anatomy_data["task"]
        family = self.main_family_from_instance(instance)
        families = instance.data["families"]

        # Find profile most matching current host, task and instance family
        profile = self.find_matching_profile(host_name, task_name,
                                             family, families)

        if not profile:
            self.log.info((
                "Skipped instance. None of profiles in presets are for "
                "Host: \"{}\" | Family: \"{}\" | "
                "Families: \"{}\" | Task \"{}\""
            ).format(host_name, family, families, task_name))
            return

        example_fill_data = {
            "thumbnail_path": "C:/CODE/_PYPE_testing/slates_testing/thumbnail.png"
        }

        # options
        fonts_dir = self.options.get("font_filepath", {}).get(
            platform.system().lower())
        fonts_dir = fonts_dir.format(**os.environ)

        images_dir_path = self.options.get("images_path", {}).get(
            platform.system().lower())
        images_dir_path = images_dir_path.format(**os.environ)

        formating_data.update(anatomy_data)
        formating_data.update(example_fill_data)
        formating_data.update({
            "comment": context.data.get("comment", ""),
            "studio_name": context.data[
                "system_settings"]["general"]["studio_name"],
            "studio_code": context.data[
                "system_settings"]["general"]["studio_code"],
            "images_dir_path": images_dir_path
        })

        formating_data.update(os.environ)

        self.log.debug(pformat(formating_data))

        # TODO: form output slate path into temp dir
        # TODO: convert input video file to thumbnail image > ffmpeg
        # TODO: get resolution of an input image
        slates.api.slate_generator(
            formating_data, json.loads(profile["template"]),
            output_path="C:/CODE/_PYPE_testing/slates_testing/slate.png",
            width=1920, height=1080, fonts_dir=fonts_dir
        )

        # TODO: connect generated slate image to input video
        # TODO: remove previous video and replace representation with new data

    def find_matching_profile(self, host_name, task_name, family, families):
        """ Filter profiles by Host name, Task name and main Family.

        Filtering keys are "hosts" (list), "tasks" (list), "families" (list).
        If key is not find or is empty than it's expected to match.

        Args:
            profiles (list): Profiles definition from presets.
            host_name (str): Current running host name.
            task_name (str): Current context task name.
            family (str): Main family of current Instance.
            families (list): list of additional families

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
            self.log.debug("> host match: {}".format(match))
            if match == -1:
                continue
            profile_points += match
            profile_value.append(bool(match))

            # Task filtering
            task_names = profile.get("tasks")
            match = self.validate_value_by_regexes(task_name, task_names)
            self.log.debug("> task match: {}".format(match))
            if match == -1:
                continue
            profile_points += match
            profile_value.append(bool(match))

            # Families filtering
            p_families = profile.get("families")
            match = self.validate_value_by_regexes(families, p_families)
            self.log.debug("> families match: {}".format(match))
            if match == -1:
                continue
            profile_points += match
            profile_value.append(bool(match))

            # Family filtering
            p_family = profile.get("family")
            match = self.validate_value_by_regexes(family, p_family)
            self.log.debug("> family match: {}".format(match))
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

        self.log.info("> matching_profiles: {}".format(matching_profiles))

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
        """Validate in any regexe from list match entered value.

        Args:
            in_list (list): List with regexes.
            value (str or list): String or list where regexes is checked.

        Returns:
            int: Returns `0` when list is not set or is empty. Returns `1` when
                any regex match value and returns `-1` when none of regexes
                match value entered.
        """
        if not in_list:
            return 0

        if isinstance(value, str):
            value = [value]

        output = -1
        regexes = self.compile_list_of_regexes(in_list)
        for regex in regexes:
            for val in value:
                self.log.debug(f"val: {val} | regex: {regex}")
                if re.match(regex, val):
                    output = 1
                    break
        return output

    def main_family_from_instance(self, instance):
        """Return main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family
