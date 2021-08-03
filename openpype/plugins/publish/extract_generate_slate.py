import os
import re
import json
import pyblish
import platform

from openpype.scripts import slates

# class ExtractGenerateSlate(openpype.api.Extractor):
class ExtractGenerateSlate(pyblish.api.InstancePlugin):
    """ Extractor for dynamically generating slates.

    Slates are generated from previous representation file
    """

    label = "Extract generated slates"
    order = pyblish.api.CollectorOrder + 0.495
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
        # TODO get these data from context
        # Store anatomy data
        project_doc = instance.data["projectEntity"]
        anatomy_data = instance.data["anatomyData"]
        version_number = instance.data["version"]

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

        self.log.info(self.options)
        # TODO: how to get following data from context
        # TODO: how to define keys matching slates template keys
        # TODO: where to get notes data > last ftrack comments which is addressed by this submission
        # TODO: how to address vendor parent (our client's project client) logo path issue
        # TODO: vendor can be taken from `settings.system.general.studio_name`
        example_fill_data = {
            "shot": "106_V12_010",
            "version": "V007",
            "length": 187,
            "date": "11/02/2021",
            "artist": "John Murdoch",
            "notes": (
                "Lorem ipsum dolor sit amet, consectetuer adipiscing elit."
                " Aenean commodo ligula eget dolor. Aenean massa."
                " Cum sociis natoque penatibus et magnis dis parturient montes,"
                " nascetur ridiculus mus. Donec quam felis, ultricies nec,"
                " pellentesque eu, pretium quis, sem. Nulla consequat massa quis"
                " enim. Donec pede justo, fringilla vel,"
                " aliquet nec, vulputate eget, arcu."
            ),
            "thumbnail_path": "C:/CODE/_PYPE_testing/slates_testing/thumbnail.png",
            "logo": "C:/CODE/_PYPE_testing/slates_testing/logo.jpg",
            "vendor": "VENDOR"
        }

        # TODO: send font patch into slates generator's font factory
        # TODO: form output slate path into temp dir
        # TODO: convert input video file to thumbnail image > ffmpeg
        # TODO: get resolution of an input image
        fonts_dir = self.options.get("font_filepath", {}).get(
            platform.system().lower())
        self.log.info(fonts_dir)
        slates.api.slate_generator(
            example_fill_data, json.loads(profile["template"]),
            output_path="C:/CODE/_PYPE_testing/slates_testing/slate.png",
            width=1920, height=1080, fonts_dir=fonts_dir
        )

        # TODO: connect generated slate image to input video
        # TODO: remove previous video and replace representation with new data

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
            self.log.info("> host match: {}".format(match))
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
        """Return main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family
