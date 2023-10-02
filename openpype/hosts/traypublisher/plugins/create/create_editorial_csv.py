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
from openpype.pipeline import CreatedInstance
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
    create_allow_context_change = False

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
        self.column_map = self._creator_settings["column_map"]
        self.column_map = self._creator_settings["column_map"]

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
                print(f"Provided CSV file does not exist in the filesystem: {csv_path}")
                continue

            with open(csv_path) as csvfile:
                # Submission,Vendor,Filename,Shot,Task,Version,Notes
                # 2023-10-2_fcg_sub0001,fastcheapgood,ABCD_0080_0010_comp_v001.[1010-1024].exr,ABCD_0080_0010,comp,v001,Prep: Beep boop
                # 2023-10-2_fcg_sub0001,fastcheapgood,ABCD_0080_0010_comp_v001.mov,ABCD_0080_0010,comp,v001,Prep: Beep boop
                for row in csv.DictReader(csvfile):
                    instance = copy.deepcopy(instance_data)
                    timeline = otio.schema.Timeline()
                    timeline.metadata["submission"] = copy.deepcopy(row)
                    track = otio.schema.Track()
                    timeline.tracks.append(track)
                    clip = otio.schema.Clip()
                    track.append(clip)

                    instance.update({
                        "task": row["Task"],
                        "version": row["Version"]
                    })

                    full_file_name = row["Filename"]

                    file_name, file_extension = os.path.splitext(full_file_name)
                    subset_name = file_name.split(".")[0]
                    file_path = os.path.join(ingest_root, full_file_name)

                    if file_extension == ".exr":
                        m = re.search(r"\[\d+-\d+\]", file_name)
                        if not m.group():
                            # Single exr file,, unprobable, but just in case
                            file_path = os.path.join(ingest_root, file_name, full_file_name)
                            clip.media_reference = otio.schema.ExternalReference(
                                target_url=file_path
                            )
                        else:
                            first_frame, last_frame = m.group().replace(
                                "[", ""
                            ).replace(
                                "]", ""
                            ).split("-")

                            frame_directory_name = file_name.split(".")[0]
                            frames_directory = os.path.join(
                                ingest_root,
                                frame_directory_name
                            )
                            frames_path = os.path.join(
                                frames_directory,
                                full_file_name.replace(m.group(), "%d")
                            )
                            collection = clique.parse(f'{frames_path} {m.group()}')
                            if not collection:
                                print("Unable to find frames on disk...skipping.")
                                continue
                            else:
                                img_seq_ref = otio.schema.ImageSequenceReference(
                                    target_url_base=frames_directory,
                                    start_frame=list(collection.indexes)[0],
                                    name_prefix=frame_directory_name,
                                    name_suffix=file_extension,
                                    rate=self.project.get("data", {}).get("fps", 24),
                                )
                                clip.media_reference = img_seq_ref

                    elif file_extension in [".mov", ".mp4"]:
                        clip.media_reference = otio.schema.ExternalReference(
                            target_url=file_path
                        )

                    self._create_otio_instance(
                        subset_name,
                        instance_data,
                        timeline
                    )

    def _create_otio_instance(
        self,
        subset_name,
        data,
        otio_timeline
    ):
        """Otio instance creating function

        Args:
            subset_name (str): name of subset
            data (dict): instance data
            otio_timeline (otio.Timeline): otio timeline object
        """
        # Pass precreate data to creator attributes
        data.update({
            "otioTimeline": otio.adapters.write_to_string(otio_timeline)
        })
        new_instance = CreatedInstance(
            self.family, subset_name, data, self
        )
        self._store_new_instance(new_instance)

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
