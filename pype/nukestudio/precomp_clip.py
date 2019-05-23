from hiero.core import *
from hiero.ui import *
import ft_utils
import re
import os


def create_nk_script_clips(script_lst, seq=None):
    '''
    nk_scripts is list of dictionaries like:
    [{
        'path': 'P:/Jakub_testy_pipeline/test_v01.nk',
        'name': 'test',
        'timeline_frame_in': 10,
        'handles': 10,
        'source_start': 0,
        'source_end': 54,
        'task': 'Comp-tracking',
        'work_dir': 'VFX_PR',
        'shot': '00010'
    }]
    '''
    env = ft_utils.Env()
    proj = projects()[-1]
    root = proj.clipsBin()

    if not seq:
        seq = Sequence('NewSequences')
        root.addItem(BinItem(seq))
    # todo will ned to define this better
    # track = seq[1]  # lazy example to get a destination#  track
    clips_lst = []
    for nk in script_lst:
        task_short = env.task_codes[nk['task']]
        script_file = task_short
        task_path = '/'.join([nk['work_dir'], nk['shot'], nk['task']])
        bin = create_bin_in_project(task_path, proj)
        task_path += script_file

        if nk['task'] not in seq.videoTracks():
            track = hiero.core.VideoTrack(nk['task'])
            seq.addTrack(track)
        else:
            track = seq.tracks(nk['task'])

        # create slip media
        print nk['path']
        media = MediaSource(nk['path'])
        print media
        source = Clip(media)
        print source
        name = os.path.basename(os.path.splitext(nk['path'])[0])
        split_name = split_by_client_version(name, env)[0] or name
        print split_name
        # print source
        # add to bin as clip item
        items_in_bin = [b.name() for b in bin.items()]
        if split_name not in items_in_bin:
            binItem = BinItem(source)
            bin.addItem(binItem)
        print bin.items()
        new_source = [
            item for item in bin.items() if split_name in item.name()
        ][0].items()[0].item()
        print new_source
        # add to track as clip item
        trackItem = TrackItem(split_name, TrackItem.kVideo)
        trackItem.setSource(new_source)
        trackItem.setSourceIn(nk['source_start'] + nk['handles'])
        trackItem.setSourceOut(nk['source_end'] - nk['handles'])
        trackItem.setTimelineIn(nk['source_start'] + nk['timeline_frame_in'])
        trackItem.setTimelineOut(
            (nk['source_end'] - (nk['handles'] * 2)) + nk['timeline_frame_in'])
        track.addTrackItem(trackItem)
        track.addTrackItem(trackItem)
        clips_lst.append(trackItem)

    return clips_lst


def create_bin_in_project(bin_name='', project=''):
    '''
    create bin in project and
    if the bin_name is "bin1/bin2/bin3" it will create whole depth
    '''

    if not project:
        # get the first loaded project
        project = projects()[0]
    if not bin_name:
        return None
    if '/' in bin_name:
        bin_name = bin_name.split('/')
    else:
        bin_name = [bin_name]

    clipsBin = project.clipsBin()

    done_bin_lst = []
    for i, b in enumerate(bin_name):
        if i == 0 and len(bin_name) > 1:
            if b in [bin.name() for bin in clipsBin.bins()]:
                bin = [bin for bin in clipsBin.bins() if b in bin.name()][0]
                done_bin_lst.append(bin)
            else:
                create_bin = Bin(b)
                clipsBin.addItem(create_bin)
                done_bin_lst.append(create_bin)

        elif i >= 1 and i < len(bin_name) - 1:
            if b in [bin.name() for bin in done_bin_lst[i - 1].bins()]:
                bin = [
                    bin for bin in done_bin_lst[i - 1].bins()
                    if b in bin.name()
                ][0]
                done_bin_lst.append(bin)
            else:
                create_bin = Bin(b)
                done_bin_lst[i - 1].addItem(create_bin)
                done_bin_lst.append(create_bin)

        elif i == len(bin_name) - 1:
            if b in [bin.name() for bin in done_bin_lst[i - 1].bins()]:
                bin = [
                    bin for bin in done_bin_lst[i - 1].bins()
                    if b in bin.name()
                ][0]
                done_bin_lst.append(bin)
            else:
                create_bin = Bin(b)
                done_bin_lst[i - 1].addItem(create_bin)
                done_bin_lst.append(create_bin)
    # print [bin.name() for bin in clipsBin.bins()]
    return done_bin_lst[-1]


def split_by_client_version(string, env=None):
    if not env:
        env = ft_utils.Env()

    client_letter, client_digits = env.get_version_type('client')
    regex = "[/_.]" + client_letter + "\d+"
    try:
        matches = re.findall(regex, string, re.IGNORECASE)
        return string.split(matches[0])
    except Exception, e:
        print e
        return None
