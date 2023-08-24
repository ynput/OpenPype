import os
from pprint import pformat
import tempfile
from pathlib import Path

import pyblish.api
from openpype.pipeline import publish


class CollectSettingsSimpleInstances(pyblish.api.InstancePlugin,
                                     publish.PrepRepresentationPluginMixin,
                                     publish.ColormanagedPyblishPluginMixin):
    """Collect data for instances created by settings creators.

    Plugin create representations for simple instances based
    on 'representation_files' attribute stored on instance data.

    There is also possibility to have reviewable representation which can be
    stored under 'reviewable' attribute stored on instance data. If there was
    already created representation with the same files as 'reviewable' contains

    Representations can be marked for review and in that case is also added
    'review' family to instance families. For review can be marked only one
    representation so **first** representation that has extension available
    in '_review_extensions' is used for review.

    For instance 'source' is used path from last representation created
    from 'representation_files'.

    Set staging directory on instance. That is probably never used because
    each created representation has it's own staging dir.
    """

    label = "Collect Settings Simple Instances"
    order = pyblish.api.CollectorOrder - 0.49

    hosts = ["traypublisher"]

    def process(self, instance):
        if not instance.data.get("settings_creator"):
            return

        context = instance.context
        instance_label = instance.data["name"]
        family = instance.data["family"]

        # Create instance's staging dir in temp
        tmp_folder = tempfile.mkdtemp(prefix="traypublisher_")
        instance.data["stagingDir"] = tmp_folder
        instance.context.data["cleanupFullPaths"].append(tmp_folder)

        self.log.debug((
            "Created temp staging directory for instance {}. {}"
        ).format(instance_label, tmp_folder))

        creator_attributes = instance.data["creator_attributes"]
        publish_target = creator_attributes["publish_target"]
        review_file_item = creator_attributes["reviewable"]
        review_filenames = review_file_item.get("filenames")

        # make instance reviewable if reviewable attribute is set
        if review_filenames:
            instance.data["review"] = True
            instance.data["families"].append("review")

        self._fill_version(instance, instance_label)

        # prep all representation files for processing
        filepath_items = creator_attributes["representation_files"]
        if not isinstance(filepath_items, list):
            filepath_items = [filepath_items]

        # also add reviewable item to list of items to process
        if review_filenames:
            filepath_items.append(review_file_item)

        representation_files = self.get_processing_file_data(
            instance, filepath_items)

        for file_path, file_data in representation_files.items():
            # making sure file extension is publishable over farm
            file_ext = os.path.splitext(file_path)[-1].lower().lstrip(".")
            if file_ext not in self.pixel_ext:
                # allow farm publishing only for pixel type data
                publish_target = "local"

            frame_start, frame_end = file_data["framerange"]

            file_paths = self.prepare_collection_of_file_paths(
                file_path, frame_start, frame_end
            )

            representation = self.prepare_representation(
                instance, file_paths, frame_start, frame_end,
                reviewable=("reviewable" in file_data)
            )

            if publish_target == "farm":
                # farm publish needs to have output dir set
                output_dir = os.path.dirname(file_path)
                instance.data["outputDir"] = output_dir
                context.data["currentFile"] = file_path

                self.make_farm_publishing_representation(
                    representation
                )

            # QUESTION: perhaps we should do this in other plugin
            self.set_representation_colorspace(
                representation, context
            )
            instance.data["representations"].append(representation)

        # Add render target specific data
        # NOTE: need to be done after review family is added
        if publish_target == "farm":
            self.add_farm_instance_data(instance)
            # add farm suffixed family to families
            instance.data["families"].append("{}.farm".format(family))

        self.log.debug(
            (
                "Created Simple Settings instance \"{}\""
                " with {} representations"
            ).format(
                instance_label,
                len(instance.data["representations"])
            )
        )
        self.log.debug(pformat(instance.data))

    def get_processing_file_data(self, instance, filepath_items):
        """Get data for processing files.

        Args:
            filepath_items (List[Dict[str, Any]]): List of items with
                information about files.
        Returns:
            List[Dict[str, Any]]: List of items with data for processing files.
        """
        representation_files = {}
        source_filepaths = []
        for filepath_item in filepath_items:
            # Skip if filepath item does not have filenames
            if not filepath_item["filenames"]:
                continue

            filepaths = {
                os.path.join(filepath_item["directory"], filename)
                for filename in filepath_item["filenames"]
            }

            # add it to source filepaths
            # for later validation of existence
            source_filepaths.extend(filepaths)

            file_path = self.get_single_filepath_from_list_of_files(
                filepaths)
            frame_start, frame_end = self.get_frame_range_from_list_of_files(
                filepaths)
            processing_file_data = {
                file_path: {
                    "framerange": (frame_start, frame_end)
                }
            }

            # make sure there is no duplicity for case reviewable is duplicated
            if file_path in representation_files:
                # update the data to be reviewable
                representation_files[file_path]["reviewable"] = True
            else:
                representation_files.update(processing_file_data)

        # store source filepaths on instance
        source_filepaths = sorted(list(set(source_filepaths)))

        # NOTE: we need to make sure there are no duplicities
        instance.data.setdefault(
            "sourceFilepaths", source_filepaths
        )
        # NOTE: Missing filepaths should not cause crashes (at least not here)
        # - if filepaths are required they should crash on validation
        if source_filepaths:
            # NOTE: Original basename is not handling sequences
            # - we should maybe not fill the key when sequence is used?
            origin_basename = Path(source_filepaths[0]).stem
            instance.data["originalBasename"] = origin_basename

        if not instance.data.get("thumbnailSource"):
            instance.data["thumbnailSource"] = source_filepaths[0]

        return representation_files

    def _fill_version(self, instance, instance_label):
        """Fill instance version under which will be instance integrated.

        Instance must have set 'use_next_version' to 'False'
        and 'version_to_use' to version to use.

        Args:
            instance (pyblish.api.Instance): Instance to fill version for.
            instance_label (str): Label of instance to fill version for.
        """

        creator_attributes = instance.data["creator_attributes"]
        use_next_version = creator_attributes.get("use_next_version", True)
        # If 'version_to_use' is '0' it means that next version should be used
        version_to_use = creator_attributes.get("version_to_use", 0)
        instance.context.data["version"] = version_to_use

        if use_next_version or not version_to_use:
            return
        instance.data["version"] = version_to_use
        self.log.debug(
            "Version for instance \"{}\" was set to \"{}\"".format(
                instance_label, version_to_use))
