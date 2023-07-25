# -*- coding: utf-8 -*-
"""Unreal launching and project tools."""

import json
import os
import platform
import re
import subprocess
from collections import OrderedDict
from distutils import dir_util
from pathlib import Path
from typing import List

from openpype.settings import get_project_settings


def get_engine_versions(env=None):
    """Detect Unreal Engine versions.

    This will try to detect location and versions of installed Unreal Engine.
    Location can be overridden by `UNREAL_ENGINE_LOCATION` environment
    variable.

    .. deprecated:: 3.15.4

    Args:
        env (dict, optional): Environment to use.

    Returns:
        OrderedDict: dictionary with version as a key and dir as value.
            so the highest version is first.

    Example:
        >>> get_engine_versions()
        {
            "4.23": "C:/Epic Games/UE_4.23",
            "4.24": "C:/Epic Games/UE_4.24"
        }

    """
    env = env or os.environ
    engine_locations = {}
    try:
        root, dirs, _ = next(os.walk(env["UNREAL_ENGINE_LOCATION"]))

        for directory in dirs:
            if directory.startswith("UE"):
                try:
                    ver = re.split(r"[-_]", directory)[1]
                except IndexError:
                    continue
                engine_locations[ver] = os.path.join(root, directory)
    except KeyError:
        # environment variable not set
        pass
    except OSError:
        # specified directory doesn't exist
        pass
    except StopIteration:
        # specified directory doesn't exist
        pass

    # if we've got something, terminate auto-detection process
    if engine_locations:
        return OrderedDict(sorted(engine_locations.items()))

    # else kick in platform specific detection
    if platform.system().lower() == "windows":
        return OrderedDict(sorted(_win_get_engine_versions().items()))
    if platform.system().lower() == "linux":
        # on linux, there is no installation and getting Unreal Engine involves
        # git clone. So we'll probably depend on `UNREAL_ENGINE_LOCATION`.
        pass
    if platform.system().lower() == "darwin":
        return OrderedDict(sorted(_darwin_get_engine_version().items()))

    return OrderedDict()


def get_editor_exe_path(engine_path: Path, engine_version: str) -> Path:
    """Get UE Editor executable path."""
    ue_path = engine_path / "Engine/Binaries"
    if platform.system().lower() == "windows":
        if engine_version.split(".")[0] == "4":
            ue_path /= "Win64/UE4Editor.exe"
        elif engine_version.split(".")[0] == "5":
            ue_path /= "Win64/UnrealEditor.exe"

    elif platform.system().lower() == "linux":
        ue_path /= "Linux/UE4Editor"

    elif platform.system().lower() == "darwin":
        ue_path /= "Mac/UE4Editor"

    return ue_path


def _win_get_engine_versions():
    """Get Unreal Engine versions on Windows.

    If engines are installed via Epic Games Launcher then there is:
    `%PROGRAMDATA%/Epic/UnrealEngineLauncher/LauncherInstalled.dat`
    This file is JSON file listing installed stuff, Unreal engines
    are marked with `"AppName" = "UE_X.XX"`` like `UE_4.24`

    .. deprecated:: 3.15.4

    Returns:
        dict: version as a key and path as a value.

    """
    install_json_path = os.path.join(
        os.getenv("PROGRAMDATA"),
        "Epic",
        "UnrealEngineLauncher",
        "LauncherInstalled.dat",
    )

    return _parse_launcher_locations(install_json_path)


def _darwin_get_engine_version() -> dict:
    """Get Unreal Engine versions on MacOS.

    It works the same as on Windows, just JSON file location is different.

    .. deprecated:: 3.15.4

    Returns:
        dict: version as a key and path as a value.

    See Also:
        :func:`_win_get_engine_versions`.

    """
    install_json_path = os.path.join(
        os.getenv("HOME"),
        "Library",
        "Application Support",
        "Epic",
        "UnrealEngineLauncher",
        "LauncherInstalled.dat",
    )

    return _parse_launcher_locations(install_json_path)


def _parse_launcher_locations(install_json_path: str) -> dict:
    """This will parse locations from json file.

    .. deprecated:: 3.15.4

    Args:
        install_json_path (str): Path to `LauncherInstalled.dat`.

    Returns:
        dict: with unreal engine versions as keys and
            paths to those engine installations as value.

    """
    engine_locations = {}
    if os.path.isfile(install_json_path):
        with open(install_json_path, "r") as ilf:
            try:
                install_data = json.load(ilf)
            except json.JSONDecodeError as e:
                raise Exception(
                    "Invalid `LauncherInstalled.dat file. `"
                    "Cannot determine Unreal Engine location."
                ) from e

        for installation in install_data.get("InstallationList", []):
            if installation.get("AppName").startswith("UE_"):
                ver = installation.get("AppName").split("_")[1]
                engine_locations[ver] = installation.get("InstallLocation")

    return engine_locations


def create_unreal_project(project_name: str,
                          unreal_project_name: str,
                          ue_version: str,
                          pr_dir: Path,
                          engine_path: Path,
                          dev_mode: bool = False,
                          env: dict = None) -> None:
    """This will create `.uproject` file at specified location.

    As there is no way I know to create a project via command line, this is
    easiest option. Unreal project file is basically a JSON file. If we find
    the `AYON_UNREAL_PLUGIN` environment variable we assume this is the
    location of the Integration Plugin and we copy its content to the project
    folder and enable this plugin.

    Args:
        project_name (str): Name of the project in AYON.
        unreal_project_name (str): Name of the project in Unreal.
        ue_version (str): Unreal engine version (like 4.23).
        pr_dir (Path): Path to directory where project will be created.
        engine_path (Path): Path to Unreal Engine installation.
        dev_mode (bool, optional): Flag to trigger C++ style Unreal project
            needing Visual Studio and other tools to compile plugins from
            sources. This will trigger automatically if `Binaries`
            directory is not found in plugin folders as this indicates
            this is only source distribution of the plugin. Dev mode
            is also set in Settings.
        env (dict, optional): Environment to use. If not set, `os.environ`.

    Throws:
        NotImplementedError: For unsupported platforms.

    Returns:
        None

    Deprecated:
        since 3.16.0

    """
    env = env or os.environ

    preset = get_project_settings(project_name)["unreal"]["project_setup"]
    ue_id = ".".join(ue_version.split(".")[:2])
    # get unreal engine identifier
    # -------------------------------------------------------------------------
    # FIXME (antirotor): As of 4.26 this is problem with UE4 built from
    # sources. In that case Engine ID is calculated per machine/user and not
    # from Engine files as this code then reads. This then prevents UE4
    # to directly open project as it will complain about project being
    # created in different UE4 version. When user convert such project
    # to his UE4 version, Engine ID is replaced in uproject file. If some
    # other user tries to open it, it will present him with similar error.

    # engine_path should be the location of UE_X.X folder

    ue_editor_exe: Path = get_editor_exe_path(engine_path, ue_version)
    cmdlet_project: Path = get_path_to_cmdlet_project(ue_version)

    project_file = pr_dir / f"{unreal_project_name}.uproject"

    print("--- Generating a new project ...")
    commandlet_cmd = [f'{ue_editor_exe.as_posix()}',
                      f'{cmdlet_project.as_posix()}',
                      f'-run=AyonGenerateProject',
                      f'{project_file.resolve().as_posix()}']

    if dev_mode or preset["dev_mode"]:
        commandlet_cmd.append('-GenerateCode')

    gen_process = subprocess.Popen(commandlet_cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    for line in gen_process.stdout:
        print(line.decode(), end='')
    gen_process.stdout.close()
    return_code = gen_process.wait()

    if return_code and return_code != 0:
        raise RuntimeError(
            (f"Failed to generate '{unreal_project_name}' project! "
             f"Exited with return code {return_code}"))

    print("--- Project has been generated successfully.")

    with open(project_file.as_posix(), mode="r+") as pf:
        pf_json = json.load(pf)
        pf_json["EngineAssociation"] = get_build_id(engine_path, ue_version)
        pf.seek(0)
        json.dump(pf_json, pf, indent=4)
        pf.truncate()
        print(f'--- Engine ID has been written into the project file')

    if dev_mode or preset["dev_mode"]:
        u_build_tool = get_path_to_ubt(engine_path, ue_version)

        arch = "Win64"
        if platform.system().lower() == "windows":
            arch = "Win64"
        elif platform.system().lower() == "linux":
            arch = "Linux"
        elif platform.system().lower() == "darwin":
            # we need to test this out
            arch = "Mac"

        command1 = [u_build_tool.as_posix(), "-projectfiles",
                    f"-project={project_file}", "-progress"]

        subprocess.run(command1)

        command2 = [u_build_tool.as_posix(),
                    f"-ModuleWithSuffix={unreal_project_name},3555", arch,
                    "Development", "-TargetType=Editor",
                    f'-Project={project_file}',
                    f'{project_file}',
                    "-IgnoreJunk"]

        subprocess.run(command2)

    # ensure we have PySide2 installed in engine
    python_path = None
    if platform.system().lower() == "windows":
        python_path = engine_path / ("Engine/Binaries/ThirdParty/"
                                     "Python3/Win64/python.exe")

    if platform.system().lower() == "linux":
        python_path = engine_path / ("Engine/Binaries/ThirdParty/"
                                     "Python3/Linux/bin/python3")

    if platform.system().lower() == "darwin":
        python_path = engine_path / ("Engine/Binaries/ThirdParty/"
                                     "Python3/Mac/bin/python3")

    if not python_path:
        raise NotImplementedError("Unsupported platform")
    if not python_path.exists():
        raise RuntimeError(f"Unreal Python not found at {python_path}")
    subprocess.check_call(
        [python_path.as_posix(), "-m", "pip", "install", "pyside2"])


def get_path_to_uat(engine_path: Path) -> Path:
    if platform.system().lower() == "windows":
        return engine_path / "Engine/Build/BatchFiles/RunUAT.bat"

    if platform.system().lower() in ["linux", "darwin"]:
        return engine_path / "Engine/Build/BatchFiles/RunUAT.sh"


def get_compatible_integration(
        ue_version: str, integration_root: Path) -> List[Path]:
    """Get path to compatible version of integration plugin.

    This will try to get the closest compatible versions to the one
    specified in sorted list.

    Args:
        ue_version (str): version of the current Unreal Engine.
        integration_root (Path): path to built-in integration plugins.

    Returns:
        list of Path: Sorted list of paths closest to the specified
            version.

    """
    major, minor = ue_version.split(".")
    integration_paths = [p for p in integration_root.iterdir()
                         if p.is_dir()]

    compatible_versions = []
    for i in integration_paths:
        # parse version from path
        try:
            i_major, i_minor = re.search(
                r"(?P<major>\d+).(?P<minor>\d+)$", i.name).groups()
        except AttributeError:
            # in case there is no match, just skip to next
            continue

        # consider versions with different major so different that they
        # are incompatible
        if int(major) != int(i_major):
            continue

        compatible_versions.append(i)

    sorted(set(compatible_versions))
    return compatible_versions


def get_path_to_cmdlet_project(ue_version: str) -> Path:
    cmd_project = Path(
        os.path.abspath(os.getenv("OPENPYPE_ROOT")))

    # For now, only tested on Windows (For Linux and Mac
    # it has to be implemented)
    cmd_project /= f"openpype/hosts/unreal/integration/UE_{ue_version}"

    # if the integration doesn't exist for current engine version
    # try to find the closest to it.
    if cmd_project.exists():
        return cmd_project / "CommandletProject/CommandletProject.uproject"

    if compatible_versions := get_compatible_integration(
        ue_version, cmd_project.parent
    ):
        return compatible_versions[-1] / "CommandletProject/CommandletProject.uproject"  # noqa: E501
    else:
        raise RuntimeError(
            ("There are no compatible versions of Unreal "
             "integration plugin compatible with running version "
             f"of Unreal Engine {ue_version}"))


def get_path_to_ubt(engine_path: Path, ue_version: str) -> Path:
    u_build_tool_path = engine_path / "Engine/Binaries/DotNET"

    if ue_version.split(".")[0] == "4":
        u_build_tool_path /= "UnrealBuildTool.exe"
    elif ue_version.split(".")[0] == "5":
        u_build_tool_path /= "UnrealBuildTool/UnrealBuildTool.exe"

    return Path(u_build_tool_path)


def get_build_id(engine_path: Path, ue_version: str) -> str:
    ue_modules = Path()
    if platform.system().lower() == "windows":
        ue_modules_path = engine_path / "Engine/Binaries/Win64"
        if ue_version.split(".")[0] == "4":
            ue_modules_path /= "UE4Editor.modules"
        elif ue_version.split(".")[0] == "5":
            ue_modules_path /= "UnrealEditor.modules"
        ue_modules = Path(ue_modules_path)

    if platform.system().lower() == "linux":
        ue_modules = Path(os.path.join(engine_path, "Engine", "Binaries",
                                       "Linux", "UE4Editor.modules"))

    if platform.system().lower() == "darwin":
        ue_modules = Path(os.path.join(engine_path, "Engine", "Binaries",
                                       "Mac", "UE4Editor.modules"))

    if ue_modules.exists():
        print("--- Loading Engine ID from modules file ...")
        with open(ue_modules, "r") as mp:
            loaded_modules = json.load(mp)

        if loaded_modules.get("BuildId"):
            return "{" + loaded_modules.get("BuildId") + "}"


def check_built_plugin_existance(plugin_path) -> bool:
    if not plugin_path:
        return False

    integration_plugin_path = Path(plugin_path)

    if not os.path.isdir(integration_plugin_path):
        raise RuntimeError("Path to the integration plugin is null!")

    if not (integration_plugin_path / "Binaries").is_dir() \
            or not (integration_plugin_path / "Intermediate").is_dir():
        return False

    return True


def move_built_plugin(engine_path: Path, plugin_path: Path) -> None:
    ayon_plugin_path: Path = engine_path / "Engine/Plugins/Marketplace/Ayon"

    if not ayon_plugin_path.is_dir():
        ayon_plugin_path.mkdir(parents=True, exist_ok=True)

        engine_plugin_config_path: Path = ayon_plugin_path / "Config"
        engine_plugin_config_path.mkdir(exist_ok=True)

        dir_util._path_created = {}

    dir_util.copy_tree(plugin_path.as_posix(), ayon_plugin_path.as_posix())


def check_plugin_existence(engine_path: Path, env: dict = None) -> bool:
    env = env or os.environ
    integration_plugin_path: Path = Path(env.get("AYON_UNREAL_PLUGIN", ""))

    if not os.path.isdir(integration_plugin_path):
        raise RuntimeError("Path to the integration plugin is null!")

    # Create a path to the plugin in the engine
    op_plugin_path: Path = engine_path / "Engine/Plugins/Marketplace/Ayon"

    if not op_plugin_path.is_dir():
        return False

    if not (op_plugin_path / "Binaries").is_dir() \
            or not (op_plugin_path / "Intermediate").is_dir():
        return False

    return True


def try_installing_plugin(engine_path: Path, env: dict = None) -> None:
    env = env or os.environ

    integration_plugin_path: Path = Path(env.get("AYON_UNREAL_PLUGIN", ""))

    if not os.path.isdir(integration_plugin_path):
        raise RuntimeError("Path to the integration plugin is null!")

    # Create a path to the plugin in the engine
    op_plugin_path: Path = engine_path / "Engine/Plugins/Marketplace/Ayon"

    if not op_plugin_path.is_dir():
        op_plugin_path.mkdir(parents=True, exist_ok=True)

        engine_plugin_config_path: Path = op_plugin_path / "Config"
        engine_plugin_config_path.mkdir(exist_ok=True)

        dir_util._path_created = {}

    if not (op_plugin_path / "Binaries").is_dir() \
            or not (op_plugin_path / "Intermediate").is_dir():
        _build_and_move_plugin(engine_path, op_plugin_path, env)


def _build_and_move_plugin(engine_path: Path,
                           plugin_build_path: Path,
                           env: dict = None) -> None:
    uat_path: Path = get_path_to_uat(engine_path)

    env = env or os.environ
    integration_plugin_path: Path = Path(env.get("AYON_UNREAL_PLUGIN", ""))

    if uat_path.is_file():
        temp_dir: Path = integration_plugin_path.parent / "Temp"
        temp_dir.mkdir(exist_ok=True)
        uplugin_path: Path = integration_plugin_path / "Ayon.uplugin"

        # in order to successfully build the plugin,
        # It must be built outside the Engine directory and then moved
        build_plugin_cmd: List[str] = [f'{uat_path.as_posix()}',
                                       'BuildPlugin',
                                       f'-Plugin={uplugin_path.as_posix()}',
                                       f'-Package={temp_dir.as_posix()}']
        subprocess.run(build_plugin_cmd)

        # Copy the contents of the 'Temp' dir into the
        # 'Ayon' directory in the engine
        dir_util.copy_tree(temp_dir.as_posix(), plugin_build_path.as_posix())

        # We need to also copy the config folder.
        # The UAT doesn't include the Config folder in the build
        plugin_install_config_path: Path = plugin_build_path / "Config"
        integration_plugin_config_path = integration_plugin_path / "Config"

        dir_util.copy_tree(integration_plugin_config_path.as_posix(),
                           plugin_install_config_path.as_posix())

        dir_util.remove_tree(temp_dir.as_posix())
