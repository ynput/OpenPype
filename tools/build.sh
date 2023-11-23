#!/usr/bin/env bash

# Build Pype using existing virtual environment.


art () {
  cat <<-EOF

             . .   ..     .    ..
        _oOOP3OPP3Op_. .
     .PPpo~·   ··   ~2p.  ··  ····  ·  ·
    ·Ppo · .pPO3Op.· · O:· · · ·
   .3Pp · oP3'· 'P33· · 4 ··   ·  ·   · ·· ·  ·  ·
  ·~OP    3PO·  .Op3    : · ··  _____  _____  _____
  ·P3O  · oP3oP3O3P' · · ·   · /    /·/    /·/    /
   O3:·   O3p~ ·       ·:· · ·/____/·/____/ /____/
   'P ·   3p3·  oP3~· ·.P:· ·  · ··  ·   · ·· ·  ·  ·
  · ':  · Po'  ·Opo'· .3O· .  o[ by Pype Club ]]]==- - - ·  ·
    · '_ ..  ·    . _OP3··  ·  ·https://openpype.io·· ·
         ~P3·OPPPO3OP~ · ··  ·
           ·  ' '· ·  ·· · · · ··  ·

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

args=$@
disable_submodule_update=0
while :; do
  case $1 in
    --no-submodule-update)
      disable_submodule_update=1
      ;;
    --)
      shift
      break
      ;;
    *)
      break
  esac

  shift
done




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
  command -v python >/dev/null 2>&1 || { echo -e "${BIRed}- NOT FOUND${RST} ${BIYellow}You need Python 3.9 installed to continue.${RST}"; return 1; }
  local version_command
  version_command="import sys;print('{0}.{1}'.format(sys.version_info[0], sys.version_info[1]))"
  local python_version
  python_version="$(python <<< ${version_command})"
  oIFS="$IFS"
  IFS=.
  set -- $python_version
  IFS="$oIFS"
  if [ "$1" -ge "3" ] && [ "$2" -ge "9" ] ; then
    if [ "$2" -gt "9" ] ; then
      echo -e "${BIWhite}[${RST} ${BIRed}$1.$2 ${BIWhite}]${RST} - ${BIRed}FAILED${RST} ${BIYellow}Version is new and unsupported, use${RST} ${BIPurple}3.9.x${RST}"; return 1;
    else
      echo -e "${BIWhite}[${RST} ${BIGreen}$1.$2${RST} ${BIWhite}]${RST}"
    fi
  else
    command -v python >/dev/null 2>&1 || { echo -e "${BIRed}$1.$2$ - ${BIRed}FAILED${RST} ${BIYellow}Version is old and unsupported${RST}"; return 1; }
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
  find "$path" -path ./build -o -regex '^.*\(__pycache__\|\.py[co]\)$' -delete

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

# Main
main () {
  echo -e "${BGreen}"
  art
  echo -e "${RST}"
  detect_python || return 1

  # Directories
  openpype_root=$(dirname $(dirname "$(realpath ${BASH_SOURCE[0]})"))
  pushd "$openpype_root" > /dev/null || return > /dev/null

  version_command="import os;import re;version={};exec(open(os.path.join('$openpype_root', 'openpype', 'version.py')).read(), version);print(re.search(r'(\d+\.\d+.\d+).*', version['__version__'])[1]);"
  openpype_version="$(python <<< ${version_command})"

  _inside_openpype_tool="1"

  if [[ -z $POETRY_HOME ]]; then
    export POETRY_HOME="$openpype_root/.poetry"
  fi

  echo -e "${BIYellow}---${RST} Cleaning build directory ..."
  rm -rf "$openpype_root/build" && mkdir "$openpype_root/build" > /dev/null

  echo -e "${BIGreen}>>>${RST} Building OpenPype ${BIWhite}[${RST} ${BIGreen}$openpype_version${RST} ${BIWhite}]${RST}"
  echo -e "${BIGreen}>>>${RST} Cleaning cache files ..."
  clean_pyc

  echo -e "${BIGreen}>>>${RST} Reading Poetry ... \c"
  if [ -f "$POETRY_HOME/bin/poetry" ]; then
    echo -e "${BIGreen}OK${RST}"
  else
    echo -e "${BIYellow}NOT FOUND${RST}"
    echo -e "${BIYellow}***${RST} We need to install Poetry and virtual env ..."
    . "$openpype_root/tools/create_env.sh" || { echo -e "${BIRed}!!!${RST} Poetry installation failed"; return 1; }
  fi

if [ "$disable_submodule_update" == 1 ]; then
    echo -e "${BIYellow}***${RST} Not updating submodules ..."
  else
    echo -e "${BIGreen}>>>${RST} Making sure submodules are up-to-date ..."
    git submodule update --init --recursive || { echo -e "${BIRed}!!!${RST} Poetry installation failed"; return 1; }
  fi
  echo -e "${BIGreen}>>>${RST} Building ..."
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    "$POETRY_HOME/bin/poetry" run python "$openpype_root/setup.py" build &> "$openpype_root/build/build.log" || { echo -e "${BIRed}------------------------------------------${RST}"; cat "$openpype_root/build/build.log"; echo -e "${BIRed}------------------------------------------${RST}"; echo -e "${BIRed}!!!${RST} Build failed, see the build log."; return 1; }
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    "$POETRY_HOME/bin/poetry" run python "$openpype_root/setup.py" bdist_mac &> "$openpype_root/build/build.log" || { echo -e "${BIRed}------------------------------------------${RST}"; cat "$openpype_root/build/build.log"; echo -e "${BIRed}------------------------------------------${RST}"; echo -e "${BIRed}!!!${RST} Build failed, see the build log."; return 1; }
  fi
  "$POETRY_HOME/bin/poetry" run python "$openpype_root/tools/build_dependencies.py" || { echo -e "${BIRed}!!!>${RST} ${BIYellow}Failed to process dependencies${RST}"; return 1; }

  if [[ "$OSTYPE" == "darwin"* ]]; then
    # fix cx_Freeze libs issue
    echo -e "${BIGreen}>>>${RST} Fixing libs ..."
    mv "$openpype_root/build/OpenPype $openpype_version.app/Contents/MacOS/dependencies/cx_Freeze" "$openpype_root/build/OpenPype $openpype_version.app/Contents/MacOS/lib/"  || { echo -e "${BIRed}!!!>${RST} ${BIYellow}Can't move cx_Freeze libs${RST}"; return 1; }

    # force hide icon from Dock
    defaults write "$openpype_root/build/OpenPype $openpype_version.app/Contents/Info" LSUIElement 1

    # fix code signing issue
    echo -e "${BIGreen}>>>${RST} Fixing code signatures ...\c"
    codesign --remove-signature "$openpype_root/build/OpenPype $openpype_version.app/Contents/MacOS/openpype_console" || { echo -e "${BIRed}FAILED${RST}"; return 1; }
    codesign --remove-signature "$openpype_root/build/OpenPype $openpype_version.app/Contents/MacOS/openpype_gui" || { echo -e "${BIRed}FAILED${RST}"; return 1; }
    echo -e "${BIGreen}DONE${RST}"
    if command -v create-dmg > /dev/null 2>&1; then
      echo -e "${BIGreen}>>>${RST} Creating dmg image ...\c"
      create-dmg \
        --volname "OpenPype $openpype_version Installer" \
        --window-pos 200 120 \
        --window-size 600 300 \
        --app-drop-link 100 50 \
        "$openpype_root/build/OpenPype-Installer-$openpype_version.dmg" \
        "$openpype_root/build/OpenPype $openpype_version.app"

      test $? -eq 0 || { echo -e "${BIRed}FAILED${RST}"; return 1; }
      echo -e "${BIGreen}DONE${RST}"
    else
      echo -e "${BIYellow}!!!${RST} ${BIWhite}create-dmg${RST} command is not available."
    fi
  fi

  echo -e "${BICyan}>>>${RST} All done. You will find OpenPype and build log in \c"
  echo -e "${BIWhite}$openpype_root/build${RST} directory."
}

return_code=0
main || return_code=$?
exit $return_code
