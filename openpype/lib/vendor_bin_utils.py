import os
import logging
import platform
import subprocess

from openpype import AYON_SERVER_ENABLED

log = logging.getLogger("Vendor utils")


class CachedToolPaths:
    """Cache already used and discovered tools and their executables.

    Discovering path can take some time and can trigger subprocesses so it's
    better to cache the paths on first get.
    """

    _cached_paths = {}

    @classmethod
    def is_tool_cached(cls, tool):
        return tool in cls._cached_paths

    @classmethod
    def get_executable_path(cls, tool):
        return cls._cached_paths.get(tool)

    @classmethod
    def cache_executable_path(cls, tool, path):
        cls._cached_paths[tool] = path


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
        Union[str, None]: Full path to executable with extension which was
            found otherwise None.
    """

    # Skip if passed path is file
    if is_file_executable(executable):
        return executable

    low_platform = platform.system().lower()
    _, ext = os.path.splitext(executable)

    # Prepare extensions to check
    exts = set()
    if ext:
        exts.add(ext.lower())

    else:
        # Add other possible extension variants only if passed executable
        #   does not have any
        if low_platform == "windows":
            exts |= {".exe", ".ps1", ".bat"}
            for ext in os.getenv("PATHEXT", "").split(os.pathsep):
                exts.add(ext.lower())

        else:
            exts |= {".sh"}

    # Executable is a path but there may be missing extension
    #   - this can happen primarily on windows where
    #       e.g. "ffmpeg" should be "ffmpeg.exe"
    exe_dir, exe_filename = os.path.split(executable)
    if exe_dir and os.path.isdir(exe_dir):
        for filename in os.listdir(exe_dir):
            filepath = os.path.join(exe_dir, filename)
            basename, ext = os.path.splitext(filename)
            if (
                basename == exe_filename
                and ext.lower() in exts
                and is_file_executable(filepath)
            ):
                return filepath

    # Get paths where to look for executable
    path_str = os.environ.get("PATH", None)
    if path_str is None:
        if hasattr(os, "confstr"):
            path_str = os.confstr("CS_PATH")
        elif hasattr(os, "defpath"):
            path_str = os.defpath

    if not path_str:
        return None

    paths = path_str.split(os.pathsep)
    for path in paths:
        if not os.path.isdir(path):
            continue
        for filename in os.listdir(path):
            filepath = os.path.abspath(os.path.join(path, filename))
            # Filename matches executable exactly
            if filename == executable and is_file_executable(filepath):
                return filepath

            basename, ext = os.path.splitext(filename)
            if (
                basename == executable
                and ext.lower() in exts
                and is_file_executable(filepath)
            ):
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


def find_tool_in_custom_paths(paths, tool, validation_func=None):
    """Find a tool executable in custom paths.

    Args:
        paths (Iterable[str]): Iterable of paths where to look for tool.
        tool (str): Name of tool (binary file) to find in passed paths.
        validation_func (Function): Custom validation function of path.
            Function must expect one argument which is path to executable.
            If not passed only 'find_executable' is used to be able identify
            if path is valid.

    Reuturns:
        Union[str, None]: Path to validated executable or None if was not
            found.
    """

    for path in paths:
        # Skip empty strings
        if not path:
            continue

        # Handle cases when path is just an executable
        #   - it allows to use executable from PATH
        #   - basename must match 'tool' value (without extension)
        extless_path, ext = os.path.splitext(path)
        if extless_path == tool:
            executable_path = find_executable(tool)
            if executable_path and (
                validation_func is None
                or validation_func(executable_path)
            ):
                return executable_path
            continue

        # Normalize path because it should be a path and check if exists
        normalized = os.path.normpath(path)
        if not os.path.exists(normalized):
            continue

        # Note: Path can be both file and directory

        # If path is a file validate it
        if os.path.isfile(normalized):
            basename, ext = os.path.splitext(os.path.basename(path))
            # Check if the filename has actually the sane bane as 'tool'
            if basename == tool:
                executable_path = find_executable(normalized)
                if executable_path and (
                    validation_func is None
                    or validation_func(executable_path)
                ):
                    return executable_path

        # Check if path is a directory and look for tool inside the dir
        if os.path.isdir(normalized):
            executable_path = find_executable(os.path.join(normalized, tool))
            if executable_path and (
                validation_func is None
                or validation_func(executable_path)
            ):
                return executable_path
    return None


def _check_args_returncode(args):
    try:
        kwargs = {}
        if platform.system().lower() == "windows":
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

        if hasattr(subprocess, "DEVNULL"):
            proc = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **kwargs
            )
            proc.wait()
        else:
            with open(os.devnull, "w") as devnull:
                proc = subprocess.Popen(
                    args, stdout=devnull, stderr=devnull, **kwargs
                )
                proc.wait()

    except Exception:
        return False
    return proc.returncode == 0


def _oiio_executable_validation(args):
    """Validate oiio tool executable if can be executed.

    Validation has 2 steps. First is using 'find_executable' to fill possible
    missing extension or fill directory then launch executable and validate
    that it can be executed. For that is used '--help' argument which is fast
    and does not need any other inputs.

    Any possible crash of missing libraries or invalid build should be caught.

    Main reason is to validate if executable can be executed on OS just running
    which can be issue ob linux machines.

    Note:
        It does not validate if the executable is really a oiio tool which
            should be used.

    Args:
        args (Union[str, list[str]]): Arguments to launch tool or
            path to tool executable.

    Returns:
        bool: Filepath is valid executable.
    """

    if not args:
        return False

    if not isinstance(args, list):
        filepath = find_executable(args)
        if not filepath:
            return False
        args = [filepath]
    return _check_args_returncode(args + ["--help"])


def _get_ayon_oiio_tool_args(tool_name):
    try:
        # Use 'ayon-third-party' addon to get ffmpeg arguments
        from ayon_third_party import get_oiio_arguments
    except Exception:
        print("!!! Failed to import 'ayon_third_party' addon.")
        return None

    try:
        return get_oiio_arguments(tool_name)
    except Exception as exc:
        print("!!! Failed to get OpenImageIO args. Reason: {}".format(exc))
    return None


def get_oiio_tools_path(tool="oiiotool"):
    """Path to OpenImageIO tool executables.

    On Windows it adds .exe extension if missing from tool argument.

    Args:
        tool (string): Tool name 'oiiotool', 'maketx', etc.
            Default is "oiiotool".
    """

    if CachedToolPaths.is_tool_cached(tool):
        return CachedToolPaths.get_executable_path(tool)

    if AYON_SERVER_ENABLED:
        args = _get_ayon_oiio_tool_args(tool)
        if args:
            if len(args) > 1:
                raise ValueError(
                    "AYON oiio arguments consist of multiple arguments."
                )
            tool_executable_path = args[0]
            CachedToolPaths.cache_executable_path(tool, tool_executable_path)
            return tool_executable_path

    custom_paths_str = os.environ.get("OPENPYPE_OIIO_PATHS") or ""
    tool_executable_path = find_tool_in_custom_paths(
        custom_paths_str.split(os.pathsep),
        tool,
        _oiio_executable_validation
    )

    if not tool_executable_path:
        oiio_dir = get_vendor_bin_path("oiio")
        if platform.system().lower() == "linux":
            oiio_dir = os.path.join(oiio_dir, "bin")
        default_path = find_executable(os.path.join(oiio_dir, tool))
        if default_path and _oiio_executable_validation(default_path):
            tool_executable_path = default_path

    # Look to PATH for the tool
    if not tool_executable_path:
        from_path = find_executable(tool)
        if from_path and _oiio_executable_validation(from_path):
            tool_executable_path = from_path

    CachedToolPaths.cache_executable_path(tool, tool_executable_path)
    return tool_executable_path


def get_oiio_tools_args(tool_name="oiiotool"):
    """Arguments to launch OpenImageIO tool.

    Args:
        tool_name (str): Tool name 'oiiotool', 'maketx', etc.
            Default is "oiiotool".

    Returns:
        list[str]: List of arguments.
    """

    if AYON_SERVER_ENABLED:
        args = _get_ayon_oiio_tool_args(tool_name)
        if args:
            return args

    path = get_oiio_tools_path(tool_name)
    if path:
        return [path]
    return []


def _ffmpeg_executable_validation(args):
    """Validate ffmpeg tool executable if can be executed.

    Validation has 2 steps. First is using 'find_executable' to fill possible
    missing extension or fill directory then launch executable and validate
    that it can be executed. For that is used '-version' argument which is fast
    and does not need any other inputs.

    Any possible crash of missing libraries or invalid build should be caught.

    Main reason is to validate if executable can be executed on OS just running
    which can be issue ob linux machines.

    Note:
        It does not validate if the executable is really a ffmpeg tool.

    Args:
        args (Union[str, list[str]]): Arguments to launch tool or
            path to tool executable.

    Returns:
        bool: Filepath is valid executable.
    """

    if not args:
        return False

    if not isinstance(args, list):
        filepath = find_executable(args)
        if not filepath:
            return False
        args = [filepath]
    return _check_args_returncode(args + ["--help"])


def _get_ayon_ffmpeg_tool_args(tool_name):
    try:
        # Use 'ayon-third-party' addon to get ffmpeg arguments
        from ayon_third_party import get_ffmpeg_arguments

    except Exception:
        print("!!! Failed to import 'ayon_third_party' addon.")
        return None

    try:
        return get_ffmpeg_arguments(tool_name)
    except Exception as exc:
        print("!!! Failed to get FFmpeg args. Reason: {}".format(exc))
    return None


def get_ffmpeg_tool_path(tool="ffmpeg"):
    """Path to vendorized FFmpeg executable.

    Args:
        tool (str): Tool name 'ffmpeg', 'ffprobe', etc.
            Default is "ffmpeg".

    Returns:
        str: Full path to ffmpeg executable.
    """

    if CachedToolPaths.is_tool_cached(tool):
        return CachedToolPaths.get_executable_path(tool)

    if AYON_SERVER_ENABLED:
        args = _get_ayon_ffmpeg_tool_args(tool)
        if args is not None:
            if len(args) > 1:
                raise ValueError(
                    "AYON ffmpeg arguments consist of multiple arguments."
                )
            tool_executable_path = args[0]
            CachedToolPaths.cache_executable_path(tool, tool_executable_path)
            return tool_executable_path

    custom_paths_str = os.environ.get("OPENPYPE_FFMPEG_PATHS") or ""
    tool_executable_path = find_tool_in_custom_paths(
        custom_paths_str.split(os.pathsep),
        tool,
        _ffmpeg_executable_validation
    )

    if not tool_executable_path:
        ffmpeg_dir = get_vendor_bin_path("ffmpeg")
        if platform.system().lower() == "windows":
            ffmpeg_dir = os.path.join(ffmpeg_dir, "bin")
        tool_path = find_executable(os.path.join(ffmpeg_dir, tool))
        if tool_path and _ffmpeg_executable_validation(tool_path):
            tool_executable_path = tool_path

    # Look to PATH for the tool
    if not tool_executable_path:
        from_path = find_executable(tool)
        if from_path and _ffmpeg_executable_validation(from_path):
            tool_executable_path = from_path

    CachedToolPaths.cache_executable_path(tool, tool_executable_path)
    return tool_executable_path


def get_ffmpeg_tool_args(tool_name="ffmpeg"):
    """Arguments to launch FFmpeg tool.

    Args:
        tool_name (str): Tool name 'ffmpeg', 'ffprobe', exc.
            Default is "ffmpeg".

    Returns:
        list[str]: List of arguments.
    """

    if AYON_SERVER_ENABLED:
        args = _get_ayon_ffmpeg_tool_args(tool_name)
        if args:
            return args

    executable_path = get_ffmpeg_tool_path(tool_name)
    if executable_path:
        return [executable_path]
    return []


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
