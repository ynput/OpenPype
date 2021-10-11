import re
import os
import glob
import nuke
from openpype.api import Logger
log = Logger().get_logger(__name__)

SINGLE_FILE_FORMATS = ['avi', 'mp4', 'mxf', 'mov', 'mpg', 'mpeg', 'wmv', 'm4v',
                       'm2v']


def evaluate_filepath_new(
        k_value, k_eval, project_dir, first_frame, allow_relative):

    # get combined relative path
    combined_relative_path = None
    if k_eval is not None and project_dir is not None:
        combined_relative_path = os.path.abspath(
            os.path.join(project_dir, k_eval))
        combined_relative_path = combined_relative_path.replace('\\', '/')
        filetype = combined_relative_path.split('.')[-1]
        frame_number = re.findall(r'\d+', combined_relative_path)[-1]
        basename = combined_relative_path[: combined_relative_path.rfind(
            frame_number)]
        filepath_glob = basename + '*' + filetype
        glob_search_results = glob.glob(filepath_glob)
        if len(glob_search_results) <= 0:
            combined_relative_path = None

    try:
        # k_value = k_value % first_frame
        if os.path.isdir(os.path.basename(k_value)):
            # doesn't check for file, only parent dir
            filepath = k_value
        elif os.path.exists(k_eval):
            filepath = k_eval
        elif not isinstance(project_dir, type(None)) and \
                not isinstance(combined_relative_path, type(None)):
            filepath = combined_relative_path

        filepath = os.path.abspath(filepath)
    except Exception as E:
        log.error("Cannot create Read node. Perhaps it needs to be \
                  rendered first :) Error: `{}`".format(E))
        return None

    filepath = filepath.replace('\\', '/')
    # assumes last number is a sequence counter
    current_frame = re.findall(r'\d+', filepath)[-1]
    padding = len(current_frame)
    basename = filepath[: filepath.rfind(current_frame)]
    filetype = filepath.split('.')[-1]

    # sequence or not?
    if filetype in SINGLE_FILE_FORMATS:
        pass
    else:
        # Image sequence needs hashes
        # to do still with no number not handled
        filepath = basename + '#' * padding + '.' + filetype

    # relative path? make it relative again
    if allow_relative:
        if (not isinstance(project_dir, type(None))) and project_dir != "":
            filepath = filepath.replace(project_dir, '.')

    # get first and last frame from disk
    frames = []
    firstframe = 0
    lastframe = 0
    filepath_glob = basename + '*' + filetype
    glob_search_results = glob.glob(filepath_glob)
    for f in glob_search_results:
        frame = re.findall(r'\d+', f)[-1]
        frames.append(frame)
    frames = sorted(frames)
    firstframe = frames[0]
    lastframe = frames[len(frames) - 1]

    if int(lastframe) < 0:
        lastframe = firstframe

    return filepath, firstframe, lastframe


def create_read_node(ndata, comp_start):
    read = nuke.createNode('Read', 'file "' + ndata['filepath'] + '"')
    read.knob('colorspace').setValue(int(ndata['colorspace']))
    read.knob('raw').setValue(ndata['rawdata'])
    read.knob('first').setValue(int(ndata['firstframe']))
    read.knob('last').setValue(int(ndata['lastframe']))
    read.knob('origfirst').setValue(int(ndata['firstframe']))
    read.knob('origlast').setValue(int(ndata['lastframe']))
    if comp_start == int(ndata['firstframe']):
        read.knob('frame_mode').setValue("1")
        read.knob('frame').setValue(str(comp_start))
    else:
        read.knob('frame_mode').setValue("0")
    read.knob('xpos').setValue(ndata['new_xpos'])
    read.knob('ypos').setValue(ndata['new_ypos'])
    nuke.inputs(read, 0)
    return


def write_to_read(gn,
                  allow_relative=False):

    comp_start = nuke.Root().knob('first_frame').value()
    project_dir = nuke.Root().knob('project_directory').getValue()
    if not os.path.exists(project_dir):
        project_dir = nuke.Root().knob('project_directory').evaluate()

    group_read_nodes = []
    with gn:
        height = gn.screenHeight()  # get group height and position
        new_xpos = int(gn.knob('xpos').value())
        new_ypos = int(gn.knob('ypos').value()) + height + 20
        group_writes = [n for n in nuke.allNodes() if n.Class() == "Write"]
        if group_writes != []:
            # there can be only 1 write node, taking first
            n = group_writes[0]

            if n.knob('file') is not None:
                myfile, firstFrame, lastFrame = evaluate_filepath_new(
                    n.knob('file').getValue(),
                    n.knob('file').evaluate(),
                    project_dir,
                    comp_start,
                    allow_relative
                )
                if not myfile:
                    return

                # get node data
                ndata = {
                    'filepath': myfile,
                    'firstframe': int(firstFrame),
                    'lastframe': int(lastFrame),
                    'new_xpos': new_xpos,
                    'new_ypos': new_ypos,
                    'colorspace': n.knob('colorspace').getValue(),
                    'rawdata': n.knob('raw').value(),
                    'write_frame_mode': str(n.knob('frame_mode').value()),
                    'write_frame': n.knob('frame').value()
                }
                group_read_nodes.append(ndata)

    # create reads in one go
    for oneread in group_read_nodes:
        # create read node
        create_read_node(oneread, comp_start)
