import os
import subprocess
import tempfile
import shutil
import json
import sys

import opentimelineio as otio
import ftrack_api
import requests

from openpype_modules.ftrack.lib import BaseAction


def download_file(url, path):
    with open(path, "wb") as f:
        print("\nDownloading %s" % path)
        response = requests.get(url, stream=True)
        total_length = response.headers.get('content-length')

        if total_length is None:
            f.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)))
                sys.stdout.flush()


class ExportEditorialAction(BaseAction):
    '''Export Editorial action'''

    label = "Export Editorial"
    variant = None
    identifier = "export-editorial"
    description = None
    component_name_order = ["exr", "mov", "ftrackreview-mp4_src"]

    def export_editorial(self, entity, output_path):
        session = ftrack_api.Session()
        unmanaged_location = session.query(
            "Location where name is \"ftrack.unmanaged\""
        ).one()
        temp_path = tempfile.mkdtemp()

        files = {}
        for obj in entity["review_session_objects"]:
            data = {}
            parent_name = obj["asset_version"]["asset"]["parent"]["name"]
            component_query = "Component where version_id is \"{}\""
            component_query += " and name is \"{}\""
            for name in self.component_name_order:
                try:
                    component = session.query(
                        component_query.format(
                            obj["asset_version"]["id"], name
                        )
                    ).one()
                    path = unmanaged_location.get_filesystem_path(component)
                    data["path"] = path.replace("\\", "/")
                    break
                except ftrack_api.exception.NoResultFoundError:
                    pass

            # Download online review if not local path found.
            if "path" not in data:
                component = session.query(
                    component_query.format(
                        obj["asset_version"]["id"], "ftrackreview-mp4"
                    )
                ).one()
                location = component["component_locations"][0]
                component_url = location["location"].get_url(component)
                asset_name = obj["asset_version"]["asset"]["name"]
                version = obj["asset_version"]["version"]
                filename = "{}_{}_v{:03d}.mp4".format(
                    parent_name, asset_name, version
                )
                filepath = os.path.join(
                    output_path, "downloads", filename
                ).replace("\\", "/")

                if not os.path.exists(os.path.dirname(filepath)):
                    os.makedirs(os.path.dirname(filepath))

                download_file(component_url, filepath)
                data["path"] = filepath

            # Get frame duration and framerate.
            query = "Component where version_id is \"{}\""
            query += " and name is \"ftrackreview-mp4\""
            component = session.query(
                query.format(obj["asset_version"]["id"])
            ).one()
            metadata = json.loads(component["metadata"]["ftr_meta"])
            data["framerate"] = metadata["frameRate"]
            data["frames"] = metadata["frameOut"] - metadata["frameIn"]

            # Find audio if it exists.
            query = "Asset where parent.id is \"{}\""
            query += " and type.name is \"Audio\""
            asset = session.query(
                query.format(obj["asset_version"]["asset"]["parent"]["id"])
            )
            if asset:
                asset_version = asset[0]["versions"][-1]
                query = "Component where version_id is \"{}\""
                query += " and name is \"{}\""
                comp = session.query(
                    query.format(asset_version["id"], "wav")
                ).one()
                src = unmanaged_location.get_filesystem_path(comp)
                dst = os.path.join(temp_path, parent_name + ".wav")
                shutil.copy(src, dst)

            # Collect data.
            files[parent_name] = data

        clips = []
        for name, data in files.items():
            self.log.info("Processing {} with {}".format(name, data))
            f = data["path"]
            range = otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, data["framerate"]),
                duration=otio.opentime.RationalTime(
                    data["frames"], data["framerate"]
                )
            )

            media_reference = otio.schema.ExternalReference(
                available_range=range,
                target_url=f"file://{f}"
            )

            clip = otio.schema.Clip(
                name=name,
                media_reference=media_reference,
                source_range=range
            )
            clips.append(clip)

            # path = os.path.join(temp_path, name + ".wav").replace("\\", "/")
            # if not os.path.exists(path):
            #     args = ["ffmpeg", "-y", "-i", f, path]
            #     self.log.info(subprocess.list2cmdline(args))
            #     subprocess.call(args)

        timeline = otio.schema.timeline_from_clips(clips)
        otio.adapters.write_to_file(
            timeline, os.path.join(output_path, entity["name"] + ".xml")
        )

        data = ""
        for f in os.listdir(temp_path):
            f = f.replace("\\", "/")
            data += f"file '{f}'\n"

        path = os.path.join(temp_path, "temp.txt")
        with open(path, "w") as f:
            f.write(data)

        args = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", os.path.basename(path),
            os.path.join(output_path, entity["name"] + ".wav")
        ]
        self.log.info(subprocess.list2cmdline(args))
        subprocess.call(args, cwd=temp_path)

        shutil.rmtree(temp_path)

    def discover(self, session, entities, event):
        '''Return true if we can handle the selected entities.
        *session* is a `ftrack_api.Session` instance
        *entities* is a list of tuples each containing the entity type and the
        entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.
        *event* the unmodified original event
        '''
        if len(entities) == 1:
            if entities[0].entity_type == "ReviewSession":
                return True

        return False

    def launch(self, session, entities, event):
        '''Callback method for the custom action.
        return either a bool ( True if successful or False if the action
        failed ) or a dictionary with they keys `message` and `success`, the
        message should be a string and will be displayed as feedback to the
        user, success should be a bool, True if successful or False if the
        action failed.
        *session* is a `ftrack_api.Session` instance
        *entities* is a list of tuples each containing the entity type and the
        entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.
        *event* the unmodified original event
        '''
        if 'values' in event['data']:
            userId = event['source']['user']['id']
            user = session.query('User where id is ' + userId).one()
            job = session.create(
                'Job',
                {
                    'user': user,
                    'status': 'running',
                    'data': json.dumps({
                        'description': 'Export Editorial.'
                    })
                }
            )
            session.commit()

            try:
                output_path = event["data"]["values"]["output_path"]

                if not os.path.exists(output_path):
                    os.makedirs(output_path)

                self.export_editorial(entities[0], output_path)

                job['status'] = 'done'
                session.commit()
            except Exception:
                session.rollback()
                job["status"] = "failed"
                session.commit()
                self.log.error(
                    "Exporting editorial failed ({})", exc_info=True
                )

            return {
                'success': True,
                'message': 'Action completed successfully'
            }

        items = [
            {
                'label': 'Output folder:',
                'type': 'text',
                'value': '',
                'name': 'output_path'
            }

        ]
        return {
            'success': True,
            'message': "",
            'items': items
        }


def register(session):
    '''Register action. Called when used as an event plugin.'''

    ExportEditorialAction(session).register()


if __name__ == "__main__":
    session = ftrack_api.Session()
    action = ExportEditorialAction(session)
    id = "bfe0477c-d5a8-49d8-88b9-6d44d2e48fd9"
    review_session = session.get("ReviewSession", id)
    path = r"c:/projects"
    action.export_editorial(review_session, path)