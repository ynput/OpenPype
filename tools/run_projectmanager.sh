#!/usr/bin/env bash

# Run OpenPype Settings GUI


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

  _inside_openpype_tool="1"

  if [[ -z $POETRY_HOME ]]; then
    export POETRY_HOME="$openpype_root/.poetry"
  fi

  pushd "$openpype_root" > /dev/null || return > /dev/null

  echo -e "${BIGreen}>>>${RST} Reading Poetry ... \c"
  if [ -f "$POETRY_HOME/bin/poetry" ]; then
    echo -e "${BIGreen}OK${RST}"
  else
    echo -e "${BIYellow}NOT FOUND${RST}"
    echo -e "${BIYellow}***${RST} We need to install Poetry and virtual env ..."
    . "$openpype_root/tools/create_env.sh" || { echo -e "${BIRed}!!!${RST} Poetry installation failed"; return; }
  fi

  echo -e "${BIGreen}>>>${RST} Generating zip from current sources ..."
  "$POETRY_HOME/bin/poetry" run python "$openpype_root/start.py" projectmanager
}

main
