# Test for backward compatibility of restructure of lib.py into lib library
# Contains simple imports that should still work


def test_backward_compatibility(printer):
    printer("Test if imports still work")
    try:
        from pype.lib import filter_pyblish_plugins
        from pype.lib import execute_hook
        from pype.lib import PypeHook

        from pype.lib import get_latest_version
        from pype.lib import ApplicationLaunchFailed
        from pype.lib import launch_application
        from pype.lib import ApplicationAction

        from pype.lib import get_ffmpeg_tool_path
        from pype.lib import get_last_version_from_path
        from pype.lib import get_paths_from_environ
        from pype.lib import get_version_from_path
        from pype.lib import version_up

        from pype.lib import is_latest
        from pype.lib import any_outdated
        from pype.lib import get_asset
        from pype.lib import get_hierarchy
        from pype.lib import get_linked_assets
        from pype.lib import get_latest_version
        from pype.lib import ffprobe_streams

        from pype.hosts.fusion.lib import switch_item

        from pype.lib import source_hash
        from pype.lib import _subprocess

    except ImportError as e:
        raise
