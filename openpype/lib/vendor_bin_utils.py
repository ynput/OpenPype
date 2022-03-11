import os
import logging
import platform

log = logging.getLogger("Vendor utils")


def is_file_executable(filepath):
    """Filepath lead to executable file.

    Args:
        filepath(str): Full path to file.
    """
    if not filepath:
        return False

    if os.path.isfile(filepath):
        if os.access(filepath, os.X_OK):
            return True

        log.info(
            "Filepath is not available for execution \"{}\"".format(filepath)
        )
    return False


def find_executable(executable):
    """Find full path to executable.

    Also tries additional extensions if passed executable does not contain one.

    Paths where it is looked for executable is defined by 'PATH' environment
    variable, 'os.confstr("CS_PATH")' or 'os.defpath'.

    Args:
        executable(str): Name of executable with or without extension. Can be
            path to file.

    Returns:
        str: Full path to executable with extension (is file).
        None: When the executable was not found.
    """
    # Skip if passed path is file
    if is_file_executable(executable):
        return executable

    low_platform = platform.system().lower()
    _, ext = os.path.splitext(executable)

    # Prepare variants for which it will be looked
    variants = [executable]
    # Add other extension variants only if passed executable does not have one
    if not ext:
        if low_platform == "windows":
            exts = [".exe", ".ps1", ".bat"]
            for ext in os.getenv("PATHEXT", "").split(os.pathsep):
                ext = ext.lower()
                if ext and ext not in exts:
                    exts.append(ext)
        else:
            exts = [".sh"]

        for ext in exts:
            variant = executable + ext
            if is_file_executable(variant):
                return variant
            variants.append(variant)

    # Get paths where to look for executable
    path_str = os.environ.get("PATH", None)
    if path_str is None:
        if hasattr(os, "confstr"):
            path_str = os.confstr("CS_PATH")
        elif hasattr(os, "defpath"):
            path_str = os.defpath

    if path_str:
        paths = path_str.split(os.pathsep)
        for path in paths:
            for variant in variants:
                filepath = os.path.abspath(os.path.join(path, variant))
                if is_file_executable(filepath):
                    return filepath
    return None


def get_vendor_bin_path(bin_app):
    """Path to OpenPype vendorized binaries.

    Vendorized executables are expected in specific hierarchy inside build or
    in code source.

    "{OPENPYPE_ROOT}/vendor/bin/{name of vendorized app}/{platform}"

    Args:
        bin_app (str): Name of vendorized application.

    Returns:
        str: Path to vendorized binaries folder.
    """
    return os.path.join(
        os.environ["OPENPYPE_ROOT"],
        "vendor",
        "bin",
        bin_app,
        platform.system().lower()
    )


def get_oiio_tools_path(tool="oiiotool"):
    """Path to vendorized OpenImageIO tool executables.

    On Window it adds .exe extension if missing from tool argument.

    Args:
        tool (string): Tool name (oiiotool, maketx, ...).
            Default is "oiiotool".
    """
    oiio_dir = get_vendor_bin_path("oiio")
    return find_executable(os.path.join(oiio_dir, tool))


def get_ffmpeg_tool_path(tool="ffmpeg"):
    """Path to vendorized FFmpeg executable.

    Args:
        tool (string): Tool name (ffmpeg, ffprobe, ...).
            Default is "ffmpeg".

    Returns:
        str: Full path to ffmpeg executable.
    """
    ffmpeg_dir = get_vendor_bin_path("ffmpeg")
    if platform.system().lower() == "windows":
        ffmpeg_dir = os.path.join(ffmpeg_dir, "bin")
    return find_executable(os.path.join(ffmpeg_dir, tool))


def is_oiio_supported():
    """Checks if oiiotool is configured for this platform.

    Returns:
        bool: OIIO tool executable is available.
    """
    loaded_path = oiio_path = get_oiio_tools_path()
    if oiio_path:
        oiio_path = find_executable(oiio_path)

    if not oiio_path:
        log.debug("OIIOTool is not configured or not present at {}".format(
            loaded_path
        ))
        return False
    return True


def get_fps(str_value):
    """Returns (str) value of fps from ffprobe frame format (120/1)"""
    if str_value == "0/0":
        print("WARNING: Source has \"r_frame_rate\" value set to \"0/0\".")
        return "Unknown"

    items = str_value.split("/")
    if len(items) == 1:
        fps = float(items[0])

    elif len(items) == 2:
        fps = float(items[0]) / float(items[1])

    # Check if fps is integer or float number
    if int(fps) == fps:
        fps = int(fps)

    return str(fps)
