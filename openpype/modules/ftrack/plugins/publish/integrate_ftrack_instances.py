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
            self.log.debug("Representation {}".format(repre))
            repre_tags = repre.get("tags") or []
            if repre.get("thumbnail") or "thumbnail" in repre_tags:
                thumbnail_representations.append(repre)

            elif "ftrackreview" in repre_tags:
                review_representations.append(repre)
                if self._is_repre_video(repre):
                    has_movie_review = True

            else:
                other_representations.append(repre)

        # Prepare ftrack locations
        unmanaged_location_name = "ftrack.unmanaged"
        ftrack_server_location_name = "ftrack.server"

        # Components data
        component_list = []
        # Components that will be duplicated to unmanaged location
        src_components_to_add = []

        # Create thumbnail components
        # TODO what if there is multiple thumbnails?
        first_thumbnail_component = None
        first_thumbnail_component_repre = None

        if not review_representations or has_movie_review:
            for repre in thumbnail_representations:
                repre_path = get_publish_repre_path(instance, repre, False)
                if not repre_path:
                    self.log.warning(
                        "Published path is not set and source was removed."
                    )
                    continue

                # Create copy of base comp item and append it
                thumbnail_item = copy.deepcopy(base_component_item)
                thumbnail_item["component_path"] = repre_path
                thumbnail_item["component_data"] = {
                    "name": "thumbnail"
                }
                thumbnail_item["thumbnail"] = True

                # Create copy of item before setting location
                if "delete" not in repre.get("tags", []):
                    src_components_to_add.append(copy.deepcopy(thumbnail_item))
                # Create copy of first thumbnail
                if first_thumbnail_component is None:
                    first_thumbnail_component_repre = repre
                    first_thumbnail_component = thumbnail_item
                # Set location
                thumbnail_item["component_location_name"] = (
                    ftrack_server_location_name
                )

                # Add item to component list
                component_list.append(thumbnail_item)

        if first_thumbnail_component is not None:
            metadata = self._prepare_image_component_metadata(
                first_thumbnail_component_repre,
                first_thumbnail_component["component_path"]
            )

            if metadata:
                component_data = first_thumbnail_component["component_data"]
                component_data["metadata"] = metadata

                if review_representations:
                    component_data["name"] = "thumbnail"
                else:
                    component_data["name"] = "ftrackreview-image"

        # Create review components
        # Change asset name of each new component for review
        is_first_review_repre = True
        not_first_components = []
        extended_asset_name = ""
        multiple_reviewable = len(review_representations) > 1
        for repre in review_representations:
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

            # get asset name and define extended name variant
            asset_name = review_item["asset_data"]["name"]
            extended_asset_name = "_".join(
                (asset_name, repre["name"])
            )

            # reset extended if no need for extended asset name
            if (
                self.keep_first_subset_name_for_review
                and is_first_review_repre
            ):
                extended_asset_name = ""
            else:
                # only rename if multiple reviewable
                if multiple_reviewable:
                    review_item["asset_data"]["name"] = extended_asset_name
                else:
                    extended_asset_name = ""

            # rename all already created components
            # only if first repre and extended name available
            if is_first_review_repre and extended_asset_name:
                # and rename all already created components
                for _ci in component_list:
                    _ci["asset_data"]["name"] = extended_asset_name

                # and rename all already created src components
                for _sci in src_components_to_add:
                    _sci["asset_data"]["name"] = extended_asset_name

                # rename also first thumbnail component if any
                if first_thumbnail_component is not None:
                    first_thumbnail_component[
                        "asset_data"]["name"] = extended_asset_name

            # Change location
            review_item["component_path"] = repre_path
            # Change component data

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

            review_item["component_data"] = {
                # Default component name is "main".
                "name": component_name,
                "metadata": metadata
            }

            if is_first_review_repre:
                is_first_review_repre = False
            else:
                # later detection for thumbnail duplication
                not_first_components.append(review_item)

            # Create copy of item before setting location
            if "delete" not in repre.get("tags", []):
                src_components_to_add.append(copy.deepcopy(review_item))

            # Set location
            review_item["component_location_name"] = (
                ftrack_server_location_name
            )
            # Add item to component list
            component_list.append(review_item)
            if self.upload_reviewable_with_origin_name:
                origin_name_component = copy.deepcopy(review_item)
                filename = os.path.basename(repre_path)
                origin_name_component["component_data"]["name"] = (
                    os.path.splitext(filename)[0]
                )
                component_list.append(origin_name_component)

        # Duplicate thumbnail component for all not first reviews
        if first_thumbnail_component is not None:
            for component_item in not_first_components:
                asset_name = component_item["asset_data"]["name"]
                new_thumbnail_component = copy.deepcopy(
                    first_thumbnail_component
                )
                new_thumbnail_component["asset_data"]["name"] = asset_name
                new_thumbnail_component["component_location_name"] = (
                    ftrack_server_location_name
                )
                component_list.append(new_thumbnail_component)

        # Add source components for review and thubmnail components
        for copy_src_item in src_components_to_add:
            # Make sure thumbnail is disabled
            copy_src_item["thumbnail"] = False
            # Set location
            copy_src_item["component_location_name"] = unmanaged_location_name
            # Modify name of component to have suffix "_src"
            component_data = copy_src_item["component_data"]
            component_name = component_data["name"]
            component_data["name"] = component_name + "_src"
            component_data["metadata"] = self._prepare_component_metadata(
                instance, repre, copy_src_item["component_path"], False
            )
            component_list.append(copy_src_item)

        # Add others representations as component
        for repre in other_representations:
            published_path = get_publish_repre_path(instance, repre, True)
            if not published_path:
                continue
            # Create copy of base comp item and append it
            other_item = copy.deepcopy(base_component_item)

            # add extended name if any
            if (
                not self.keep_first_subset_name_for_review
                and extended_asset_name
            ):
                other_item["asset_data"]["name"] = extended_asset_name

            component_data = {
                "name": repre["name"],
                "metadata": self._prepare_component_metadata(
                    instance, repre, published_path, False
                )
            }
            other_item["component_data"] = component_data
            other_item["component_location_name"] = unmanaged_location_name
            other_item["component_path"] = published_path
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

            self.log.debug("FPS from stream is {} and duration is {}".format(
                input_framerate, stream_duration
            ))
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
