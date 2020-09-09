import subprocess
import os
from .log import PypeLogger as Logger


def execute(args,
            silent=False,
            cwd=None,
            env=None,
            shell=None):
    """ Execute command as process.

        This will execute given command as process, monitor its output
        and log it appropriately.

        .. seealso:: :mod:`subprocess` module in Python

        :param args: list of arguments passed to process
        :type args: list
        :param silent: control ouput of executed process
        :type silent: bool
        :param cwd: current working directory for process
        :type cwd: string
        :param env: environment variables for process
        :type env: dict
        :param shell: use shell to execute, default is no
        :type shell: bool
        :returns: return code of process
        :rtype: int
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
