import json
import os
import platform
import re
import subprocess
import tempfile
from distutils import dir_util
from distutils.dir_util import copy_tree
from pathlib import Path
from typing import List, Union

from qtpy import QtCore

import openpype.hosts.unreal.lib as ue_lib
from openpype.settings import get_current_project_settings


def parse_comp_progress(line: str, progress_signal: QtCore.Signal(int)):
    match = re.search(r"\[[1-9]+/[0-9]+]", line)
    if match is not None:
        split: list[str] = match.group().split("/")
        curr: float = float(split[0][1:])
        total: float = float(split[1][:-1])
        progress_signal.emit(int((curr / total) * 100.0))


def parse_prj_progress(line: str, progress_signal: QtCore.Signal(int)):
    match = re.search("@progress", line)
    if match is not None:
        percent_match = re.search(r"\d{1,3}", line)
        progress_signal.emit(int(percent_match.group()))


def retrieve_exit_code(line: str):
    match = re.search(r"ExitCode=\d+", line)
    if match is not None:
        split: list[str] = match.group().split("=")
        return int(split[1])

    return None


class UEProjectGenerationWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    progress = QtCore.Signal(int)
    log = QtCore.Signal(str)
    stage_begin = QtCore.Signal(str)

    ue_version: str = None
    project_name: str = None
    env = None
    engine_path: Path = None
    project_dir: Path = None
    dev_mode = False

    def setup(self, ue_version: str,
              unreal_project_name,
              engine_path: Path,
              project_dir: Path,
              dev_mode: bool = False,
              env: dict = None):

        self.ue_version = ue_version
        self.project_dir = project_dir
        self.env = env or os.environ

        preset = get_current_project_settings()["unreal"]["project_setup"]

        if dev_mode or preset["dev_mode"]:
            self.dev_mode = True

        self.project_name = unreal_project_name
        self.engine_path = engine_path

    def run(self):
        # engine_path should be the location of UE_X.X folder

        ue_editor_exe = ue_lib.get_editor_exe_path(self.engine_path,
                                                   self.ue_version)
        cmdlet_project = ue_lib.get_path_to_cmdlet_project(self.ue_version)
        project_file = self.project_dir / f"{self.project_name}.uproject"

        print("--- Generating a new project ...")
        # 1st stage
        stage_count = 2
        if self.dev_mode:
            stage_count = 4

        self.stage_begin.emit(
            ("Generating a new UE project ... 1 out of "
             f"{stage_count}"))

        # Need to copy the commandlet project to a temporary folder where
        # users don't need admin rights to write to.
        cmdlet_tmp = tempfile.TemporaryDirectory()
        cmdlet_filename = cmdlet_project.name
        cmdlet_dir = cmdlet_project.parent.as_posix()
        cmdlet_tmp_name = Path(cmdlet_tmp.name)
        cmdlet_tmp_file = cmdlet_tmp_name.joinpath(cmdlet_filename)
        copy_tree(
            cmdlet_dir,
            cmdlet_tmp_name.as_posix())

        commandlet_cmd = [
            f"{ue_editor_exe.as_posix()}",
            f"{cmdlet_tmp_file.as_posix()}",
            "-run=AyonGenerateProject",
            f"{project_file.resolve().as_posix()}",
        ]

        if self.dev_mode:
            commandlet_cmd.append("-GenerateCode")

        gen_process = subprocess.Popen(commandlet_cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

        for line in gen_process.stdout:
            decoded_line = line.decode(errors="replace")
            print(decoded_line, end="")
            self.log.emit(decoded_line)
        gen_process.stdout.close()
        return_code = gen_process.wait()

        cmdlet_tmp.cleanup()

        if return_code and return_code != 0:
            msg = (
                f"Failed to generate {self.project_name} "
                f"project! Exited with return code {return_code}"
            )
            self.failed.emit(msg, return_code)
            raise RuntimeError(msg)

        print("--- Project has been generated successfully.")
        self.stage_begin.emit(
            (f"Writing the Engine ID of the build UE ... 1"
             f" out of {stage_count}"))

        if not project_file.is_file():
            msg = ("Failed to write the Engine ID into .uproject file! Can "
                   "not read!")
            self.failed.emit(msg)
            raise RuntimeError(msg)

        with open(project_file.as_posix(), mode="r+") as pf:
            pf_json = json.load(pf)
            pf_json["EngineAssociation"] = ue_lib.get_build_id(
                self.engine_path,
                self.ue_version
            )
            print(pf_json["EngineAssociation"])
            pf.seek(0)
            json.dump(pf_json, pf, indent=4)
            pf.truncate()
            print("--- Engine ID has been written into the project file")

        self.progress.emit(90)
        if self.dev_mode:
            # 2nd stage
            self.stage_begin.emit(
                (f"Generating project files ... 2 out of "
                 f"{stage_count}"))

            self.progress.emit(0)
            ubt_path = ue_lib.get_path_to_ubt(self.engine_path,
                                              self.ue_version)

            arch = "Win64"
            if platform.system().lower() == "windows":
                arch = "Win64"
            elif platform.system().lower() == "linux":
                arch = "Linux"
            elif platform.system().lower() == "darwin":
                # we need to test this out
                arch = "Mac"

            gen_prj_files_cmd = [ubt_path.as_posix(),
                                 "-projectfiles",
                                 f"-project={project_file}",
                                 "-progress"]
            gen_proc = subprocess.Popen(gen_prj_files_cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
            for line in gen_proc.stdout:
                decoded_line: str = line.decode(errors="replace")
                print(decoded_line, end="")
                self.log.emit(decoded_line)
                parse_prj_progress(decoded_line, self.progress)

            gen_proc.stdout.close()
            return_code = gen_proc.wait()

            if return_code and return_code != 0:
                msg = ("Failed to generate project files! "
                       f"Exited with return code {return_code}")
                self.failed.emit(msg, return_code)
                raise RuntimeError(msg)

            self.stage_begin.emit(
                f"Building the project ... 3 out of {stage_count}")
            self.progress.emit(0)
            # 3rd stage
            build_prj_cmd = [ubt_path.as_posix(),
                             f"-ModuleWithSuffix={self.project_name},3555",
                             arch,
                             "Development",
                             "-TargetType=Editor",
                             f"-Project={project_file}",
                             f"{project_file}",
                             "-IgnoreJunk"]

            build_prj_proc = subprocess.Popen(build_prj_cmd,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
            for line in build_prj_proc.stdout:
                decoded_line: str = line.decode(errors="replace")
                print(decoded_line, end="")
                self.log.emit(decoded_line)
                parse_comp_progress(decoded_line, self.progress)

            build_prj_proc.stdout.close()
            return_code = build_prj_proc.wait()

            if return_code and return_code != 0:
                msg = ("Failed to build project! "
                       f"Exited with return code {return_code}")
                self.failed.emit(msg, return_code)
                raise RuntimeError(msg)

        # ensure we have PySide2 installed in engine

        self.progress.emit(0)
        self.stage_begin.emit(
            (f"Checking PySide2 installation... {stage_count} "
             f" out of {stage_count}"))
        python_path = None
        if platform.system().lower() == "windows":
            python_path = self.engine_path / ("Engine/Binaries/ThirdParty/"
                                              "Python3/Win64/python.exe")

        if platform.system().lower() == "linux":
            python_path = self.engine_path / ("Engine/Binaries/ThirdParty/"
                                              "Python3/Linux/bin/python3")

        if platform.system().lower() == "darwin":
            python_path = self.engine_path / ("Engine/Binaries/ThirdParty/"
                                              "Python3/Mac/bin/python3")

        if not python_path:
            msg = "Unsupported platform"
            self.failed.emit(msg, 1)
            raise NotImplementedError(msg)
        if not python_path.exists():
            msg = f"Unreal Python not found at {python_path}"
            self.failed.emit(msg, 1)
            raise RuntimeError(msg)
        pyside_cmd = [python_path.as_posix(),
                      "-m",
                      "pip",
                      "install",
                      "pyside2"]

        pyside_install = subprocess.Popen(pyside_cmd,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)

        for line in pyside_install.stdout:
            decoded_line: str = line.decode(errors="replace")
            print(decoded_line, end="")
            self.log.emit(decoded_line)

        pyside_install.stdout.close()
        return_code = pyside_install.wait()

        if return_code and return_code != 0:
            msg = ("Failed to create the project! "
                   "The installation of PySide2 has failed!")
            self.failed.emit(msg, return_code)
            raise RuntimeError(msg)

        self.progress.emit(100)
        self.finished.emit("Project successfully built!")


class UEPluginInstallWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    installing = QtCore.Signal(str)
    failed = QtCore.Signal(str, int)
    progress = QtCore.Signal(int)
    log = QtCore.Signal(str)

    engine_path: Path = None
    env = None

    def setup(self, engine_path: Path, env: dict = None, ):
        self.engine_path = engine_path
        self.env = env or os.environ

    def _build_and_move_plugin(self, plugin_build_path: Path):
        uat_path: Path = ue_lib.get_path_to_uat(self.engine_path)
        src_plugin_dir = Path(self.env.get("AYON_UNREAL_PLUGIN", ""))

        if not os.path.isdir(src_plugin_dir):
            msg = "Path to the integration plugin is null!"
            self.failed.emit(msg, 1)
            raise RuntimeError(msg)

        if not uat_path.is_file():
            msg = "Building failed! Path to UAT is invalid!"
            self.failed.emit(msg, 1)
            raise RuntimeError(msg)

        temp_dir: Path = src_plugin_dir.parent / "Temp"
        temp_dir.mkdir(exist_ok=True)
        uplugin_path: Path = src_plugin_dir / "Ayon.uplugin"

        # in order to successfully build the plugin,
        # It must be built outside the Engine directory and then moved
        build_plugin_cmd: List[str] = [f"{uat_path.as_posix()}",
                                       "BuildPlugin",
                                       f"-Plugin={uplugin_path.as_posix()}",
                                       f"-Package={temp_dir.as_posix()}"]

        build_proc = subprocess.Popen(build_plugin_cmd,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        return_code: Union[None, int] = None
        for line in build_proc.stdout:
            decoded_line: str = line.decode(errors="replace")
            print(decoded_line, end="")
            self.log.emit(decoded_line)
            if return_code is None:
                return_code = retrieve_exit_code(decoded_line)
            parse_comp_progress(decoded_line, self.progress)

        build_proc.stdout.close()
        build_proc.wait()

        if return_code and return_code != 0:
            msg = ("Failed to build plugin"
                   f" project! Exited with return code {return_code}")
            dir_util.remove_tree(temp_dir.as_posix())
            self.failed.emit(msg, return_code)
            raise RuntimeError(msg)

        # Copy the contents of the 'Temp' dir into the
        # 'Ayon' directory in the engine
        dir_util.copy_tree(temp_dir.as_posix(),
                           plugin_build_path.as_posix())

        # We need to also copy the config folder.
        # The UAT doesn't include the Config folder in the build
        plugin_install_config_path: Path = plugin_build_path / "Config"
        src_plugin_config_path = src_plugin_dir / "Config"

        dir_util.copy_tree(src_plugin_config_path.as_posix(),
                           plugin_install_config_path.as_posix())

        dir_util.remove_tree(temp_dir.as_posix())

    def run(self):
        src_plugin_dir = Path(self.env.get("AYON_UNREAL_PLUGIN", ""))

        if not os.path.isdir(src_plugin_dir):
            msg = "Path to the integration plugin is null!"
            self.failed.emit(msg, 1)
            raise RuntimeError(msg)

        # Create a path to the plugin in the engine
        op_plugin_path = self.engine_path / "Engine/Plugins/Marketplace" \
                                            "/Ayon"

        if not op_plugin_path.is_dir():
            self.installing.emit("Installing and building the plugin ...")
            op_plugin_path.mkdir(parents=True, exist_ok=True)

            engine_plugin_config_path = op_plugin_path / "Config"
            engine_plugin_config_path.mkdir(exist_ok=True)

            dir_util._path_created = {}

        if not (op_plugin_path / "Binaries").is_dir() \
                or not (op_plugin_path / "Intermediate").is_dir():
            self.installing.emit("Building the plugin ...")
            print("--- Building the plugin...")

            self._build_and_move_plugin(op_plugin_path)

        self.finished.emit("Plugin successfully installed")
