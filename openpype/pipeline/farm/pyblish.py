from openpype.lib import Logger
import attr


@attr.s
class InstanceSkeleton(object):
    family = attr.ib(factory=)

def remap_source(source, anatomy):
    success, rootless_path = (
        anatomy.find_root_template_from_path(source)
    )
    if success:
        source = rootless_path
    else:
        # `rootless_path` is not set to `source` if none of roots match
        log = Logger.get_logger("farm_publishing")
        log.warning((
                        "Could not find root path for remapping \"{}\"."
                        " This may cause issues."
                    ).format(source))
    return source

def get_skeleton_instance()
    instance_skeleton_data = {
        "family": family,
        "subset": subset,
        "families": families,
        "asset": asset,
        "frameStart": start,
        "frameEnd": end,
        "handleStart": handle_start,
        "handleEnd": handle_end,
        "frameStartHandle": start - handle_start,
        "frameEndHandle": end + handle_end,
        "comment": instance.data["comment"],
        "fps": fps,
        "source": source,
        "extendFrames": data.get("extendFrames"),
        "overrideExistingFrame": data.get("overrideExistingFrame"),
        "pixelAspect": data.get("pixelAspect", 1),
        "resolutionWidth": data.get("resolutionWidth", 1920),
        "resolutionHeight": data.get("resolutionHeight", 1080),
        "multipartExr": data.get("multipartExr", False),
        "jobBatchName": data.get("jobBatchName", ""),
        "useSequenceForReview": data.get("useSequenceForReview", True),
        # map inputVersions `ObjectId` -> `str` so json supports it
        "inputVersions": list(map(str, data.get("inputVersions", [])))
    }