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


urls = ["keyring://file/environment/foo=bar", "keyring://foo=bar"]
ids = ["fullpath", "no_namespace"]
@pytest.mark.parametrize("url", urls, ids=ids)
def test_set_get(url):
    cmd_args = ["setvalue", url]
    _, popen_stderr = _run_cli_command(cmd_args)

    assert not popen_stderr

    cmd_args = ["getvalue", url]
    popen_stdout, popen_stderr = _run_cli_command(cmd_args)
    exp_msg = "getvalue:bar"
    assert exp_msg in str(popen_stdout)


def test_get_unknown():
    cmd_args = ["getvalue", "keyring://bar"]
    popen_std, popen_stderr = _run_cli_command(cmd_args)
    exp_msg = "bar does not exist"
    assert exp_msg in str(popen_std)
    exp_msg = "getvalue:None"
    assert exp_msg in str(popen_std)


def _run_cli_command(cmd_args):
    args = [sys.executable,
            os.path.join(os.environ["OPENPYPE_ROOT"], "start.py")]
    args.extend(cmd_args)

    popen = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        popen_stdout, popen_stderr = popen.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        popen.kill()
        popen_stdout, popen_stderr = popen.communicate()

    return popen_stdout, popen_stderr
