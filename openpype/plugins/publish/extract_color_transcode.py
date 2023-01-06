import os
import copy

import pyblish.api

from openpype.pipeline import publish
from openpype.lib import (

    is_oiio_supported,
)

from openpype.lib.transcoding import (
    convert_colorspace_for_input_paths,
    get_transcode_temp_directory,
)

from openpype.lib.profiles_filtering import filter_profiles


class ExtractColorTranscode(publish.Extractor):
    """
    Extractor to convert colors from one colorspace to different.

    Expects "colorspaceData" on representation. This dictionary is collected
    previously and denotes that representation files should be converted.
    This dict contains source colorspace information, collected by hosts.

    Target colorspace is selected by profiles in the Settings, based on:
    - families
    - host
    - task types
    - task names
    - subset names
    """

    label = "Transcode color spaces"
    order = pyblish.api.ExtractorOrder + 0.019

    optional = True

    # Supported extensions
    supported_exts = ["exr", "jpg", "jpeg", "png", "dpx"]

    # Configurable by Settings
    profiles = None
    options = None

    def process(self, instance):
        if not self.profiles:
            self.log.debug("No profiles present for color transcode")
            return

        if "representations" not in instance.data:
            self.log.debug("No representations, skipping.")
            return

        if not is_oiio_supported():
            self.log.warning("OIIO not supported, no transcoding possible.")
            return

        profile = self._get_profile(instance)
        if not profile:
            return

        repres = instance.data.get("representations") or []
        for idx, repre in enumerate(list(repres)):
            self.log.debug("repre ({}): `{}`".format(idx + 1, repre["name"]))
            if not self._repre_is_valid(repre):
                continue

            colorspace_data = repre["colorspaceData"]
            source_color_space = colorspace_data["colorspace"]
            config_path = colorspace_data.get("configData", {}).get("path")
            if not os.path.exists(config_path):
                self.log.warning("Config file doesn't exist, skipping")
                continue

            repre = self._handle_original_repre(repre, profile)

            for _, output_def in profile.get("outputs", {}).items():
                new_repre = copy.deepcopy(repre)

                new_staging_dir = get_transcode_temp_directory()
                original_staging_dir = new_repre["stagingDir"]
                new_repre["stagingDir"] = new_staging_dir
                files_to_convert = new_repre["files"]
                if not isinstance(files_to_convert, list):
                    files_to_convert = [files_to_convert]

                files_to_delete = copy.deepcopy(files_to_convert)

                output_extension = output_def["output_extension"]
                files_to_convert = self._rename_output_files(files_to_convert,
                                                             output_extension)

                files_to_convert = [os.path.join(original_staging_dir, path)
                                    for path in files_to_convert]

                target_colorspace = output_def["output_colorspace"]
                if not target_colorspace:
                    raise RuntimeError("Target colorspace must be set")

                convert_colorspace_for_input_paths(
                    files_to_convert,
                    new_staging_dir,
                    config_path,
                    source_color_space,
                    target_colorspace,
                    self.log
                )

                instance.context.data["cleanupFullPaths"].extend(
                    files_to_delete)

                custom_tags = output_def.get("custom_tags")
                if custom_tags:
                    if not new_repre.get("custom_tags"):
                        new_repre["custom_tags"] = []
                    new_repre["custom_tags"].extend(custom_tags)

                # Add additional tags from output definition to representation
                for tag in output_def["tags"]:
                    if tag not in new_repre["tags"]:
                        new_repre["tags"].append(tag)

                instance.data["representations"].append(new_repre)

    def _rename_output_files(self, files_to_convert, output_extension):
        """Change extension of converted files."""
        if output_extension:
            output_extension = output_extension.replace('.', '')
            renamed_files = []
            for file_name in files_to_convert:
                file_name, _ = os.path.splitext(file_name)
                new_file_name = '{}.{}'.format(file_name,
                                               output_extension)
                renamed_files.append(new_file_name)
            files_to_convert = renamed_files
        return files_to_convert

    def _get_profile(self, instance):
        """Returns profile if and how repre should be color transcoded."""
        host_name = instance.context.data["hostName"]
        family = instance.data["family"]
        task_data = instance.data["anatomyData"].get("task", {})
        task_name = task_data.get("name")
        task_type = task_data.get("type")
        subset = instance.data["subset"]
        filtering_criteria = {
            "hosts": host_name,
            "families": family,
            "task_names": task_name,
            "task_types": task_type,
            "subset": subset
        }
        profile = filter_profiles(self.profiles, filtering_criteria,
                                  logger=self.log)

        if not profile:
            self.log.info((
                  "Skipped instance. None of profiles in presets are for"
                  " Host: \"{}\" | Families: \"{}\" | Task \"{}\""
                  " | Task type \"{}\" | Subset \"{}\" "
              ).format(host_name, family, task_name, task_type, subset))

        self.log.debug("profile: {}".format(profile))
        return profile

    def _repre_is_valid(self, repre):
        """Validation if representation should be processed.

        Args:
            repre (dict): Representation which should be checked.

        Returns:
            bool: False if can't be processed else True.
        """

        if repre.get("ext") not in self.supported_exts:
            self.log.debug((
                    "Representation \"{}\" of unsupported extension. Skipped."
            ).format(repre["name"]))
            return False

        if not repre.get("files"):
            self.log.debug((
                "Representation \"{}\" have empty files. Skipped."
            ).format(repre["name"]))
            return False

        if not repre.get("colorspaceData"):
            self.log.debug("Repre has no colorspace data. Skipped.")
            return False

        return True

    def _handle_original_repre(self, repre, profile):
        delete_original = profile["delete_original"]

        if delete_original:
            if not repre.get("tags"):
                repre["tags"] = []

            if "review" in repre["tags"]:
                repre["tags"].remove("review")
            if "delete" not in repre["tags"]:
                repre["tags"].append("delete")

        return repre
