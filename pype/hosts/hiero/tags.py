import re
import os
import hiero

from pype.api import Logger
from avalon import io

log = Logger().get_logger(__name__, "hiero")


def tag_data():
    return {
        "Hierarchy": {
            "editable": "1",
            "note": "{folder}/{sequence}/{shot}",
            "icon": "hierarchy.png",
            "metadata": {
                "folder": "FOLDER_NAME",
                "shot": "{clip}",
                "track": "{track}",
                "sequence": "{sequence}",
                "episode": "EPISODE_NAME",
                "root": "{projectroot}"
            }
        },
        "Source Resolution": {
            "editable": "1",
            "note": "Use source resolution",
            "icon": "resolution.png",
            "metadata": {
                "family": "resolution"
            }
        },
        "Retiming": {
            "editable": "1",
            "note": "Clip has retime or TimeWarp effects (or multiple effects stacked on the clip)",  # noqa
            "icon": "retiming.png",
            "metadata": {
                "family": "retiming",
                "marginIn": 1,
                "marginOut": 1
            }
        },
        "Frame start": {
            "editable": "1",
            "note": "Starting frame for comps. \n\n> Use `value` and add either number or write `source` (if you want to preserve source frame numbering)",  # noqa
            "icon": "icons:TagBackground.png",
            "metadata": {
                "family": "frameStart",
                "value": "1001"
            }
        },
        "[Lenses]": {
            "Set lense here": {
                "editable": "1",
                "note": "Adjust parameters of your lense and then drop to clip. Remember! You can always overwrite on clip",  # noqa
                "icon": "lense.png",
                "metadata": {
                    "focalLengthMm": 57

                }
            }
        },
        "[Subsets]": {
            "Audio": {
                "editable": "1",
                "note": "Export with Audio",
                "icon": "volume.png",
                "metadata": {
                    "family": "audio",
                    "subset": "main"
                }
            },
            "plateFg": {
                "editable": "1",
                "note": "Add to publish to \"forground\" subset. Change metadata subset name if different order number",  # noqa
                "icon": "z_layer_fg.png",
                "metadata": {
                    "family": "plate",
                    "subset": "Fg01"
                }
            },
            "plateBg": {
                "editable": "1",
                "note": "Add to publish to \"background\" subset. Change metadata subset name if different order number",  # noqa
                "icon": "z_layer_bg.png",
                "metadata": {
                    "family": "plate",
                    "subset": "Bg01"
                }
            },
            "plateRef": {
                "editable": "1",
                "note": "Add to publish to \"reference\" subset.",
                "icon": "icons:Reference.png",
                "metadata": {
                    "family": "plate",
                    "subset": "Ref"
                }
            },
            "plateMain": {
                "editable": "1",
                "note": "Add to publish to \"main\" subset.",
                "icon": "z_layer_main.png",
                "metadata": {
                    "family": "plate",
                    "subset": "main"
                }
            },
            "plateProxy": {
                "editable": "1",
                "note": "Add to publish to \"proxy\" subset.",
                "icon": "z_layer_main.png",
                "metadata": {
                    "family": "plate",
                    "subset": "proxy"
                }
            },
            "review": {
                "editable": "1",
                "note": "Upload to Ftrack as review component.",
                "icon": "review.png",
                "metadata": {
                    "family": "review",
                    "track": "review"
                }
            }
        },
        "[Handles]": {
            "start: add 20 frames": {
                "editable": "1",
                "note": "Adding frames to start of selected clip",
                "icon": "3_add_handles_start.png",
                "metadata": {
                    "family": "handles",
                    "value": "20",
                    "args": "{'op':'add','where':'start'}"
                }
            },
            "start: add 10 frames": {
                "editable": "1",
                "note": "Adding frames to start of selected clip",
                "icon": "3_add_handles_start.png",
                "metadata": {
                    "family": "handles",
                    "value": "10",
                    "args": "{'op':'add','where':'start'}"
                }
            },
            "start: add 5 frames": {
                "editable": "1",
                "note": "Adding frames to start of selected clip",
                "icon": "3_add_handles_start.png",
                "metadata": {
                    "family": "handles",
                    "value": "5",
                    "args": "{'op':'add','where':'start'}"
                }
            },
            "start: add 0 frames": {
                "editable": "1",
                "note": "Adding frames to start of selected clip",
                "icon": "3_add_handles_start.png",
                "metadata": {
                    "family": "handles",
                    "value": "0",
                    "args": "{'op':'add','where':'start'}"
                }
            },
            "end: add 20 frames": {
                "editable": "1",
                "note": "Adding frames to end of selected clip",
                "icon": "1_add_handles_end.png",
                "metadata": {
                    "family": "handles",
                    "value": "20",
                    "args": "{'op':'add','where':'end'}"
                }
            },
            "end: add 10 frames": {
                "editable": "1",
                "note": "Adding frames to end of selected clip",
                "icon": "1_add_handles_end.png",
                "metadata": {
                    "family": "handles",
                    "value": "10",
                    "args": "{'op':'add','where':'end'}"
                }
            },
            "end: add 5 frames": {
                "editable": "1",
                "note": "Adding frames to end of selected clip",
                "icon": "1_add_handles_end.png",
                "metadata": {
                    "family": "handles",
                    "value": "5",
                    "args": "{'op':'add','where':'end'}"
                }
            },
            "end: add 0 frames": {
                "editable": "1",
                "note": "Adding frames to end of selected clip",
                "icon": "1_add_handles_end.png",
                "metadata": {
                    "family": "handles",
                    "value": "0",
                    "args": "{'op':'add','where':'end'}"
                }
            }
        },
        "NukeScript": {
            "editable": "1",
            "note": "Collecting track items to Nuke scripts.",
            "icon": "icons:TagNuke.png",
            "metadata": {
                "family": "nukescript",
                "subset": "main"
            }
        },
        "Comment": {
            "editable": "1",
            "note": "Comment on a shot.",
            "icon": "icons:TagComment.png",
            "metadata": {
                "family": "comment",
                "subset": "main"
            }
        }
    }


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
    return update_tag(tag, data)


def update_tag(tag, data):
    """
    Fixing Tag object.

    Args:
        tag (obj): Tag object
        data (dict): parameters of tag
    """
    # set icon if any available in input data
    if data.get("icon"):
        tag.setIcon(str(data["icon"]))
    # set note description of tag
    tag.setNote(data["note"])
    # get metadata of tag
    mtd = tag.metadata()
    # get metadata key from data
    data_mtd = data.get("metadata", {})
    # set all data metadata to tag metadata
    for k, v in data_mtd.items():
        mtd.setValue(
            "tag.{}".format(str(k)),
            str(v)
        )
    return tag


def add_tags_from_presets():
    """
    Will create default tags from presets.
    """
    from .lib import get_current_project

    # get project and root bin object
    project = get_current_project()
    root_bin = project.tagsBin()

    if "Tag Presets" in project.name():
        return

    log.debug("Setting default tags on project: {}".format(project.name()))

    # get hiero tags.json
    nks_pres_tags = tag_data()

    # Get project task types.
    tasks = io.find_one({"type": "project"})["config"]["tasks"]
    nks_pres_tags["[Tasks]"] = {}
    log.debug("__ tasks: {}".format(tasks))
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

    # loop trough tag data dict and create deep tag structure
    for _k, _val in nks_pres_tags.items():
        # check if key is not decorated with [] so it is defined as bin
        bin_find = None
        pattern = re.compile(r"\[(.*)\]")
        bin_finds = pattern.findall(_k)
        # if there is available any then pop it to string
        if bin_finds:
            bin_find = bin_finds.pop()

        # if bin was found then create or update
        if bin_find:
            # first check if in root lever is not already created bins
            bins = [b for b in root_bin.items()
                    if b.name() in str(bin_find)]

            if bins:
                bin = bins.pop()
            else:
                # create Bin object for processing
                bin = hiero.core.Bin(str(bin_find))

            # update or create tags in the bin
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
                    update_tag(tags.pop(), v)

            # finally add the Bin object to the root level Bin
            if not bins:
                # adding Tag to Root Bin
                root_bin.addItem(bin)
        else:
            # for Tags to be created in root level Bin
            # at first check if any of input data tag is not already created
            tags = None
            tags = [t for t in root_bin.items()
                    if str(_k) in t.name()]

            if not tags:
                # create Tag
                tag = create_tag(_k, _val)

                # adding Tag to Root Bin
                root_bin.addItem(tag)
            else:
                # update Tags if they already exists
                for _t in tags:
                    # skip bin objects
                    if isinstance(_t, hiero.core.Bin):
                        continue

                    # check if Hierarchy in name and skip it
                    # because hierarchy could be edited
                    if "hierarchy" in _t.name().lower():
                        continue

                    # update only non hierarchy tags
                    update_tag(_t, _val)

    log.info("Default Tags were set...")
