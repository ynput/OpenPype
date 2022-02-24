import os
import sys
import six
import re
import json

import app_utils

# Fill following constants or set them via environment variable
FTRACK_MODULE_PATH = None
FTRACK_API_KEY = None
FTRACK_API_USER = None
FTRACK_SERVER = None


def import_ftrack_api():
    try:
        import ftrack_api
        return ftrack_api
    except ImportError:
        import sys
        ftrk_m_p = FTRACK_MODULE_PATH or os.getenv("FTRACK_MODULE_PATH")
        sys.path.append(ftrk_m_p)
        import ftrack_api
        return ftrack_api


def get_ftrack_session():
    import os
    ftrack_api = import_ftrack_api()

    # fill your own credentials
    url = FTRACK_SERVER or os.getenv("FTRACK_SERVER") or ""
    user = FTRACK_API_USER or os.getenv("FTRACK_API_USER") or ""
    api = FTRACK_API_KEY or os.getenv("FTRACK_API_KEY") or ""

    first_validation = True
    if not user:
        print('- Ftrack Username is not set')
        first_validation = False
    if not api:
        print('- Ftrack API key is not set')
        first_validation = False
    if not first_validation:
        return False

    try:
        return ftrack_api.Session(
            server_url=url,
            api_user=user,
            api_key=api
        )
    except Exception as _e:
        print("Can't log into Ftrack with used credentials: {}".format(_e))
        ftrack_cred = {
            'Ftrack server': str(url),
            'Username': str(user),
            'API key': str(api),
        }

        item_lens = [len(key) + 1 for key in ftrack_cred]
        justify_len = max(*item_lens)
        for key, value in ftrack_cred.items():
            print('{} {}'.format((key + ':').ljust(justify_len, ' '), value))
        return False


def get_project_task_types(project_entity):
    tasks = {}
    proj_template = project_entity['project_schema']
    temp_task_types = proj_template['_task_type_schema']['types']

    for type in temp_task_types:
        if type['name'] not in tasks:
            tasks[type['name']] = type

    return tasks


class FtrackComponentCreator:
    default_location = "ftrack.server"
    ftrack_locations = {}
    thumbnails = []
    videos = []
    temp_dir = None

    def __init__(self, session):
        self.session = session
        self._get_ftrack_location()

    def generate_temp_data(self, selection, change_preset_data):
        with app_utils.make_temp_dir() as tempdir_path:
            for seq in selection:
                app_utils.export_thumbnail(
                    seq, tempdir_path, change_preset_data)
                app_utils.export_video(seq, tempdir_path, change_preset_data)

        return tempdir_path

    def collect_generated_data(self, tempdir_path):
        temp_files = os.listdir(tempdir_path)
        self.thumbnails = [f for f in temp_files if "jpg" in f]
        self.videos = [f for f in temp_files if "mov" in f]
        self.temp_dir = tempdir_path

    def get_thumb_path(self, shot_name):
        # get component files
        thumb_f = next((f for f in self.thumbnails if shot_name in f), None)
        return os.path.join(self.temp_dir, thumb_f)

    def get_video_path(self, shot_name):
        # get component files
        video_f = next((f for f in self.videos if shot_name in f), None)
        return os.path.join(self.temp_dir, video_f)

    def close(self):
        self.ftrack_locations = {}
        self.session = None

    def create_comonent(self, shot_entity, data, assetversion_entity=None):
        self.shot_entity = shot_entity
        location = self._get_ftrack_location()

        file_path = data["file_path"]

        # get extension
        file = os.path.basename(file_path)
        _n, ext = os.path.splitext(file)

        name = "ftrackreview-mp4" if "mov" in ext else "thumbnail"

        component_data = {
            "name": name,
            "file_path": file_path,
            "file_type": ext,
            "location": location
        }

        if name == "ftrackreview-mp4":
            duration = data["duration"]
            handles = data["handles"]
            fps = data["fps"]
            component_data["metadata"] = {
                'ftr_meta': json.dumps({
                    'frameIn': int(0),
                    'frameOut': int(duration + (handles * 2)),
                    'frameRate': float(fps)
                })
            }
        if not assetversion_entity:
            # get assettype entity from session
            assettype_entity = self._get_assettype({"short": "reference"})

            # get or create asset entity from session
            asset_entity = self._get_asset({
                "name": "plateReference",
                "type": assettype_entity,
                "parent": self.shot_entity
            })

            # get or create assetversion entity from session
            assetversion_entity = self._get_assetversion({
                "version": 0,
                "asset": asset_entity
            })

        # get or create component entity
        self._set_component(component_data, {
            "name": name,
            "version": assetversion_entity,
        })

        return assetversion_entity

    def _overwrite_members(self, entity, data):
        origin_location = self._get_ftrack_location("ftrack.origin")
        location = data.pop("location")

        self._remove_component_from_location(entity, location)

        entity["file_type"] = data["file_type"]

        try:
            origin_location.add_component(
                entity, data["file_path"]
            )
            # Add components to location.
            location.add_component(
                entity, origin_location, recursive=True)
        except Exception as __e:
            print("Error: {}".format(__e))
            self._remove_component_from_location(entity, origin_location)
            origin_location.add_component(
                entity, data["file_path"]
            )
            # Add components to location.
            location.add_component(
                entity, origin_location, recursive=True)

    def _remove_component_from_location(self, entity, location):
        print(location)
        # Removing existing members from location
        components = list(entity.get("members", []))
        components += [entity]
        for component in components:
            for loc in component.get("component_locations", []):
                if location["id"] == loc["location_id"]:
                    print("<< Removing component: {}".format(component))
                    location.remove_component(
                        component, recursive=False
                    )

        # Deleting existing members on component entity
        for member in entity.get("members", []):
            self.session.delete(member)
            print("<< Deleting member: {}".format(member))
            del(member)

        self._commit()

        # Reset members in memory
        if "members" in entity.keys():
            entity["members"] = []

    def _get_assettype(self, data):
        return self.session.query(
            self._query("AssetType", data)).first()

    def _set_component(self, comp_data, base_data):
        component_metadata = comp_data.pop("metadata", {})

        component_entity = self.session.query(
            self._query("Component", base_data)
        ).first()

        if component_entity:
            # overwrite existing members in component entity
            # - get data for member from `ftrack.origin` location
            self._overwrite_members(component_entity, comp_data)

            # Adding metadata
            existing_component_metadata = component_entity["metadata"]
            existing_component_metadata.update(component_metadata)
            component_entity["metadata"] = existing_component_metadata
            return

        assetversion_entity = base_data["version"]
        location = comp_data.pop("location")

        component_entity = assetversion_entity.create_component(
            comp_data["file_path"],
            data=comp_data,
            location=location
        )

        # Adding metadata
        existing_component_metadata = component_entity["metadata"]
        existing_component_metadata.update(component_metadata)
        component_entity["metadata"] = existing_component_metadata

        if comp_data["name"] == "thumbnail":
            self.shot_entity["thumbnail_id"] = component_entity["id"]
            assetversion_entity["thumbnail_id"] = component_entity["id"]

        self._commit()

    def _get_asset(self, data):
        # first find already created
        asset_entity = self.session.query(
            self._query("Asset", data)
        ).first()

        if asset_entity:
            return asset_entity

        asset_entity = self.session.create("Asset", data)

        # _commit if created
        self._commit()

        return asset_entity

    def _get_assetversion(self, data):
        assetversion_entity = self.session.query(
            self._query("AssetVersion", data)
        ).first()

        if assetversion_entity:
            return assetversion_entity

        assetversion_entity = self.session.create("AssetVersion", data)

        # _commit if created
        self._commit()

        return assetversion_entity

    def _commit(self):
        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            # self.session.rollback()
            # self.session._configure_locations()
            six.reraise(tp, value, tb)

    def _get_ftrack_location(self, name=None):
        name = name or self.default_location

        if name in self.ftrack_locations:
            return self.ftrack_locations[name]

        location = self.session.query(
            'Location where name is "{}"'.format(name)
        ).one()
        self.ftrack_locations[name] = location
        return location

    def _query(self, entitytype, data):
        """ Generate a query expression from data supplied.

        If a value is not a string, we'll add the id of the entity to the
        query.

        Args:
            entitytype (str): The type of entity to query.
            data (dict): The data to identify the entity.
            exclusions (list): All keys to exclude from the query.

        Returns:
            str: String query to use with "session.query"
        """
        queries = []
        if sys.version_info[0] < 3:
            for key, value in data.items():
                if not isinstance(value, (str, int)):
                    print("value: {}".format(value))
                    if "id" in value.keys():
                        queries.append(
                            "{0}.id is \"{1}\"".format(key, value["id"])
                        )
                else:
                    queries.append("{0} is \"{1}\"".format(key, value))
        else:
            for key, value in data.items():
                if not isinstance(value, (str, int)):
                    print("value: {}".format(value))
                    if "id" in value.keys():
                        queries.append(
                            "{0}.id is \"{1}\"".format(key, value["id"])
                        )
                else:
                    queries.append("{0} is \"{1}\"".format(key, value))

        query = (
            "select id from " + entitytype + " where " + " and ".join(queries)
        )
        print(query)
        return query


class FtrackEntityOperator:
    existing_tasks = []

    def __init__(self, session, project_entity):
        self.session = session
        self.project_entity = project_entity

    def commit(self):
        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            self.session._configure_locations()
            six.reraise(tp, value, tb)

    def create_ftrack_entity(self, session, type, name, parent=None):
        parent = parent or self.project_entity
        entity = session.create(type, {
            'name': name,
            'parent': parent
        })
        try:
            session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            session.rollback()
            session._configure_locations()
            six.reraise(tp, value, tb)
        return entity

    def get_ftrack_entity(self, session, type, name, parent):
        query = '{} where name is "{}" and project_id is "{}"'.format(
            type, name, self.project_entity["id"])

        entity = session.query(query).first()

        # if entity doesnt exist then create one
        if not entity:
            entity = self.create_ftrack_entity(
                session,
                type,
                name,
                parent
            )

        return entity

    def create_parents(self, template):
        parents = []
        t_split = template.split("/")
        replace_patern = re.compile(r"(\[.*\])")
        type_patern = re.compile(r"\[(.*)\]")

        for t_s in t_split:
            match_type = type_patern.findall(t_s)
            if not match_type:
                raise Exception((
                    "Missing correct type flag in : {}"
                    "/n Example: name[Type]").format(
                        t_s)
                )
            new_name = re.sub(replace_patern, "", t_s)
            f_type = match_type.pop()

            parents.append((new_name, f_type))

        return parents

    def create_task(self, task_type, task_types, parent):
        _exising_tasks = [
            child for child in parent['children']
            if child.entity_type.lower() == 'task'
        ]

        # add task into existing tasks if they are not already there
        for _t in _exising_tasks:
            if _t in self.existing_tasks:
                continue
            self.existing_tasks.append(_t)

        existing_task = [
            task for task in self.existing_tasks
            if task['name'].lower() in task_type.lower()
            if task['parent'] == parent
        ]

        if existing_task:
            return existing_task.pop()

        task = self.session.create('Task', {
            "name": task_type.lower(),
            "parent": parent
        })
        task["type"] = task_types[task_type]

        self.existing_tasks.append(task)
        return task
