import copy
import csv
import os
import re
from copy import deepcopy
import opentimelineio as otio
from openpype.client import (
    get_asset_by_name,
    get_project,
    get_assets
)
from openpype.hosts.traypublisher.api.plugin import (
    TrayPublishCreator,
    HiddenTrayPublishCreator
)
from openpype.hosts.traypublisher.api.editorial import (
    ShotMetadataSolver
)
from openpype.pipeline import CreatedInstance, KnownPublishError
from openpype.lib import (
    get_ffprobe_data,
    convert_ffprobe_fps_value,
    FileDef,
    get_version_from_path

)

import clique

from pprint import pprint

class EditorialCSVCreator(TrayPublishCreator):
    """ Editorial CSV creator class
    """
    label = "Editorial CSV Ingest"
    family = "editorial"
    identifier = "editorial_csv_ingest"
    default_variants = [
        "Main"
    ]
    description = "Ingest an Editorial CSV file and generate an OTIO timeline(s)."
    detailed_description = """
Supporting publishing by providing an CSV file, new shots to project
or updating already created. Publishing will create OTIO file(s).
"""
    icon = "fa.file"

    def __init__(
        self, project_settings, *args, **kwargs
    ):
        super(EditorialCSVCreator, self).__init__(
            project_settings, *args, **kwargs
        )
        editorial_csv_settings = deepcopy(project_settings.get(
            "traypublisher", {}
        ).get("editorial_creators", {}).get(self.identifier, {}))

        if not editorial_csv_settings:
            raise ValueError("""Missing Editorial CSV settings in:
                `settings/entities/schemas/project_schema/schema_project_traypublisher.json`
                contact with the OpenPype admin.
            """)

        self.project = get_project(self.project_name)
        self._creator_settings = editorial_csv_settings
        self.column_map = self._creator_settings["csv_ingest"]
        self.required_columns = [column["name"] for column in self.column_map if column["required"] == "Required"]
        self._shots = {}


    def create(self, subset_name, instance_data, pre_create_data):
        #None
        #{'asset': None, 'family': 'editorial', 'task': None, 'variant': 'Main'}
        #{'csv_filepath_data': {'directory': '/home/minkiu/Projects/ynput/openpype-projects-root/editorial_csv_ingest',
        #                    'filenames': ['2023-10-2_fcg_sub0001.csv'],
        #                    'is_sequence': False}}

        ingest_root = pre_create_data.get("csv_filepath_data", {}).get("directory", "")

        for csv_file in pre_create_data.get("csv_filepath_data", {}).get("filenames", []):
            csv_path = os.path.join(ingest_root, csv_file)

            if not os.path.exists(csv_path):
                raise KnownPublishError(f"Provided CSV file does not exist in the filesystem: {csv_path}")

            with open(csv_path) as csvfile:
                csv_dict = csv.DictReader(csvfile)
                missing_columns = set(self.required_columns) - set(csv_dict.fieldnames)

                if missing_columns:
                    raise KnownPublishError("The CSV is missing columns:\n{0}".format(
                        "\n".join(missing_columns)
                    ))
                _get_shots_from_csv(csv_dict, instance_data)

        if self._shots:
            for otio_timeline in _create_otio_timelines():
                instance_data["otio_timeline"] = otio_timeline
                new_instance = CreatedInstance(
                    otio_timeline["metadata"]["submission"]["family"],
                    subset_name,
                    instance_data,
                    self
                )
                self._store_new_instance(new_instance)


    def _create_otio_timelines(self):
        otio_timelines = []

        for shot_name, shot_media in self._shots.items():
            timeline = otio.schema.Timeline()
            timeline.metadata["submission"] = copy.deepcopy(shot_data)
            track = otio.schema.Track()
            timeline.tracks.append(track)
            clip = otio.schema.Clip()
            track.append(clip)

            for media in shot_media:
                media_path = media["file_path"]

                directory_name, file_name = os.path.split(media_path)
                file_prefix, file_extension = file_name.splitext()

                if media_path.endswith(".exr"):
                    colection = clique.parse(media_path)

                    if colection:
                        img_seq_ref = otio.schema.ImageSequenceReference(
                            target_url_base=directory_name,
                            start_frame=list(collection.indexes)[0],
                            name_prefix=file_prefix,
                            name_suffix=file_extension,
                            rate=self.project.get("data", {}).get("fps", 24),
                        )
                        clip.media_reference = img_seq_ref
                    else:
                        # Single Frame
                        clip.media_reference = otio.schema.ExternalReference(
                            target_url=media_path
                        )
                else:
                    # Mov or MP4
                    clip.media_reference = otio.schema.ExternalReference(
                        target_url=media_path
                    )

            otio_timelines.append(timeline)

        return otio_timelines


    def _get_shots_from_csv(self, csv_dict, instance_data):
        """Traverse the CSV file and extract the different foung shots.

        """

        for row in csv_dict:
            shot_name = row["Shot"]
            self._shots.setdefault(shot_name, [])
            instance = copy.deepcopy(instance_data)
            instance.update({
                "task": row["Task"],
                "version": row["Version"],
                "variant": row["Variant"],
                "family": row["Product Type"],
            })


            file_name = row["Filename"]

            file_prefix, file_extension = os.path.splitext(file_name)

            subset_name = file_prefix.split(".")[0]
            file_path = os.path.join(ingest_root, file_name)

            if file_extension == ".exr":
                file_path =  os.path.join(ingest_root, shot_name, file_name)

            instance["file_path"] = file_path

            self._shots[shot_name].append(instance)

    def get_pre_create_attr_defs(self):
        """ Creating pre-create attributes at creator plugin.

        Returns:
            list: list of attribute object instances
        """
        # Use same attributes as for instance attrobites
        attr_defs = [
            FileDef(
                "csv_filepath_data",
                folders=False,
                extensions=[
                    ".csv"
                ],
                allow_sequences=False,
                single_item=True,
                label="CSV File",
            ),
        ]
        return attr_defs
