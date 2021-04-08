#!/usr/bin/env bash

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
  # Directories

  openpype_root=$(realpath $(dirname $(dirname "${BASH_SOURCE[0]}")))
  pushd "$openpype_root" > /dev/null || return > /dev/null

  version_command="import os;exec(open(os.path.join('$openpype_root', 'openpype', 'version.py')).read());print(__version__);"
  openpype_version="$(python3 <<< ${version_command})"

  docker build -t pypeclub/openpype:$openpype_version .
  id="$(docker create pypeclub/openpype:$openpype_version)"
  docker cp "$id:/opt/openpype/build.linux-x86-64-3.7" "$openpype_root/build"
}

main
