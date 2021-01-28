#! python3
import sys
import avalon.api as avalon
import pype


def main():
    import pype.hosts.resolve as bmdvr
    # Registers pype's Global pyblish plugins
    pype.install()

    # activate resolve from pype
    avalon.install(bmdvr)

    fpath = r"C:\CODE\_PYPE_testing\testing_data\2d_shots\sh010\plate_sh010.00999.exr"
    media_pool_item = bmdvr.create_media_pool_item(fpath)
    print(media_pool_item)

    track_item = bmdvr.create_timeline_item(media_pool_item)
    print(track_item)


if __name__ == "__main__":
    result = main()
    sys.exit(not bool(result))
