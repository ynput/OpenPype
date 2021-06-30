#!/usr/bin/env bash

# Colors for terminal

RST='\033[0m'             # Text Reset
BIGreen='\033[1;92m'      # Green
BIYellow='\033[1;93m'     # Yellow
BIRed='\033[1;91m'        # Red

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
  echo $(cd $(dirname "$1"); pwd)/$(basename "$1")
}

# Main
main () {
  openpype_root=$(realpath $(dirname $(dirname "${BASH_SOURCE[0]}")))
  pushd "$openpype_root" > /dev/null || return > /dev/null

  echo -e "${BIYellow}---${RST} Cleaning build directory ..."
  rm -rf "$openpype_root/build" && mkdir "$openpype_root/build" > /dev/null

  version_command="import os;exec(open(os.path.join('$openpype_root', 'openpype', 'version.py')).read());print(__version__);"
  openpype_version="$(python3 <<< ${version_command})"

  echo -e "${BIGreen}>>>${RST} Running docker build ..."
  docker build --pull -t pypeclub/openpype:$openpype_version .
  if [ $? -ne 0 ] ; then
    echo -e "${BIRed}!!!${RST} Docker build failed."
    return 1
  fi

  echo -e "${BIGreen}>>>${RST} Copying build from container ..."
  echo -e "${BIYellow}---${RST} Creating container from pypeclub/openpype:$openpype_version ..."
  id="$(docker create -ti pypeclub/openpype:$openpype_version bash)"
  if [ $? -ne 0 ] ; then
    echo -e "${BIRed}!!!${RST} Cannot create just built container."
    return 1
  fi
  echo -e "${BIYellow}---${RST} Copying ..."
  docker cp "$id:/opt/openpype/build/exe.linux-x86_64-3.7" "$openpype_root/build"
  if [ $? -ne 0 ] ; then
    echo -e "${BIRed}!!!${RST} Copying failed."
    return 1
  fi

  echo -e "${BIGreen}>>>${RST} Fixing user ownership ..."
  username="$(logname)"
  chown -R $username ./build

  echo -e "${BIGreen}>>>${RST} All done, you can delete container:"
  echo -e "${BIYellow}$id${RST}"
}

return_code=0
main || return_code=$?
exit $return_code
