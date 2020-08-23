import copy
import os
import shutil
import sys

import pyblish.api
import six
from avalon import api, io, pipeline

import pype.api
from pype.api import Anatomy

class ExtractHarmonyZipFromXstage(pype.api.Extractor):
    """Extract Harmony zip"""

    label = "Extract Harmony zip"
    order = pyblish.api.ExtractorOrder + 0.02
    hosts = ["standalonepublisher"]
    families = ["scene"]

    def process(self, instance):
        context = instance.context
        asset_doc = instance.context.data["assetEntity"]
        asset_name = instance.data["asset"]
        subset_name = instance.data["subset"]
        instance_name = instance.data["name"]
        family = instance.data["family"]
        task = instance.context.data["anatomyData"]["task"]
        entity = context.data["assetEntity"]

        # Create the Ingest task if it does not exist
        if "ingest" in task:
            existing_tasks = []
            for child in entity['children']:
                if child.entity_type.lower() == 'task':
                    existing_tasks.append(child['name'].lower())

            if task.lower() in existing_tasks:
                print("Task {} already exists".format(task))

            else:
                self.create_task(
                    name=task,
                    task_type="Ingest",
                    parent=entity
                )

        # Find latest version
        latest_version = self.find_last_version(subset_name, asset_doc)
        version_number = 1
        if latest_version is not None:
            version_number += latest_version

        self.log.info(
            "Next version of instance \"{}\" will be {}".format(
                instance_name, version_number
            )
        )

        # Set family and subset
        instance.data["family"] = family
        instance.data["subset"] = subset_name
        instance.data["version"] = version_number
        instance.data["latestVersion"] = latest_version

        instance.data["anatomyData"].update({
            "subset": subset_name,
            "family": family,
            "version": version_number
        })

        # Copy `families` and check if `family` is not in current families
        families = instance.data.get("families") or list()
        if families:
            families = list(set(families))

        instance.data["families"] = families

        # Prepare staging dir for new instance
        staging_dir = self.staging_dir(instance)
        repres = instance.data.get("representations")
        source = os.path.join(repres[0]["stagingDir"], repres[0]["files"])
        os.chdir(staging_dir)
        zip_file = shutil.make_archive(os.path.basename(source), "zip", source)
        output_filename = os.path.basename(zip_file)
        self.log.info("Zip file: {}".format(zip_file))
        new_repre = {
            "name": "zip",
            "ext": "zip",
            "files": output_filename,
            "stagingDir": staging_dir
        }
        self.log.debug(
            "Creating new representation: {}".format(new_repre)
        )
        instance.data["representations"] = [new_repre]

        workfile_path = self.extract_workfile(instance, zip_file)
        self.log.debug("Extracted Workfile to: {}".format(workfile_path))

    def extract_workfile(self, instance, zip_file):

        anatomy = anatomy = Anatomy()#pype.api.Anatomy()
        data = copy.deepcopy(instance.data["anatomyData"])
        self.log.info(data)
        self.log.info(anatomy.roots)
        data["root"] = str(anatomy.roots)
        self.log.info(data)
        # Get new filename, create path based on asset and work template

        template = anatomy.templates["work"]["path"]
        data["version"] = 1
        data["ext"] = "zip"
        _data = {k: v for k, v in data.items() if v is not None}
        work_path = api.format_template_with_optional_keys(_data, template)
        _data["version"] = api.last_workfile_with_version(
            os.path.dirname(work_path), template, _data, [".zip"]
        )[1]
        self.log.info(_data)
        work_path = api.format_template_with_optional_keys(_data, template)
        os.makedirs(os.path.dirname(work_path), exist_ok=True)
        shutil.copy(zip_file, work_path)

        return work_path

    def find_last_version(self, subset_name, asset_doc):
        subset_doc = io.find_one({
            "type": "subset",
            "name": subset_name,
            "parent": asset_doc["_id"]
        })

        if subset_doc is None:
            self.log.debug("Subset entity does not exist yet.")
        else:
            version_doc = io.find_one(
                {
                    "type": "version",
                    "parent": subset_doc["_id"]
                },
                sort=[("name", -1)]
            )
            if version_doc:
                return int(version_doc["name"])
        return None

    def create_task(self, name, task_type, parent):
        task = self.session.create('Task', {
            'name': name,
            'parent': parent
        })
        # TODO not secured!!! - check if task_type exists
        self.log.info(task_type)
        self.log.info(self.task_types)
        task['type'] = self.task_types[task_type]

        try:
            self.session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            self.session.rollback()
            six.reraise(tp, value, tb)

        return task
