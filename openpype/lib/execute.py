import os
import sys
import subprocess
import platform
import json
import tempfile

from .log import PypeLogger as Logger
from .vendor_bin_utils import find_executable

# MSDN process creation flag (Windows only)
CREATE_NO_WINDOW = 0x08000000


def execute(args,
            silent=False,
            cwd=None,
            env=None,
            shell=None):
    """Execute command as process.

    This will execute given command as process, monitor its output
    and log it appropriately.

    .. seealso::

        :mod:`subprocess` module in Python.

    Args:
        args (list): list of arguments passed to process.
        silent (bool): control output of executed process.
        cwd (str): current working directory for process.
        env (dict): environment variables for process.
        shell (bool): use shell to execute, default is no.

    Returns:
        int: return code of process

    """

    log_levels = ['DEBUG:', 'INFO:', 'ERROR:', 'WARNING:', 'CRITICAL:']

    log = Logger().get_logger('execute')
    log.info("Executing ({})".format(" ".join(args)))
    popen = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
        cwd=cwd,
        env=env or os.environ,
        shell=shell
    )

    # Blocks until finished
    while True:
        line = popen.stdout.readline()
        if line == '':
            break
        if silent:
            continue
        line_test = False
        for test_string in log_levels:
            if line.startswith(test_string):
                line_test = True
                break
        if not line_test:
            print(line[:-1])

    log.info("Execution is finishing up ...")

    popen.wait()
    return popen.returncode


def run_subprocess(*args, **kwargs):
    """Convenience method for getting output errors for subprocess.

    Output logged when process finish.

    Entered arguments and keyword arguments are passed to subprocess Popen.

    Args:
        *args: Variable length arument list passed to Popen.
        **kwargs : Arbitrary keyword arguments passed to Popen. Is possible to
            pass `logging.Logger` object under "logger" if want to use
            different than lib's logger.

    Returns:
        str: Full output of subprocess concatenated stdout and stderr.

    Raises:
        RuntimeError: Exception is raised if process finished with nonzero
            return code.
    """

    # Get environents from kwarg or use current process environments if were
    # not passed.
    env = kwargs.get("env") or os.environ
    # Make sure environment contains only strings
    filtered_env = {str(k): str(v) for k, v in env.items()}

    # Use lib's logger if was not passed with kwargs.
    logger = kwargs.pop("logger", None)
    if logger is None:
        logger = Logger.get_logger("run_subprocess")

    # set overrides
    kwargs['stdout'] = kwargs.get('stdout', subprocess.PIPE)
    kwargs['stderr'] = kwargs.get('stderr', subprocess.PIPE)
    kwargs['stdin'] = kwargs.get('stdin', subprocess.PIPE)
    kwargs['env'] = filtered_env

    proc = subprocess.Popen(*args, **kwargs)

    full_output = ""
    _stdout, _stderr = proc.communicate()
    if _stdout:
        _stdout = _stdout.decode("utf-8")
        full_output += _stdout
        logger.debug(_stdout)

    if _stderr:
        _stderr = _stderr.decode("utf-8")
        # Add additional line break if output already contains stdout
        if full_output:
            full_output += "\n"
        full_output += _stderr
        logger.info(_stderr)

    if proc.returncode != 0:
        exc_msg = "Executing arguments was not successful: \"{}\"".format(args)
        if _stdout:
            exc_msg += "\n\nOutput:\n{}".format(_stdout)

        if _stderr:
            exc_msg += "Error:\n{}".format(_stderr)

        raise RuntimeError(exc_msg)

    return full_output


def clean_envs_for_openpype_process(env=None):
    """Modify environemnts that may affect OpenPype process.

    Main reason to implement this function is to pop PYTHONPATH which may be
    affected by in-host environments.
    """
    if env is None:
        env = os.environ
    return {
        key: value
        for key, value in env.items()
        if key not in ("PYTHONPATH",)
    }


def run_openpype_process(*args, **kwargs):
    """Execute OpenPype process with passed arguments and wait.

    Wrapper for 'run_process' which prepends OpenPype executable arguments
    before passed arguments and define environments if are not passed.

    Values from 'os.environ' are used for environments if are not passed.
    They are cleaned using 'clean_envs_for_openpype_process' function.

    Example:
    ```
    run_openpype_process("run", "<path to .py script>")
    ```

    Args:
        *args (tuple): OpenPype cli arguments.
        **kwargs (dict): Keyword arguments for for subprocess.Popen.
    """
    args = get_openpype_execute_args(*args)
    env = kwargs.pop("env", None)
    # Keep env untouched if are passed and not empty
    if not env:
        # Skip envs that can affect OpenPype process
        # - fill more if you find more
        env = clean_envs_for_openpype_process(os.environ)
    return run_subprocess(args, env=env, **kwargs)


def run_detached_process(args, **kwargs):
    """Execute process with passed arguments as separated process.

    Values from 'os.environ' are used for environments if are not passed.
    They are cleaned using 'clean_envs_for_openpype_process' function.

    Example:
    ```
    run_detached_openpype_process("run", "<path to .py script>")
    ```

    Args:
        *args (tuple): OpenPype cli arguments.
        **kwargs (dict): Keyword arguments for for subprocess.Popen.

    Returns:
        subprocess.Popen: Pointer to launched process but it is possible that
            launched process is already killed (on linux).
    """
    env = kwargs.pop("env", None)
    # Keep env untouched if are passed and not empty
    if not env:
        env = os.environ

    # Create copy of passed env
    kwargs["env"] = {k: v for k, v in env.items()}

    low_platform = platform.system().lower()
    if low_platform == "darwin":
        new_args = ["open", "-na", args.pop(0), "--args"]
        new_args.extend(args)
        args = new_args

    elif low_platform == "windows":
        flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
        )
        kwargs["creationflags"] = flags

        if not sys.stdout:
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL

    elif low_platform == "linux" and get_linux_launcher_args() is not None:
        json_data = {
            "args": args,
            "env": kwargs.pop("env")
        }
        json_temp = tempfile.NamedTemporaryFile(
            mode="w", prefix="op_app_args", suffix=".json", delete=False
        )
        json_temp.close()
        json_temp_filpath = json_temp.name
        with open(json_temp_filpath, "w") as stream:
            json.dump(json_data, stream)

        new_args = get_linux_launcher_args()
        new_args.append(json_temp_filpath)

        # Create mid-process which will launch application
        process = subprocess.Popen(new_args, **kwargs)
        # Wait until the process finishes
        #   - This is important! The process would stay in "open" state.
        process.wait()
        # Remove the temp file
        os.remove(json_temp_filpath)
        # Return process which is already terminated
        return process

    process = subprocess.Popen(args, **kwargs)
    return process


def path_to_subprocess_arg(path):
    """Prepare path for subprocess arguments.

    Returned path can be wrapped with quotes or kept as is.
    """
    return subprocess.list2cmdline([path])


def get_pype_execute_args(*args):
    """Backwards compatible function for 'get_openpype_execute_args'."""
    import traceback

    log = Logger.get_logger("get_pype_execute_args")
    stack = "\n".join(traceback.format_stack())
    log.warning((
        "Using deprecated function 'get_pype_execute_args'. Called from:\n{}"
    ).format(stack))
    return get_openpype_execute_args(*args)


def get_openpype_execute_args(*args):
    """Arguments to run pype command.

    Arguments for subprocess when need to spawn new pype process. Which may be
    needed when new python process for pype scripts must be executed in build
    pype.

    ## Why is this needed?
    Pype executed from code has different executable set to virtual env python
    and must have path to script as first argument which is not needed for
    build pype.

    It is possible to pass any arguments that will be added after pype
    executables.
    """
    pype_executable = os.environ["OPENPYPE_EXECUTABLE"]
    pype_args = [pype_executable]

    executable_filename = os.path.basename(pype_executable)
    if "python" in executable_filename.lower():
        pype_args.append(
            os.path.join(os.environ["OPENPYPE_ROOT"], "start.py")
        )

    if args:
        pype_args.extend(args)

    return pype_args


def get_linux_launcher_args(*args):
    """Path to application mid process executable.

    This function should be able as arguments are different when used
    from code and build.

    It is possible that this function is used in OpenPype build which does
    not have yet the new executable. In that case 'None' is returned.

    Args:
        args (iterable): List of additional arguments added after executable
            argument.

    Returns:
        list: Executables with possible positional argument to script when
            called from code.
    """
    filename = "app_launcher"
    openpype_executable = os.environ["OPENPYPE_EXECUTABLE"]

    executable_filename = os.path.basename(openpype_executable)
    if "python" in executable_filename.lower():
        script_path = os.path.join(
            os.environ["OPENPYPE_ROOT"],
            "{}.py".format(filename)
        )
        launch_args = [openpype_executable, script_path]
    else:
        new_executable = os.path.join(
            os.path.dirname(openpype_executable),
            filename
        )
        executable_path = find_executable(new_executable)
        if executable_path is None:
            return None
        launch_args = [executable_path]

    if args:
        launch_args.extend(args)

    return launch_args
