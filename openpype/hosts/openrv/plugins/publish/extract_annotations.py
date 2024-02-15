import os
import pyblish.api
import tempfile
import ftrack_api
import rv

from openpype.pipeline import publish
from openpype.client import get_project
from openpype.hosts.openrv.api.review import (
    get_path_annotated_frame,
    extract_annotated_frame
)


class ExtractOpenRVAnnotatedFrames(publish.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Annotations from Session"
    hosts = ["openrv"]
    families = ["annotation"]

    def process(self, instance):
        asset = instance.data['asset']
        annotated_frames = instance.data['annotated_frame']
        version_context = instance.data['version_context']
        node = instance.data['node']

        tmp_staging = tempfile.mkdtemp(prefix="pyblish_tmp_")
        self.log.debug(
            f"Create temp directory {tmp_staging} for thumbnail"
        )

        export_annotated_filepath = []
        for annotated_frame in annotated_frames:
            annotated_frame_path = get_path_annotated_frame(
                frame=annotated_frame,
                asset=asset,
                asset_folder=tmp_staging
            )
            self.log.info("Annotated frame path: {}".format(annotated_frame_path))
            export_annotated_filepath.append(annotated_frame_path)
            annotated_frame_folder, file = os.path.split(annotated_frame_path)
            if not os.path.isdir(annotated_frame_folder):
                os.makedirs(annotated_frame_folder)

            # save the frame
            extract_annotated_frame(filepath=annotated_frame_path, frame_to_export=annotated_frame)
            folder, file = os.path.split(annotated_frame_path)
            filename, ext = os.path.splitext(file)

        representation = {
            "name": ext.lstrip("."),
            "ext": ext.lstrip("."),
            "files": export_annotated_filepath,
            "stagingDir": folder,
        }

        if "representations" not in instance.data:
            instance.data["representations"] = []

        instance.data["representations"].append(representation)

        session = ftrack_api.session.Session()
        user = session.query("User where username is \"{}\"".format(session.api_user)).first()

        # Get the target entity
        project_id = get_project(version_context['project']['name'])['data']['ftrackId']
        asset_query = ('AssetVersion where asset.name is "{0}"'
                       ' and version is {1} and project_id is {2} '
                       'and asset.parent.name is {3}').format(version_context['subset'],
                                                              version_context['version'],
                                                              project_id,
                                                              version_context['asset'])
        asset_version = session.query(asset_query).one()

        # Set up note details
        properties_name = "{0}.openpype_review.comment".format(node)
        note_text = ""
        if rv.commands.propertyExists(properties_name):
            note_text = rv.commands.getStringProperty(properties_name)[0]

        # Create the note
        note = asset_version.create_note(note_text, author=user)

        server_location = session.query(
            'Location where name is "ftrack.server"'
        ).one()

        for annotated_frame_path in export_annotated_filepath:
            component = session.create_component(
                annotated_frame_path,
                data={'name': os.path.basename(annotated_frame_path)},
                location=server_location
            )

            session.create(
                'NoteComponent',
                {'component_id': component['id'], 'note_id': note['id']}
            )

        # Commit the changes
        session.commit()
