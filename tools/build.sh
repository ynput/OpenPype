#!/usr/bin/env bash

# Build Pype using existing virtual environment.


art () {
  cat <<-EOF

▒█▀▀▀█ █▀▀█ █▀▀ █▀▀▄ ▒█▀▀█ █░░█ █▀▀█ █▀▀ ▀█▀ ▀█▀ ▀█▀
▒█░░▒█ █░░█ █▀▀ █░░█ ▒█▄▄█ █▄▄█ █░░█ █▀▀ ▒█░ ▒█░ ▒█░
▒█▄▄▄█ █▀▀▀ ▀▀▀ ▀░░▀ ▒█░░░ ▄▄▄█ █▀▀▀ ▀▀▀ ▄█▄ ▄█▄ ▄█▄
            .---= [ by Pype Club ] =---.
                 https://openpype.io

EOF
}

# Colors for terminal

RST='\033[0m'             # Text Reset

# Regular Colors
Black='\033[0;30m'        # Black
Red='\033[0;31m'          # Red
Green='\033[0;32m'        # Green
Yellow='\033[0;33m'       # Yellow
Blue='\033[0;34m'         # Blue
Purple='\033[0;35m'       # Purple
Cyan='\033[0;36m'         # Cyan
White='\033[0;37m'        # White

# Bold
BBlack='\033[1;30m'       # Black
BRed='\033[1;31m'         # Red
BGreen='\033[1;32m'       # Green
BYellow='\033[1;33m'      # Yellow
BBlue='\033[1;34m'        # Blue
BPurple='\033[1;35m'      # Purple
BCyan='\033[1;36m'        # Cyan
BWhite='\033[1;37m'       # White

# Bold High Intensity
BIBlack='\033[1;90m'      # Black
BIRed='\033[1;91m'        # Red
BIGreen='\033[1;92m'      # Green
BIYellow='\033[1;93m'     # Yellow
BIBlue='\033[1;94m'       # Blue
BIPurple='\033[1;95m'     # Purple
BICyan='\033[1;96m'       # Cyan
BIWhite='\033[1;97m'      # White


##############################################################################
# Detect required version of python
# Globals:
#   colors
#   PYTHON
# Arguments:
#   None
# Returns:
#   None
###############################################################################
detect_python () {
  echo -e "${BIGreen}>>>${RST} Using python \c"
  local version_command
  version_command="import sys;print('{0}.{1}'.format(sys.version_info[0], sys.version_info[1]))"
  local python_version
  python_version="$(python3 <<< ${version_command})"
  oIFS="$IFS"
  IFS=.
  set -- $python_version
  IFS="$oIFS"
  if [ "$1" -ge "3" ] && [ "$2" -ge "6" ] ; then
    if [ "$2" -gt "7" ] ; then
      echo -e "${BIWhite}[${RST} ${BIRed}$1.$2 ${BIWhite}]${RST} - ${BIRed}FAILED${RST} ${BIYellow}Version is new and unsupported, use${RST} ${BIPurple}3.7.x${RST}"; return 1;
    else
      echo -e "${BIWhite}[${RST} ${BIGreen}$1.$2${RST} ${BIWhite}]${RST}"
    fi
  else
    command -v python3 >/dev/null 2>&1 || { echo -e "${BIRed}$1.$2$ - ${BIRed}FAILED${RST} ${BIYellow}Version is old and unsupported${RST}"; return 1; }
  fi
}

##############################################################################
# Clean pyc files in specified directory
# Globals:
#   None
# Arguments:
#   Optional path to clean
# Returns:
#   None
###############################################################################
clean_pyc () {
  local path
  path=$openpype_root
  echo -e "${BIGreen}>>>${RST} Cleaning pyc at [ ${BIWhite}$path${RST} ] ... \c"
  find "$path" -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
  echo -e "${BIGreen}DONE${RST}"
}

##############################################################################
# Return absolute path
# Globals:
#   None
# Arguments:
#   Path to resolve
# Returns:
#   None
###############################################################################
realpath () {
  echo $(cd $(dirname "$1") || return; pwd)/$(basename "$1")
}

##############################################################################
# Install Poetry when needed
# Globals:
#   PATH
# Arguments:
#   None
# Returns:
#   None
###############################################################################
install_poetry () {
  echo -e "${BIGreen}>>>${RST} Installing Poetry ..."
  command -v curl >/dev/null 2>&1 || { echo -e "${BIRed}!!!${RST}${BIYellow} Missing ${RST}${BIBlue}curl${BIYellow} command.${RST}"; return 1; }
  curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
  export PATH="$PATH:$HOME/.poetry/bin"
}

# Main
main () {
  echo -e "${BGreen}"
  art
  echo -e "${RST}"
  detect_python || return 1

  # Directories
  openpype_root=$(dirname $(dirname "$(realpath ${BASH_SOURCE[0]})"))
  pushd "$openpype_root" > /dev/null || return > /dev/null

  version_command="import os;exec(open(os.path.join('$openpype_root', 'openpype', 'version.py')).read());print(__version__);"
  openpype_version="$(python3 <<< ${version_command})"

  echo -e "${BIYellow}---${RST} Cleaning build directory ..."
  rm -rf "$openpype_root/build" && mkdir "$openpype_root/build" > /dev/null

  echo -e "${BIGreen}>>>${RST} Building OpenPype ${BIWhite}[${RST} ${BIGreen}$openpype_version${RST} ${BIWhite}]${RST}"
  echo -e "${BIGreen}>>>${RST} Cleaning cache files ..."
  clean_pyc

  echo -e "${BIGreen}>>>${RST} Reading Poetry ... \c"
  if [ -f "$HOME/.poetry/bin/poetry" ]; then
    echo -e "${BIGreen}OK${RST}"
    export PATH="$PATH:$HOME/.poetry/bin"
  else
    echo -e "${BIYellow}NOT FOUND${RST}"
    install_poetry || { echo -e "${BIRed}!!!${RST} Poetry installation failed"; return; }
  fi

  echo -e "${BIGreen}>>>${RST} Making sure submodules are up-to-date ..."
  git submodule update --init --recursive

  echo -e "${BIGreen}>>>${RST} Building ..."
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    poetry run python3 "$openpype_root/setup.py" build > "$openpype_root/build/build.log" || { echo -e "${BIRed}!!!${RST} Build failed, see the build log."; return; }
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    poetry run python3 "$openpype_root/setup.py" bdist_mac > "$openpype_root/build/build.log" || { echo -e "${BIRed}!!!${RST} Build failed, see the build log."; return; }
  fi
  poetry run python3 "$openpype_root/tools/build_dependencies.py"

  if [[ "$OSTYPE" == "darwin"* ]]; then
    # fix code signing issue
    codesign --remote-signature "$openpype_root/build/OpenPype.app/Contents/MacOS/lib/Python"
    if command -v create-dmg > /dev/null 2>&1; then
      create-dmg \
        --volname "OpenPype Installer" \
        --window-pos 200 120 \
        --window-size 600 300 \
        --app-drop-link 100 50 \
        "$openpype_root/build/OpenPype-Installer.dmg" \
        "$openpype_root/build/OpenPype.app"
    else
      echo -e "${BIYellow}!!!${RST} ${BIWhite}create-dmg${RST} command is not available."
    fi
  fi

  echo -e "${BICyan}>>>${RST} All done. You will find OpenPype and build log in \c"
  echo -e "${BIWhite}$openpype_root/build${RST} directory."
}

main
