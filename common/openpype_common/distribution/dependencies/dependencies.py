import os.path
import toml
import abc
import six
from packaging import version
import subprocess
import logging
import platform


@six.add_metaclass(abc.ABCMeta)
class AbstractTomlProvider:
    """Interface class to base real toml data providers."""
    @abc.abstractmethod
    def get_toml(self):
        """
            Returns dict containing toml information


            Returns:
                (dict)
        """
        pass


class FileTomlProvider(AbstractTomlProvider):
    """Class that parses toml from 'source_url' into dictionary."""
    def __init__(self, source_url):
        self.source_url = source_url

    def get_toml(self):
        if not os.path.exists(self.source_url):
            raise ValueError(f"{self.source_url} doesn't exist. "
                             "Provide path to real toml.")

        with open(self.source_url) as fp:
            return toml.load(fp)


def is_valid_toml(toml):
    """Validates that 'toml' contains all required fields.

    Args:
        toml (dict)
    Returns:
        True if all required keys present
    Raises:
        KeyError
    """
    required_fields = ["tool.poetry"]

    for field in required_fields:
        fields = field.split('.')
        value = toml
        while fields:
            key = fields.pop(0)
            value = value.get(key)

            if not value:
                raise KeyError(f"Toml content must contain {field}")

    return True


def merge_tomls(main_toml, addon_toml):
    """Add dependencies from 'addon_toml' to 'main_toml'.

    Looks for mininimal compatible version from both tomls.

    Handles sections:
        - ["tool"]["poetry"]["dependencies"]
        - ["tool"]["poetry"][""-dependencies"]
        - ["openpype"]["thirdparty"]

    Returns:
        (dict): updated 'main_toml' with additional/updated dependencies
    """
    dependency_keyes = ["dependencies", "dev-dependencies"]
    for key in dependency_keyes:
        main_poetry = main_toml["tool"]["poetry"][key]
        addon_poetry = addon_toml["tool"]["poetry"][key]
        for dependency, dep_version in addon_poetry.items():
            if main_poetry.get(dependency):
                main_version = main_poetry[dependency]
                # max ==  smaller from both versions
                dep_version = max(version.parse(dep_version),
                                  version.parse(main_version))

            main_poetry[dependency] = str(dep_version)

        main_toml["tool"]["poetry"][key] = main_poetry

    # handle thirdparty
    platform_name = platform.system().lower()

    addon_poetry = addon_toml["openpype"]["thirdparty"]
    for dependency, dep_info in addon_poetry.items():
        main_poetry = main_toml["openpype"]["thirdparty"]  # reset level
        if main_poetry.get(dependency):
            if dep_info.get(platform_name):
                dep_version = dep_info[platform_name]["version"]
                main_version = (main_poetry[dependency]
                                           [platform_name]
                                           ["version"])
            else:
                dep_version = dep_info["version"]
                main_version = main_poetry[dependency]["version"]

            if version.parse(dep_version) > version.parse(main_version):
                dep_info = main_poetry[dependency]

        main_poetry[dependency] = dep_info

    main_toml["openpype"]["thirdparty"] = main_poetry

    return main_toml


def get_full_toml(base_toml_data, addon_folders):
    """Loops through list of local addon folder paths to create full .toml

    Full toml is used to calculate set of python dependencies for all enabled
    addons.

    Args:
        base_toml_data (dict): content of pyproject.toml in the root
        addon_folders (list): of local paths to addons
    Returns:
        (dict) updated base .toml
    """
    for addon_folder in addon_folders:
        addon_toml_path = os.path.join(addon_folder, "pyproject.toml")
        if not os.path.exists(addon_toml_path):
            print(f"{addon_toml_path} doesn't exist, no dependencies added.")
            continue
        addon_toml = FileTomlProvider(addon_toml_path).get_toml()
        base_toml_data = merge_tomls(base_toml_data, addon_toml)

    return base_toml_data


def prepare_new_venv(full_toml_data, venv_folder):
    """Let Poetry create new venv in 'venv_folder' from 'full_toml_data'.

    Args:
        full_toml_data (dict): toml representation calculated based on basic
            .toml + all addon tomls
        venv_folder (str): path where venv should be created
    Raises:
        RuntimeError: Exception is raised if process finished with nonzero
            return code.
    """
    toml_path = os.path.join(venv_folder, "pyproject.toml")

    with open(toml_path, 'w') as fp:
        fp.write(toml.dumps(full_toml_data))

    low_platform = platform.system().lower()

    if low_platform == "windows":
        ext = "ps1"
        executable = "powershell"
    else:
        ext = "sh"
        executable = "bash"

    pype_root = os.path.abspath('../../../../..')
    create_env_script_path = os.path.join(pype_root, "tools",
                                          f"create_env.{ext}")
    cmd_args = [
        executable,
        create_env_script_path,
        "-venv_path", venv_folder
    ]

    run_subprocess(cmd_args)


def zip_venv(venv_folder, zip_destination_path):
    """Zips newly created venv to single .zip file."""
    # RemoteFileHandler.unzip(addon_zip_path, destination)
    raise NotImplementedError


def upload_zip_venv(zip_path, server_endpoint):
    """Uploads zipped venv to the server for distribution.

    Args:
        zip_path (str): local path to zipped venv
        server_endpoint (str)

    """
    raise NotImplementedError


# TODO copy from openpype.lib.execute, could be imported directly??
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
        logger = logging.getLogger("dependencies_tool")

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
