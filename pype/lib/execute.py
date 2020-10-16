import logging
import os
import subprocess

from .log import PypeLogger as Logger

log = logging.getLogger(__name__)


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


def _subprocess(*args, **kwargs):
    """Convenience method for getting output errors for subprocess.

    .. seealso:: :mod:`subprocess`

    """
    # make sure environment contains only strings
    if not kwargs.get("env"):
        filtered_env = {k: str(v) for k, v in os.environ.items()}
    else:
        filtered_env = {k: str(v) for k, v in kwargs.get("env").items()}

    # set overrides
    kwargs['stdout'] = kwargs.get('stdout', subprocess.PIPE)
    kwargs['stderr'] = kwargs.get('stderr', subprocess.STDOUT)
    kwargs['stdin'] = kwargs.get('stdin', subprocess.PIPE)
    kwargs['env'] = filtered_env

    proc = subprocess.Popen(*args, **kwargs)

    output, error = proc.communicate()

    if output:
        output = output.decode("utf-8")
        output += "\n"
        for line in output.strip().split("\n"):
            log.info(line)

    if error:
        error = error.decode("utf-8")
        error += "\n"
        for line in error.strip().split("\n"):
            log.error(line)

    if proc.returncode != 0:
        raise ValueError(
            "\"{}\" was not successful:\nOutput: {}\nError: {}".format(
                args, output, error))
    return output
