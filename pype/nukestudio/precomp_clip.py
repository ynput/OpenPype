import hiero.core
import hiero.ui

import re
import os


def create_nk_script_clips(script_lst, seq=None):
    '''
    nk_scripts is list of dictionaries like:
    [{
        'path': 'P:/Jakub_testy_pipeline/test_v01.nk',
        'name': 'test',
        'handles': 10,
        'handleStart': 15, # added asymetrically to handles
        'handleEnd': 10, # added asymetrically to handles
        "clipIn": 16,
        "frameStart": 991,
        "frameEnd": 1023,
        'task': 'Comp-tracking',
        'work_dir': 'VFX_PR',
        'shot': '00010'
    }]
    '''

    proj = hiero.core.projects()[-1]
    root = proj.clipsBin()

    if not seq:
        seq = hiero.core.Sequence('NewSequences')
        root.addItem(hiero.core.BinItem(seq))
    # todo will ned to define this better
    # track = seq[1]  # lazy example to get a destination#  track
    clips_lst = []
    for nk in script_lst:
        task_path = '/'.join([nk['work_dir'], nk['shot'], nk['task']])
        bin = create_bin_in_project(task_path, proj)

        if nk['task'] not in seq.videoTracks():
            track = hiero.core.VideoTrack(nk['task'])
            seq.addTrack(track)
        else:
            track = seq.tracks(nk['task'])

        # create slip media
        print("__ path: `{}`".format(nk['path']))

        media = hiero.core.MediaSource(nk['path'])
        media_in = int(media.startTime() or 0)
        media_duration = int(media.duration() or 0)

        handle_start = nk.get("handleStart") or nk['handles']
        handle_end = nk.get("handleEnd") or nk['handles']

        if media_in:
            source_in = media_in + handle_start
        else:
            source_in = nk["frameStart"] + handle_start

        if media_duration:
            source_out = (media_in + media_duration - 1) - handle_end
        else:
            source_out = nk["frameEnd"] - handle_end

        print("__ media: `{}`".format(media))
        print("__ media_in: `{}`".format(media_in))
        print("__ media_duration : `{}`".format(media_duration))
        print("__ source_in: `{}`".format(source_in))
        print("__ source_out : `{}`".format(source_out))

        source = hiero.core.Clip(media)
        print("__ source : `{}`".format(source))
        print("__ source.sourceIn(): `{}`".format(source.sourceIn()))

        name = os.path.basename(os.path.splitext(nk['path'])[0])
        split_name = split_by_client_version(name)[0] or name

        print("__ split_name: `{}`".format(split_name))

        # add to bin as clip item
        items_in_bin = [b.name() for b in bin.items()]
        if split_name not in items_in_bin:
            binItem = hiero.core.BinItem(source)
            bin.addItem(binItem)

        print("__ bin.items(): `{}`".format(bin.items()))

        new_source = [
            item for item in bin.items() if split_name in item.name()
        ][0].items()[0].item()

        print("__ new_source: `{}`".format(new_source))
        print("__ new_source: `{}`".format(new_source))

        # add to track as clip item
        trackItem = hiero.core.TrackItem(split_name, hiero.core.TrackItem.kVideo)
        trackItem.setSource(new_source)
        trackItem.setSourceIn(source_in)
        trackItem.setSourceOut(source_out)
        trackItem.setSourceIn(source_in)
        trackItem.setTimelineIn(nk["clipIn"])
        trackItem.setTimelineOut(nk["clipIn"] + (source_out - source_in))
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
        project = hiero.core.projects()[-1]
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
                create_bin = hiero.core.Bin(b)
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
                create_bin = hiero.core.Bin(b)
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
                create_bin = hiero.core.Bin(b)
                done_bin_lst[i - 1].addItem(create_bin)
                done_bin_lst.append(create_bin)
    # print [bin.name() for bin in clipsBin.bins()]
    return done_bin_lst[-1]


def split_by_client_version(string):
    regex = r"[/_.]v\d+"
    try:
        matches = re.findall(regex, string, re.IGNORECASE)
        return string.split(matches[0])
    except Exception as e:
        print(e)
        return None


script_lst = [{
    'path': 'C:/Users/hubert/_PYPE_testing/projects/D001_projectx/episodes/ep120/ep120sq01/120sh020/publish/plates/platesMain/v023/prjx_120sh020_platesMain_v023.nk',
    'name': '120sh020_platesMain',
    'handles': 10,
    'handleStart': 10,
    'handleEnd': 10,
    "clipIn": 16,
    "frameStart": 991,
    "frameEnd": 1023,
    'task': 'platesMain',
    'work_dir': 'shots',
    'shot': '120sh020'
}]
