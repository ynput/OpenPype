import os
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

    # Configurable by Settings
    profiles = None
    options = None

    def process(self, instance):
        if not self.profiles:
            self.log.warning("No profiles present for create burnin")
            return

        if "representations" not in instance.data:
            self.log.warning("No representations, skipping.")
            return

        if not is_oiio_supported():
            self.log.warning("OIIO not supported, no transcoding possible.")
            return

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
            return

        self.log.debug("profile: {}".format(profile))

        target_colorspace = profile["output_colorspace"]
        if not target_colorspace:
            raise RuntimeError("Target colorspace must be set")
        custom_tags = profile["custom_tags"]

        repres = instance.data.get("representations") or []
        for idx, repre in enumerate(repres):
            self.log.debug("repre ({}): `{}`".format(idx + 1, repre["name"]))
            # if not self.repre_is_valid(repre):
            #     continue

            colorspace_data = repre.get("colorspaceData")
            if not colorspace_data:
                # TODO get_colorspace ??
                self.log.warning("Repre has not colorspace data, skipping")
                continue
            source_color_space = colorspace_data["colorspace"]
            config_path = colorspace_data.get("configData", {}).get("path")
            if not os.path.exists(config_path):
                self.log.warning("Config file doesn't exist, skipping")
                continue

            new_staging_dir = get_transcode_temp_directory()
            original_staging_dir = repre["stagingDir"]
            repre["stagingDir"] = new_staging_dir
            files_to_convert = repre["files"]
            if not isinstance(files_to_convert, list):
                files_to_convert = [files_to_convert]
            files_to_convert = [os.path.join(original_staging_dir, path)
                                for path in files_to_convert]
            instance.context.data["cleanupFullPaths"].extend(files_to_convert)

            convert_colorspace_for_input_paths(
                files_to_convert,
                new_staging_dir,
                config_path,
                source_color_space,
                target_colorspace,
                self.log
            )

            if custom_tags:
                if not repre.get("custom_tags"):
                    repre["custom_tags"] = []
                repre["custom_tags"].extend(custom_tags)

    def repre_is_valid(self, repre):
        """Validation if representation should be processed.

        Args:
            repre (dict): Representation which should be checked.

        Returns:
            bool: False if can't be processed else True.
        """

        if "review" not in (repre.get("tags") or []):
            self.log.info((
                "Representation \"{}\" don't have \"review\" tag. Skipped."
            ).format(repre["name"]))
            return False

        if not repre.get("files"):
            self.log.warning((
                "Representation \"{}\" have empty files. Skipped."
            ).format(repre["name"]))
            return False
        return True
