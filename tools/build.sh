#!/usr/bin/env bash
art () {
  cat <<-EOF
 ____________
/\\           \\
\\ \\      ---  \\
 \\ \\     _____/ ______
  \\ \\    \\___/ /\\     \\
   \\ \\____\\    \\ \\_____\\
    \\/____/     \\/_____/   PYPE Club .

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


###############################################################################
# Test if Xcode Command Line tools are installed in MacOS
###############################################################################
have_command_line_tools() {
  [[ -e "/Library/Developer/CommandLineTools/usr/bin/git" ]]
}

###############################################################################
# Get command any key from user
###############################################################################
getc() {
  local save_state
  save_state=$(/bin/stty -g)
  /bin/stty raw -echo
  IFS= read -r -n 1 -d '' "$@"
  /bin/stty "$save_state"
}

###############################################################################
# Test if we have access via sudo
# Used in MacOS
###############################################################################
have_sudo_access() {
  if [[ -z "${HAVE_SUDO_ACCESS-}" ]]; then
    /usr/bin/sudo -l mkdir &>/dev/null
    HAVE_SUDO_ACCESS="$?"
  fi

  if [[ "$HAVE_SUDO_ACCESS" -ne 0 ]]; then
    echo -e "${BIRed}!!!${RST} Need sudo access on MacOS"
    return 1
  fi

  return "$HAVE_SUDO_ACCESS"
}

###############################################################################
# Execute command and report failure
###############################################################################
execute() {
  if ! "$@"; then
    echo -e "${BIRed}!!!${RST} Failed execution of ${BIWhite}[ $@ ]${RST}"
  fi
}

###############################################################################
# Execute command using sudo
# This is used on MacOS to handle Xcode command line tools installation
###############################################################################
execute_sudo() {
  local -a args=("$@")
  if [[ -n "${SUDO_ASKPASS-}" ]]; then
    args=("-A" "${args[@]}")
  fi
  if have_sudo_access; then
    echo -e "${BIGreen}>->${RST} sudo: [${BIWhite} ${args[@]} ${RST}]"
    execute "/usr/bin/sudo" "${args[@]}"
  else
    echo -e "${BIGreen}>->${RST} [${BIWhite} ${args[@]} ${RST}]"
    execute "${args[@]}"
  fi
}


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
  echo -e "${BIYellow}>>>${RST} Forced using python at [ ${BIWhite}[ $PYPE_PYTHON_EXE ]${RST} ... \c"
  local version_command="import sys;print('{0}.{1}'.format(sys.version_info[0], sys.version_info[1]))"
  local python_version="$(python3 <<< ${version_command})"
  oIFS="$IFS"
  IFS=.
  set -- $python_version
  IFS="$oIFS"
  if [ "$1" -ge "3" ] && [ "$2" -ge "6" ] ; then
    echo -e "${BIGreen}$1.$2${RST}"
    PYTHON="python3"
  else
    command -v python3 >/dev/null 2>&1 || { echo -e "${BIRed}FAILED${RST} ${BIYellow} Version [${RST}${BICyan}$1.$2${RST}]${BIYellow} is old and unsupported${RST}"; return 1; }
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
  path=${1:-$PYPE_SETUP_PATH}
  echo -e "${IGreen}>>>${RST} Cleaning pyc at [ ${BIWhite}$path${RST} ] ... \c"
  find "$path" -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
  echo -e "${BIGreen}DONE${RST}"
}

# Main
art
detect_python || return 1

version_command="import version;print(version.__version__)"
pype_version="$(python3 <<< ${version_command})"
echo -e "${IGreen}>>>${RST} Building Pype [${IGreen} v$pype_version ${RST}]"
echo -e "${IGreen}>>>${RST} Creating virtual env ..."
python3 -m venv venv
echo -e "${IGreen}>>>${RST} Entering venv ..."
source venv/bin/activate
echo -e "${IGreen}>>>${RST} Installing packages to new venv ..."
pip install -r requirements.txt
echo -e "${IGreen}>>>${RST} Cleaning cache files ..."
clean_pyc
echo -e "${IGreen}>>>${RST} Building ..."
python setup.py build
deactivate
