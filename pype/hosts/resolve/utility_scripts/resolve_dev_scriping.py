#!/usr/bin/env python


def main():
    import pype.hosts.resolve as bmdvr
    bmdvr.utils.get_resolve_module()

    tracks = list()
    track_type = "video"
    sequence = bmdvr.get_current_sequence()

    # get all tracks count filtered by track type
    selected_track_count = sequence.GetTrackCount(track_type)

    # loop all tracks and get items
    for track_index in range(1, (int(selected_track_count) + 1)):
        track_name = sequence.GetTrackName("video", track_index)
        tracks.append(track_name)


if __name__ == "__main__":
    main()
