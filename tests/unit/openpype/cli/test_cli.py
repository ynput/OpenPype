import pytest
import os
import sys
import subprocess


def test_setvalue_broken_url():
    cmd_args = ["setvalue", "broken:/foo=bar"]
    _, popen_stderr = _run_cli_command(cmd_args)
    exp_msg = "must contain general location"
    assert exp_msg in str(popen_stderr)


def test_setvalue_missing_value():
    cmd_args = ["setvalue", "keyring://foo"]
    _, popen_stderr = _run_cli_command(cmd_args)
    exp_msg = "must contain value"
    assert exp_msg in str(popen_stderr)


def _run_cli_command(cmd_args):
    args = [sys.executable,
            os.path.join(os.environ["OPENPYPE_ROOT"], "start.py")]
    args.extend(cmd_args)

    popen = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    popen_stdout, popen_stderr = popen.communicate()
    return popen_stdout, popen_stderr