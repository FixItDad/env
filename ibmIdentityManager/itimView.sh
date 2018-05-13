#!/bin/bash

# Tool for importing, exporting listing, etc ITIM view definitions.

# 2011-04-04 Paul T Sparks

SFX_DEF="_viewdef.del"
SFX_TSK="_viewtasks.del"


function usage {
  NAME=${0##*/}
  echo "ITIM View management tool. This tool should be run from the active ITIM database node as a suitably\
   privileged user."
  echo "Files are named <basename>${SFX_DEF} and <basename>_viewtasks.del"
  echo
  echo "Usage:"
  echo "$NAME display"
  echo "  displays list of Views in the database"
  echo
  echo "$NAME export <basename> \"View Name\""
  echo "  export the configuration data for a single view"
  echo
  echo "$NAME exportall <basename>"
  echo "  export the data for all views"
  echo
  echo "$NAME import <basename>"
  echo "  insert or update table from the file entries"
  exit 1
}

function error {
  echo "ERROR: $@"
  echo
}

function exportView { 
  db2 connect to itimdb >/dev/null
  db2 export to "${1}" of del "select * from itimuser.view_definition where name='${3}'"
  db2 export to "${2}" of del "select t.* from itimuser.view_definition d, itimuser.tasks_viewable t where d.id=t.view_id and d.name='${3}'"
  db2 disconnect >/dev/null
}

function exportAll {
  db2 connect to itimdb >/dev/null
  db2 export to "${1}" of del "select * from itimuser.view_definition"
  db2 export to "${2}" of del "select * from itimuser.tasks_viewable"
  db2 disconnect >/dev/null
}

function importView {
  db2 connect to itimdb >/dev/null  
  db2 import from "${1}" of del insert_update into itimuser.view_definition
  db2 import from "${2}" of del insert_update into itimuser.tasks_viewable
  db2 disconnect >/dev/null
}

# dump View names to output
function displayViews {
  db2 connect to itimdb >/dev/null
  db2 "select name from itimuser.view_definition"
  db2 disconnect >/dev/null
}




if [[ "$1" == "" ]]; then
		usage
fi

case "$1" in
(display)
  displayViews
;;

(export)
if [[ "$2" == "" ]]; then
	error "Missing base filename"
  usage
fi

if [[ "$3" == "" ]]; then
  error "Missing view name"
  usage
fi

exportView  "${2}${SFX_DEF}" "${2}${SFX_TSK}" "$3"
;;

(exportall)
if [[ "$2" == "" ]]; then
	error "Missing base filename"
  usage
fi

exportAll "${2}${SFX_DEF}" "${2}${SFX_TSK}"
;;

(import)
if [[ "$2" == "" ]]; then
	error "Missing base filename"
  usage
fi
DEF="${2}${SFX_DEF}"
TASK="${2}${SFX_TSK}"

if [[ ! -r "${DEF}" ]]; then
	error "Unable to read input file: $DEF"
  usage
fi

if [[ ! -r "${TASK}" ]]; then
	error "Unable to read input file: $TASK"
  usage
fi

importView "$DEF" "$TASK"
;;

(*)
error "Invalid operation: $1"
usage
;;
esac
