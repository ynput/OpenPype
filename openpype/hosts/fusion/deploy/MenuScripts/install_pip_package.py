import os
import platform
import subprocess
from pathlib import Path


def get_python_home() -> Path:
    python_home = Path(os.__file__).parent.parent
    return python_home


def get_python_executable(python_home):
    if platform.system() == "Windows":
        python_executable = python_home / "python.exe"
    else:
        python_executable = python_home.parent / "bin" / "python3"
    if not python_executable.exists():
        print(f"No Python executable found at {python_home}")
        return
    return python_executable.as_posix()


def run_installation_command(python_executable, package) -> None:
    if not python_executable:
        return
    command = [
        python_executable,
        "-m",
        "pip",
        "install",
        package,
    ]
    print(f"running command: {command}")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    while True:
        output = process.stdout.readline().decode()
        if output == "" or process.poll() is not None:
            break
        if output:
            print(output.strip())


def pip_install(package: str, fusion_python_home=None) -> None:
    if fusion_python_home is None:
        fusion_python_home = get_python_home()

    python_executable = get_python_executable(fusion_python_home)
    if not python_executable:
        return
    print(f"Installing {package}")
    run_installation_command(python_executable, package)
    print("Done.")
