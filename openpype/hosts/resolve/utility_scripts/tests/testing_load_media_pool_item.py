#! python3
import avalon.api as avalon
import openpype
import openpype.hosts.resolve as bmdvr


def file_processing(fpath):
    media_pool_item = bmdvr.create_media_pool_item(fpath)
    print(media_pool_item)

    track_item = bmdvr.create_timeline_item(media_pool_item)
    print(track_item)


if __name__ == "__main__":
    path = "C:/CODE/__openpype_projects/jtest03dev/shots/sq01/mainsq01sh030/publish/plate/plateMain/v006/jt3d_mainsq01sh030_plateMain_v006.0996.exr"

    openpype.install()
    # activate resolve from openpype
    avalon.install(bmdvr)

    file_processing(path)