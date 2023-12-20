import os
import json
import copy
import pyblish.api

from openpype.pipeline.publish import get_publish_repre_path
from openpype.lib.openpype_version import get_openpype_version
from openpype.lib.transcoding import (
    get_ffprobe_streams,
    convert_ffprobe_fps_to_float,
)
from openpype.lib.profiles_filtering import filter_profiles
from openpype.lib.transcoding import VIDEO_EXTENSIONS


class IntegrateFtrackInstance(pyblish.api.InstancePlugin):
    """Collect ftrack component data (not integrate yet).

    Add ftrack component list to instance.
    """

    order = pyblish.api.IntegratorOrder + 0.48
    label = "Integrate Ftrack Component"
    families = ["ftrack"]

    metadata_keys_to_label = {
        "openpype_version": "OpenPype version",
        "frame_start": "Frame start",
        "frame_end": "Frame end",
        "duration": "Duration",
        "width": "Resolution width",
        "height": "Resolution height",
        "fps": "FPS",
        "codec": "Codec"
    }

    family_mapping = {
        "camera": "cam",
        "look": "look",
        "mayaAscii": "scene",
        "model": "geo",
        "rig": "rig",
        "setdress": "setdress",
        "pointcache": "cache",
        "render": "render",
        "prerender": "render",
        "render2d": "render",
        "nukescript": "comp",
        "write": "render",
        "review": "mov",
        "plate": "img",
        "audio": "audio",
        "workfile": "scene",
        "animation": "cache",
        "image": "img",
        "reference": "reference"
    }
    keep_first_subset_name_for_review = True
    upload_reviewable_with_origin_name = False
    asset_versions_status_profiles = []
    additional_metadata_keys = []

    def process(self, instance):
        # QUESTION: should this be operating even for `farm` target?
        self.log.debug("instance {}".format(instance))

        instance_repres = instance.data.get("representations")
        if not instance_repres:
            self.log.info((
                "Skipping instance. Does not have any representations {}"
            ).format(str(instance)))
            return

        instance_version = instance.data.get("version")
        if instance_version is None:
            raise ValueError("Instance version not set")

        version_number = int(instance_version)

        family = instance.data["family"]

        # Perform case-insensitive family mapping
        family_low = family.lower()
        asset_type = instance.data.get("ftrackFamily")
        if not asset_type:
            for map_family, map_value in self.family_mapping.items():
                if map_family.lower() == family_low:
                    asset_type = map_value
                    break

        if not asset_type:
            asset_type = "upload"

        self.log.debug(
            "Family: {}\nMapping: {}".format(family_low, self.family_mapping)
        )
        status_name = self._get_asset_version_status_name(instance)

        # Base of component item data
        # - create a copy of this object when want to use it
        base_component_item = {
            "assettype_data": {
                "short": asset_type,
            },
            "asset_data": {
                "name": instance.data["subset"],
            },
            "assetversion_data": {
                "version": version_number,
                "comment": instance.context.data.get("comment") or "",
                "status_name": status_name
            },
            "component_overwrite": False,
            # This can be change optionally
            "thumbnail": False,
            # These must be changed for each component
            "component_data": None,
            "component_path": None,
            "component_location": None,
            "component_location_name": None,
            "additional_data": {}
        }

        # Filter types of representations
        review_representations = []
        thumbnail_representations = []
        other_representations = []
        has_movie_review = False
        for repre in instance_repres:
            repre_tags = repre.get("tags") or []
            # exclude representations with are going to be published on farm
            if "publish_on_farm" in repre_tags:
                continue

            self.log.debug("Representation {}".format(repre))

            # include only thumbnail representations
            if repre.get("thumbnail") or "thumbnail" in repre_tags:
                thumbnail_representations.append(repre)

            # include only review representations
            elif "ftrackreview" in repre_tags:
                review_representations.append(repre)
                if self._is_repre_video(repre):
                    has_movie_review = True

            else:
                # include all other representations
                other_representations.append(repre)

        # Prepare ftrack locations
        unmanaged_location_name = "ftrack.unmanaged"
        ftrack_server_location_name = "ftrack.server"

        # check if any outputName keys are in review_representations
        # also check if any outputName keys are in thumbnail_representations
        synced_multiple_output_names = []
        for review_repre in review_representations:
            review_output_name = review_repre.get("outputName")
            if not review_output_name:
                continue
            for thumb_repre in thumbnail_representations:
                thumb_output_name = thumb_repre.get("outputName")
                if not thumb_output_name:
                    continue
                if (
                    thumb_output_name == review_output_name
                    # output name can be added also as tags during intermediate
                    # files creation
                    or thumb_output_name in review_repre.get("tags", [])
                ):
                    synced_multiple_output_names.append(
                        thumb_repre["outputName"])
        self.log.debug("Multiple output names: {}".format(
            synced_multiple_output_names
        ))
        multiple_synced_thumbnails = len(synced_multiple_output_names) > 1

        # Components data
        component_list = []
        thumbnail_data_items = []

        # Create thumbnail components
        for repre in thumbnail_representations:
            # get repre path from representation
            # and return published_path if available
            # the path is validated and if it does not exists it returns None
            repre_path = get_publish_repre_path(
                instance,
                repre,
                only_published=False
            )
            if not repre_path:
                self.log.warning(
                    "Published path is not set or source was removed."
                )
                continue

            # Create copy of base comp item and append it
            thumbnail_item = copy.deepcopy(base_component_item)
            thumbnail_item.update({
                "component_path": repre_path,
                "component_data": {
                    "name": (
                        "thumbnail" if review_representations
                        else "ftrackreview-image"
                    ),
                    "metadata": self._prepare_image_component_metadata(
                        repre,
                        repre_path
                    )
                },
                "thumbnail": True,
                "component_location_name": ftrack_server_location_name
            })

            # add thumbnail data to items for future synchronization
            current_item_data = {
                "sync_key": repre.get("outputName"),
                "representation": repre,
                "item": thumbnail_item
            }
            # Create copy of item before setting location
            if "delete" not in repre.get("tags", []):
                src_comp = self._create_src_component(
                    instance,
                    repre,
                    copy.deepcopy(thumbnail_item),
                    unmanaged_location_name
                )
                component_list.append(src_comp)

                current_item_data["src_component"] = src_comp

            # Add item to component list
            thumbnail_data_items.append(current_item_data)

        # Create review components
        # Change asset name of each new component for review
        multiple_reviewable = len(review_representations) > 1
        extended_asset_name = None
        for index, repre in enumerate(review_representations):
            if not self._is_repre_video(repre) and has_movie_review:
                self.log.debug("Movie repre has priority "
                               "from {}".format(repre))
                continue

            repre_path = get_publish_repre_path(instance, repre, False)
            if not repre_path:
                self.log.warning(
                    "Published path is not set and source was removed."
                )
                continue

            # Create copy of base comp item and append it
            review_item = copy.deepcopy(base_component_item)

            # get first or synchronize thumbnail item
            sync_thumbnail_item = None
            sync_thumbnail_item_src = None
            sync_thumbnail_data = self._get_matching_thumbnail_item(
                repre,
                thumbnail_data_items,
                multiple_synced_thumbnails
            )
            if sync_thumbnail_data:
                sync_thumbnail_item = sync_thumbnail_data.get("item")
                sync_thumbnail_item_src = sync_thumbnail_data.get(
                    "src_component")

            """
            Renaming asset name only to those components which are explicitly
            allowed in settings. Usually clients wanted to keep first component
            as untouched product name with version and any other assetVersion
            to be named with extended form. The renaming will only happen if
            there is more than one reviewable component and extended name is
            not empty.
            """
            extended_asset_name = self._make_extended_component_name(
                base_component_item, repre, index)

            if multiple_reviewable and extended_asset_name:
                review_item["asset_data"]["name"] = extended_asset_name
                # rename also thumbnail
                if sync_thumbnail_item:
                    sync_thumbnail_item["asset_data"]["name"] = (
                        extended_asset_name
                    )
                # rename also src_thumbnail
                if sync_thumbnail_item_src:
                    sync_thumbnail_item_src["asset_data"]["name"] = (
                        extended_asset_name
                    )

            # adding thumbnail component to component list
            if sync_thumbnail_item:
                component_list.append(copy.deepcopy(sync_thumbnail_item))
            if sync_thumbnail_item_src:
                component_list.append(copy.deepcopy(sync_thumbnail_item_src))

            # add metadata to review component
            if self._is_repre_video(repre):
                component_name = "ftrackreview-mp4"
                metadata = self._prepare_video_component_metadata(
                    instance, repre, repre_path, True
                )
            else:
                component_name = "ftrackreview-image"
                metadata = self._prepare_image_component_metadata(
                    repre, repre_path
                )
                review_item["thumbnail"] = True

            review_item.update({
                "component_path": repre_path,
                "component_data": {
                    "name": component_name,
                    "metadata": metadata
                },
                "component_location_name": ftrack_server_location_name
            })

            # Create copy of item before setting location
            if "delete" not in repre.get("tags", []):
                src_comp = self._create_src_component(
                    instance,
                    repre,
                    copy.deepcopy(review_item),
                    unmanaged_location_name
                )
                component_list.append(src_comp)

            # Add item to component list
            component_list.append(review_item)


            if self.upload_reviewable_with_origin_name:
                origin_name_component = copy.deepcopy(review_item)
                filename = os.path.basename(repre_path)
                origin_name_component["component_data"]["name"] = (
                    os.path.splitext(filename)[0]
                )
                component_list.append(origin_name_component)

        # Add others representations as component
        for repre in other_representations:
            published_path = get_publish_repre_path(instance, repre, True)
            if not published_path:
                continue
            # Create copy of base comp item and append it
            other_item = copy.deepcopy(base_component_item)

            # add extended name if any
            if (
                multiple_reviewable
                and not self.keep_first_subset_name_for_review
                and extended_asset_name
            ):
                other_item["asset_data"]["name"] = extended_asset_name

            other_item.update({
                "component_path": published_path,
                "component_data": {
                    "name": repre["name"],
                    "metadata": self._prepare_component_metadata(
                        instance, repre, published_path, False
                    )
                },
                "component_location_name": unmanaged_location_name,
            })

            component_list.append(other_item)

        def json_obj_parser(obj):
            return str(obj)

        self.log.debug("Components list: {}".format(
            json.dumps(
                component_list,
                sort_keys=True,
                indent=4,
                default=json_obj_parser
            )
        ))
        instance.data["ftrackComponentsList"] = component_list

    def _get_matching_thumbnail_item(
        self,
        review_representation,
        thumbnail_data_items,
        are_multiple_synced_thumbnails
    ):
        """Return matching thumbnail item from list of thumbnail items.

        If a thumbnail item already exists, this should return it.
        The benefit is that if an `outputName` key is found in
        representation and is also used as a `sync_key`  in a thumbnail
        data item, it can sync with that item.

        Args:
            review_representation (dict): Review representation
            thumbnail_data_items (list): List of thumbnail data items
            are_multiple_synced_thumbnails (bool): If there are multiple synced
                thumbnails

        Returns:
            dict: Thumbnail data item or empty dict
        """
        output_name = review_representation.get("outputName")
        tags = review_representation.get("tags", [])
        matching_thumbnail_item = {}
        for thumb_item in thumbnail_data_items:
            if (
                are_multiple_synced_thumbnails
                and (
                    thumb_item["sync_key"] == output_name
                    # intermediate files can have preset name in tags
                    # this is usually aligned with `outputName` distributed
                    # during thumbnail creation in `need_thumbnail` tagging
                    # workflow
                    or thumb_item["sync_key"] in tags
                )
            ):
                # return only synchronized thumbnail if multiple
                matching_thumbnail_item = thumb_item
                break
            elif not are_multiple_synced_thumbnails:
                # return any first found thumbnail since we need thumbnail
                # but dont care which one
                matching_thumbnail_item = thumb_item
                break

        if not matching_thumbnail_item:
            # WARNING: this can only happen if multiple thumbnails
            # workflow is broken, since it found multiple matching outputName
            # in representation but they do not align with any thumbnail item
            self.log.warning(
                "No matching thumbnail item found for output name "
                "'{}'".format(output_name)
            )
            if not thumbnail_data_items:
                self.log.warning(
                    "No thumbnail data items found"
                )
                return {}
            # as fallback return first thumbnail item
            return thumbnail_data_items[0]

        return matching_thumbnail_item

    def _make_extended_component_name(
            self, component_item, repre, iteration_index):
        """ Returns the extended component name

        Name is based on the asset name and representation name.

        Args:
            component_item (dict): The component item dictionary.
            repre (dict): The representation dictionary.
            iteration_index (int): The index of the iteration.

        Returns:
            str: The extended component name.

        """
        # reset extended if no need for extended asset name
        if self.keep_first_subset_name_for_review and iteration_index == 0:
            return

        # get asset name and define extended name variant
        asset_name = component_item["asset_data"]["name"]
        return "_".join(
            (asset_name, repre["name"])
        )

    def _create_src_component(
            self, instance, repre, component_item, location):
        """Create src component for thumbnail.

        This will replicate the input component and change its name to
        have suffix "_src".

        Args:
            instance (pyblish.api.Instance): Instance
            repre (dict): Representation
            component_item (dict): Component item
            location (str): Location name

        Returns:
            dict: Component item
        """
        # Make sure thumbnail is disabled
        component_item["thumbnail"] = False
        # Set location
        component_item["component_location_name"] = location
        # Modify name of component to have suffix "_src"
        component_data = component_item["component_data"]
        component_name = component_data["name"]
        component_data["name"] = component_name + "_src"
        component_data["metadata"] = self._prepare_component_metadata(
            instance, repre, component_item["component_path"], False
        )
        return component_item

    def _collect_additional_metadata(self, streams):
        pass

    def _get_asset_version_status_name(self, instance):
        if not self.asset_versions_status_profiles:
            return None

        # Prepare filtering data for new asset version status
        anatomy_data = instance.data["anatomyData"]
        task_type = anatomy_data.get("task", {}).get("type")
        filtering_criteria = {
            "families": instance.data["family"],
            "hosts": instance.context.data["hostName"],
            "task_types": task_type
        }
        matching_profile = filter_profiles(
            self.asset_versions_status_profiles,
            filtering_criteria
        )
        if not matching_profile:
            return None

        return matching_profile["status"] or None

    def _prepare_component_metadata(
        self, instance, repre, component_path, is_review=None
    ):
        if self._is_repre_video(repre):
            return self._prepare_video_component_metadata(instance, repre,
                                                          component_path,
                                                          is_review)
        else:
            return self._prepare_image_component_metadata(repre,
                                                          component_path)

    def _prepare_video_component_metadata(
        self, instance, repre, component_path, is_review=None
    ):
        metadata = {}
        if "openpype_version" in self.additional_metadata_keys:
            label = self.metadata_keys_to_label["openpype_version"]
            metadata[label] = get_openpype_version()

        extension = os.path.splitext(component_path)[-1]
        streams = []
        try:
            streams = get_ffprobe_streams(component_path)
        except Exception:
            self.log.debug(
                "Failed to retrieve information about "
                "input {}".format(component_path))

        # Find video streams
        video_streams = [
            stream
            for stream in streams
            if stream["codec_type"] == "video"
        ]
        # Skip if there are not video streams
        #   - exr is special case which can have issues with reading through
        #       ffmpegh but we want to set fps for it
        if not video_streams and extension not in [".exr"]:
            return metadata

        stream_width = None
        stream_height = None
        stream_fps = None
        frame_out = None
        codec_label = None
        for video_stream in video_streams:
            codec_label = video_stream.get("codec_long_name")
            if not codec_label:
                codec_label = video_stream.get("codec")

            if codec_label:
                pix_fmt = video_stream.get("pix_fmt")
                if pix_fmt:
                    codec_label += " ({})".format(pix_fmt)

            tmp_width = video_stream.get("width")
            tmp_height = video_stream.get("height")
            if tmp_width and tmp_height:
                stream_width = tmp_width
                stream_height = tmp_height

            input_framerate = video_stream.get("r_frame_rate")
            stream_duration = video_stream.get("duration")
            if input_framerate is None or stream_duration is None:
                continue
            try:
                stream_fps = convert_ffprobe_fps_to_float(
                    input_framerate
                )
            except ValueError:
                self.log.warning(
                    "Could not convert ffprobe "
                    "fps to float \"{}\"".format(input_framerate))
                continue

            stream_width = tmp_width
            stream_height = tmp_height

            frame_out = float(stream_duration) * stream_fps
            break

        # Prepare FPS
        instance_fps = instance.data.get("fps")
        if instance_fps is None:
            instance_fps = instance.context.data["fps"]

        repre_fps = repre.get("fps")
        if repre_fps is not None:
            repre_fps = float(repre_fps)

        fps = stream_fps or repre_fps or instance_fps

        # Prepare frame ranges
        frame_start = repre.get("frameStartFtrack")
        frame_end = repre.get("frameEndFtrack")
        if frame_start is None or frame_end is None:
            frame_start = instance.data["frameStart"]
            frame_end = instance.data["frameEnd"]
        duration = (frame_end - frame_start) + 1

        for key, value in [
            ("fps", fps),
            ("frame_start", frame_start),
            ("frame_end", frame_end),
            ("duration", duration),
            ("width", stream_width),
            ("height", stream_height),
            ("fps", fps),
            ("codec", codec_label)
        ]:
            if not value or key not in self.additional_metadata_keys:
                continue
            label = self.metadata_keys_to_label[key]
            metadata[label] = value

        if not is_review:
            ftr_meta = {}
            if fps:
                ftr_meta["frameRate"] = fps

            if stream_width and stream_height:
                ftr_meta["width"] = int(stream_width)
                ftr_meta["height"] = int(stream_height)
            metadata["ftr_meta"] = json.dumps(ftr_meta)
            return metadata

        # Frame end of uploaded video file should be duration in frames
        # - frame start is always 0
        # - frame end is duration in frames
        if not frame_out:
            frame_out = duration

        # Ftrack documentation says that it is required to have
        #   'width' and 'height' in review component. But with those values
        #   review video does not play.
        metadata["ftr_meta"] = json.dumps({
            "frameIn": 0,
            "frameOut": frame_out,
            "frameRate": float(fps)
        })
        return metadata

    def _prepare_image_component_metadata(self, repre, component_path):
        width = repre.get("width")
        height = repre.get("height")
        if not width or not height:
            streams = []
            try:
                streams = get_ffprobe_streams(component_path)
            except Exception:
                self.log.debug(
                    "Failed to retrieve information "
                    "about input {}".format(component_path))

            for stream in streams:
                if "width" in stream and "height" in stream:
                    width = stream["width"]
                    height = stream["height"]
                    break

        metadata = {}
        if width and height:
            metadata = {
                "ftr_meta": json.dumps({
                    "width": width,
                    "height": height,
                    "format": "image"
                })
            }

        return metadata

    def _is_repre_video(self, repre):
        repre_ext = ".{}".format(repre["ext"])
        return repre_ext in VIDEO_EXTENSIONS
