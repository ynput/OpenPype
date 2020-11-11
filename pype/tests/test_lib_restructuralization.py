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
        from pype.lib import get_avalon_database
        from pype.lib import set_io_database

        from pype.lib import get_ffmpeg_tool_path
        from pype.lib import get_last_version_from_path
        from pype.lib import get_paths_from_environ
        from pype.lib import get_version_from_path
        from pype.lib import version_up

    except ImportError as e:
        raise
