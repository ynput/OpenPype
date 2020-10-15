import re
import os
import json
import hiero

from pprint import pformat

from pype.api import Logger
from avalon import io

log = Logger().get_logger(__name__, "hiero")


def tag_data():
    current_dir = os.path.dirname(__file__)
    json_path = os.path.join(current_dir, "tags.json")
    with open(json_path, "r") as json_stream:
        data = json.load(json_stream)
    return data


def create_tag(key, data):
    """
    Creating Tag object.

    Args:
        key (str): name of tag
        data (dict): parameters of tag

    Returns:
        object: Tag object
    """

    tag = hiero.core.Tag(str(key))
    print "Creating tag"
    return update_tag(tag, data)


def update_tag(tag, data):
    """
    Fixing Tag object.

    Args:
        tag (obj): Tag object
        data (dict): parameters of tag
    """

    tag.setNote(data["note"])
    print data
    if data.get("icon"):
        tag.setIcon(str(data["icon"]))
    mtd = tag.metadata()
    data_mtd = data.get("metadata", None)
    if data_mtd:
        [mtd.setValue("tag.{}".format(str(k)), str(v))
         for k, v in data_mtd.items()]
    print data_mtd
    print "tag updated tag"
    return tag


def add_tags_from_presets():
    """
    Will create default tags from presets.
    """
    project = hiero.core.projects()[-1]

    if "Tag Presets" in project.name():
        return

    log.debug("Setting default tags on project: {}".format(project.name()))

    # get hiero tags.json
    nks_pres_tags = tag_data()

    # Get project task types.
    tasks = io.find_one({"type": "project"})["config"]["tasks"]
    nks_pres_tags["[Tasks]"] = {}
    log.debug("__ tasks: {}".format(pformat(tasks)))
    for task_type in tasks.keys():
        nks_pres_tags["[Tasks]"][task_type.lower()] = {
            "editable": "1",
            "note": "",
            "icon": {
                "path": "icons:TagGood.png"
            },
            "metadata": {
                "family": "task",
                "type": task_type
            }
        }

    # Get project assets. Currently Ftrack specific to differentiate between
    # asset builds and shots.
    if int(os.getenv("TAG_ASSETBUILD_STARTUP", 0)) == 1:
        nks_pres_tags["[AssetBuilds]"] = {}
        for asset in io.find({"type": "asset"}):
            if asset["data"]["entityType"] == "AssetBuild":
                nks_pres_tags["[AssetBuilds]"][asset["name"]] = {
                    "editable": "1",
                    "note": "",
                    "icon": {
                        "path": "icons:TagActor.png"
                    },
                    "metadata": {
                        "family": "assetbuild"
                    }
                }

    # get project and root bin object
    project = hiero.core.projects()[-1]
    root_bin = project.tagsBin()

    for _k, _val in nks_pres_tags.items():
        pattern = re.compile(r"\[(.*)\]")
        bin_find = pattern.findall(_k)
        if bin_find:
            # check what is in root bin
            bins = [b for b in root_bin.items()
                    if b.name() in str(bin_find[0])]

            if bins:
                bin = bins[0]
            else:
                # create Bin object
                bin = hiero.core.Bin(str(bin_find[0]))

            for k, v in _val.items():
                tags = [t for t in bin.items()
                        if str(k) in t.name()
                        if len(str(k)) == len(t.name())]
                if not tags:
                    # create Tag obj
                    tag = create_tag(k, v)

                    # adding Tag to Bin
                    bin.addItem(tag)
                else:
                    update_tag(tags[0], v)

            if not bins:
                # adding Tag to Root Bin
                root_bin.addItem(bin)

        else:
            tags = None
            tags = [t for t in root_bin.items()
                    if str(_k) in t.name()]

            if not tags:
                # create Tag
                tag = create_tag(_k, _val)

                # adding Tag to Root Bin
                root_bin.addItem(tag)
            else:
                # check if Hierarchy in name
                # update Tag if already exists
                for _t in tags:
                    if isinstance(_t, hiero.core.Bin):
                        continue
                    if "hierarchy" in _t.name().lower():
                        continue

                    # update only non hierarchy tags
                    # because hierarchy could be edited
                    update_tag(_t, _val)

    log.info("Default Tags were set...")
