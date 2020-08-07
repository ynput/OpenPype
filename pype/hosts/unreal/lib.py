import sys
import os
import platform
import json
from distutils import dir_util
import subprocess
from pype.api import config


def get_engine_versions():
    """
    This will try to detect location and versions of installed Unreal Engine.
    Location can be overridden by `UNREAL_ENGINE_LOCATION` environment
    variable.

    Returns:

        dict: dictionary with version as a key and dir as value.

    Example:

        >>> get_engine_version()
        {
            "4.23": "C:/Epic Games/UE_4.23",
            "4.24": "C:/Epic Games/UE_4.24"
        }
    """
    try:
        engine_locations = {}
        root, dirs, files = next(os.walk(os.environ["UNREAL_ENGINE_LOCATION"]))

        for dir in dirs:
            if dir.startswith("UE_"):
                ver = dir.split("_")[1]
                engine_locations[ver] = os.path.join(root, dir)
    except KeyError:
        # environment variable not set
        pass
    except OSError:
        # specified directory doesn't exists
        pass

    # if we've got something, terminate autodetection process
    if engine_locations:
        return engine_locations

    # else kick in platform specific detection
    if platform.system().lower() == "windows":
        return _win_get_engine_versions()
    elif platform.system().lower() == "linux":
        # on linux, there is no installation and getting Unreal Engine involves
        # git clone. So we'll probably depend on `UNREAL_ENGINE_LOCATION`.
        pass
    elif platform.system().lower() == "darwin":
        return _darwin_get_engine_version()

    return {}


def _win_get_engine_versions():
    """
    If engines are installed via Epic Games Launcher then there is:
    `%PROGRAMDATA%/Epic/UnrealEngineLauncher/LauncherInstalled.dat`
    This file is JSON file listing installed stuff, Unreal engines
    are marked with `"AppName" = "UE_X.XX"`` like `UE_4.24`
    """
    install_json_path = os.path.join(
        os.environ.get("PROGRAMDATA"),
        "Epic",
        "UnrealEngineLauncher",
        "LauncherInstalled.dat",
    )

    return _parse_launcher_locations(install_json_path)


def _darwin_get_engine_version() -> dict:
    """
    It works the same as on Windows, just JSON file location is different.
    """
    install_json_path = os.path.join(
        os.environ.get("HOME"),
        "Library",
        "Application Support",
        "Epic",
        "UnrealEngineLauncher",
        "LauncherInstalled.dat",
    )

    return _parse_launcher_locations(install_json_path)


def _parse_launcher_locations(install_json_path: str) -> dict:
    """
    This will parse locations from json file.

    :param install_json_path: path to `LauncherInstalled.dat`
    :type install_json_path: str
    :returns: returns dict with unreal engine versions as keys and
              paths to those engine installations as value.
    :rtype: dict
    """
    engine_locations = {}
    if os.path.isfile(install_json_path):
        with open(install_json_path, "r") as ilf:
            try:
                install_data = json.load(ilf)
            except json.JSONDecodeError:
                raise Exception(
                    "Invalid `LauncherInstalled.dat file. `"
                    "Cannot determine Unreal Engine location."
                )

        for installation in install_data.get("InstallationList", []):
            if installation.get("AppName").startswith("UE_"):
                ver = installation.get("AppName").split("_")[1]
                engine_locations[ver] = installation.get("InstallLocation")

    return engine_locations


def create_unreal_project(project_name: str,
                          ue_version: str,
                          pr_dir: str,
                          engine_path: str,
                          dev_mode: bool = False) -> None:
    """
    This will create `.uproject` file at specified location. As there is no
    way I know to create project via command line, this is easiest option.
    Unreal project file is basically JSON file. If we find
    `AVALON_UNREAL_PLUGIN` environment variable we assume this is location
    of Avalon Integration Plugin and we copy its content to project folder
    and enable this plugin.

    :param project_name: project name
    :type project_name: str
    :param ue_version: unreal engine version (like 4.23)
    :type ue_version: str
    :param pr_dir: path to directory where project will be created
    :type pr_dir: str
    :param engine_path: Path to Unreal Engine installation
    :type engine_path: str
    :param dev_mode: Flag to trigger C++ style Unreal project needing
                     Visual Studio and other tools to compile plugins from
                     sources. This will trigger automatically if `Binaries`
                     directory is not found in plugin folders as this indicates
                     this is only source distribution of the plugin. Dev mode
                     is also set by preset file `unreal/project_setup.json` in
                     **PYPE_CONFIG**.
    :type dev_mode: bool
    :returns: None
    """
    preset = config.get_presets()["unreal"]["project_setup"]

    if os.path.isdir(os.environ.get("AVALON_UNREAL_PLUGIN", "")):
        # copy plugin to correct path under project
        plugins_path = os.path.join(pr_dir, "Plugins")
        avalon_plugin_path = os.path.join(plugins_path, "Avalon")
        if not os.path.isdir(avalon_plugin_path):
            os.makedirs(avalon_plugin_path, exist_ok=True)
            dir_util._path_created = {}
            dir_util.copy_tree(os.environ.get("AVALON_UNREAL_PLUGIN"),
                               avalon_plugin_path)

            if (not os.path.isdir(os.path.join(avalon_plugin_path, "Binaries"))
                    or not os.path.join(avalon_plugin_path, "Intermediate")):
                dev_mode = True

    # data for project file
    data = {
        "FileVersion": 3,
        "EngineAssociation": ue_version,
        "Category": "",
        "Description": "",
        "Plugins": [
            {"Name": "PythonScriptPlugin", "Enabled": True},
            {"Name": "EditorScriptingUtilities", "Enabled": True},
            {"Name": "Avalon", "Enabled": True}
        ]
    }

    if preset["install_unreal_python_engine"]:
        # If `PYPE_UNREAL_ENGINE_PYTHON_PLUGIN` is set, copy it from there to
        # support offline installation.
        # Otherwise clone UnrealEnginePython to Plugins directory
        # https://github.com/20tab/UnrealEnginePython.git
        uep_path = os.path.join(plugins_path, "UnrealEnginePython")
        if os.environ.get("PYPE_UNREAL_ENGINE_PYTHON_PLUGIN"):

            os.makedirs(uep_path, exist_ok=True)
            dir_util._path_created = {}
            dir_util.copy_tree(
                os.environ.get("PYPE_UNREAL_ENGINE_PYTHON_PLUGIN"),
                uep_path)
        else:
            # WARNING: this will trigger dev_mode, because we need to compile
            # this plugin.
            dev_mode = True
            import git
            git.Repo.clone_from(
                "https://github.com/20tab/UnrealEnginePython.git",
                uep_path)

        data["Plugins"].append(
            {"Name": "UnrealEnginePython", "Enabled": True})

        if (not os.path.isdir(os.path.join(uep_path, "Binaries"))
                or not os.path.join(uep_path, "Intermediate")):
            dev_mode = True

    if dev_mode or preset["dev_mode"]:
        # this will add project module and necessary source file to make it
        # C++ project and to (hopefully) make Unreal Editor to compile all
        # sources at start

        data["Modules"] = [{
            "Name": project_name,
            "Type": "Runtime",
            "LoadingPhase": "Default",
            "AdditionalDependencies": ["Engine"],
        }]

        if preset["install_unreal_python_engine"]:
            # now we need to fix python path in:
            # `UnrealEnginePython.Build.cs`
            # to point to our python
            with open(os.path.join(
                    uep_path, "Source",
                    "UnrealEnginePython",
                    "UnrealEnginePython.Build.cs"), mode="r") as f:
                build_file = f.read()

            fix = build_file.replace(
                'private string pythonHome = "";',
                'private string pythonHome = "{}";'.format(
                    sys.base_prefix.replace("\\", "/")))

            with open(os.path.join(
                    uep_path, "Source",
                    "UnrealEnginePython",
                    "UnrealEnginePython.Build.cs"), mode="w") as f:
                f.write(fix)

    # write project file
    project_file = os.path.join(pr_dir, "{}.uproject".format(project_name))
    with open(project_file, mode="w") as pf:
        json.dump(data, pf, indent=4)

    # ensure we have PySide installed in engine
    # TODO: make it work for other platforms 🍎 🐧
    if platform.system().lower() == "windows":
        python_path = os.path.join(engine_path, "Engine", "Binaries",
                                   "ThirdParty", "Python", "Win64",
                                   "python.exe")

        subprocess.run([python_path, "-m",
                        "pip", "install", "pyside"])

    if dev_mode or preset["dev_mode"]:
        _prepare_cpp_project(project_file, engine_path)


def _prepare_cpp_project(project_file: str, engine_path: str) -> None:
    """
    This function will add source files needed for project to be
    rebuild along with the avalon integration plugin.

    There seems not to be automated way to do it from command line.
    But there might be way to create at least those target and build files
    by some generator. This needs more research as manually writing
    those files is rather hackish. :skull_and_crossbones:

    :param project_file: path to .uproject file
    :type project_file: str
    :param engine_path: path to unreal engine associated with project
    :type engine_path: str
    """

    project_name = os.path.splitext(os.path.basename(project_file))[0]
    project_dir = os.path.dirname(project_file)
    targets_dir = os.path.join(project_dir, "Source")
    sources_dir = os.path.join(targets_dir, project_name)

    os.makedirs(sources_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, "Content"), exist_ok=True)

    module_target = '''
using UnrealBuildTool;
using System.Collections.Generic;

public class {0}Target : TargetRules
{{
    public {0}Target( TargetInfo Target) : base(Target)
    {{
        Type = TargetType.Game;
        ExtraModuleNames.AddRange( new string[] {{ "{0}" }} );
    }}
}}
'''.format(project_name)

    editor_module_target = '''
using UnrealBuildTool;
using System.Collections.Generic;

public class {0}EditorTarget : TargetRules
{{
    public {0}EditorTarget( TargetInfo Target) : base(Target)
    {{
        Type = TargetType.Editor;

        ExtraModuleNames.AddRange( new string[] {{ "{0}" }} );
    }}
}}
'''.format(project_name)

    module_build = '''
using UnrealBuildTool;
public class {0} : ModuleRules
{{
    public {0}(ReadOnlyTargetRules Target) : base(Target)
    {{
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] {{ "Core",
            "CoreUObject", "Engine", "InputCore" }});
        PrivateDependencyModuleNames.AddRange(new string[] {{  }});
    }}
}}
'''.format(project_name)

    module_cpp = '''
#include "{0}.h"
#include "Modules/ModuleManager.h"

IMPLEMENT_PRIMARY_GAME_MODULE( FDefaultGameModuleImpl, {0}, "{0}" );
'''.format(project_name)

    module_header = '''
#pragma once
#include "CoreMinimal.h"
'''

    game_mode_cpp = '''
#include "{0}GameModeBase.h"
'''.format(project_name)

    game_mode_h = '''
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "{0}GameModeBase.generated.h"

UCLASS()
class {1}_API A{0}GameModeBase : public AGameModeBase
{{
    GENERATED_BODY()
}};
'''.format(project_name, project_name.upper())

    with open(os.path.join(
            targets_dir, f"{project_name}.Target.cs"), mode="w") as f:
        f.write(module_target)

    with open(os.path.join(
            targets_dir, f"{project_name}Editor.Target.cs"), mode="w") as f:
        f.write(editor_module_target)

    with open(os.path.join(
            sources_dir, f"{project_name}.Build.cs"), mode="w") as f:
        f.write(module_build)

    with open(os.path.join(
            sources_dir, f"{project_name}.cpp"), mode="w") as f:
        f.write(module_cpp)

    with open(os.path.join(
            sources_dir, f"{project_name}.h"), mode="w") as f:
        f.write(module_header)

    with open(os.path.join(
            sources_dir, f"{project_name}GameModeBase.cpp"), mode="w") as f:
        f.write(game_mode_cpp)

    with open(os.path.join(
            sources_dir, f"{project_name}GameModeBase.h"), mode="w") as f:
        f.write(game_mode_h)

    if platform.system().lower() == "windows":
        u_build_tool = (f"{engine_path}/Engine/Binaries/DotNET/"
                        "UnrealBuildTool.exe")
        u_header_tool = (f"{engine_path}/Engine/Binaries/Win64/"
                         f"UnrealHeaderTool.exe")
    elif platform.system().lower() == "linux":
        # WARNING: there is no UnrealBuildTool on linux?
        u_build_tool = ""
        u_header_tool = ""
    elif platform.system().lower() == "darwin":
        # WARNING: there is no UnrealBuildTool on Mac?
        u_build_tool = ""
        u_header_tool = ""

    u_build_tool = u_build_tool.replace("\\", "/")
    u_header_tool = u_header_tool.replace("\\", "/")

    command1 = [u_build_tool, "-projectfiles", f"-project={project_file}",
                "-progress"]

    subprocess.run(command1)

    command2 = [u_build_tool, f"-ModuleWithSuffix={project_name},3555"
                "Win64", "Development", "-TargetType=Editor"
                f'-Project="{project_file}"', f'"{project_file}"'
                "-IgnoreJunk"]

    subprocess.run(command2)

    """
    uhtmanifest = os.path.join(os.path.dirname(project_file),
                               f"{project_name}.uhtmanifest")

    command3 = [u_header_tool, f'"{project_file}"', f'"{uhtmanifest}"',
                "-Unattended", "-WarningsAsErrors", "-installed"]

    subprocess.run(command3)
    """
