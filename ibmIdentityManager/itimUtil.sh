#!/bin/sh

# Wrapper script for the itimUtil.py utility. This is needed due to the limitations of
# IBM's WebSphere Jython implementation.
# 2013-08-12 Paul T Sparks

function issourced {
    [[ ${FUNCNAME[@]: -1} == "source" ]]
}

# If the script is sourced (not a sub-shell) then set passwords
if issourced ; then
    echo -n "Enter platform (wasadmin) password: "
    read -s _IU_PLAT_PW
    echo
    echo -n "Enter user password: "
    read -s _IU_USER_PW
    echo
    export _IU_PLAT_PW _IU_USER_PW
    echo "Passwords have been cached in memory"
    return
fi

if [[ "$_IU_PLAT_PW" == "" || "$_IU_USER_PW" == "" ]]; then
    echo
    echo "Re-run this command sourced to cache passwords:"
    echo ". $0"
    echo "or"
    echo "source $0"
    exit 1
fi


# Possibly environmental specific:
WASHOME=/opt/IBM/WebSphere/AppServer7
ITIMHOME=/opt/IBM/itim

# Find where this script is running from. Handle symlinks too.
MYDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
MYNAME=$(basename $0)
if [[ -L "$MYDIR/$MYNAME" ]]; then
    MYDIR=$(readlink -f "$MYDIR/$MYNAME")
    MYDIR=$(dirname $MYDIR)
fi


function abort {
    echo "$1"
    cat <<EOF
Usage: itimUtil.sh [options] userId [command file]
 -o <output file>  Needed since the underlying wsadmin pollutes stdout.
 -n  don't make updates. Dry run to determine what changes would be made.

The first time the script is run in a session, you will be prompted to 
run the script as a sourced file to enter passwords. The passwords will
be cached in memory for subsequent runs. Rerun the script sourced at any
time to reenter passwords. Passwords are stored as _IU_USER_PW and _IU_PLAT_PW

This utility allows some changes to be submitted to ITIM for
processing. Changes are submitted asynchonously and status is reported
later in the program output. Changes are input via a text file or from
stdin with one command per line. Command file structure is a text
command and parameters separated by tilde ~ characters. For example:
  personSuspend~(uid=psparks1)
is a command to suspend a person and their accounts. It takes 1
parameter which is an LDAP filter.

Some parameters can be Python lists or dictionaries. A list is just
zero or more comma separated values enclosed in square brackets
['value1', 'value2'].  A dictionary is a key to value mapping of the
form {keyvalue1 : value1, keyvalue2 : value2 ... }. The values in
lists and dictionaries can be simple strings, lists or dictionaries.
Either single or double quotes may be used around string values.

The commands to modify object attributes are of the form <object>Attr
(e.g. personAttr). These commands take an LDAP filter and a dictionary
of operations and attribute values. Operations are:
 Add - add new attribute values without overwriting existing values
 Del - delete all or specified attribute values for the object
 Rep - completely replace attribute values for an object

The following example command replaces telephone number and title and adds an email address.
  personAttr~(uid=garfield)~{'Rep':{'telephonenumber':['3046237333x683','3045551212'], 'title':"Jon's Pet"}, 'add':{'mail':'tester@test.com'}}

The second parameter is a dictionary with 2 operations:
 'Rep':{'telephonenumber':['3046237333x683','3045551212'], 'title':"Jon's Pet"} and
 'add':{'mail':'tester@test.com'}
The first operation handles the replacement of the telephone number
with 2 values (a list) and the title attribute (single value). The
second operation adds a new email address to whatever addresses are
already in the object.

The Del operation has 2 modes of operation:
  'Del':['attrname1', 'attrname2']
    deletes all values for the named attributes
  'Del': {'attr1':'value1', 'attr2':['value2','value3']}
    deletes only the specified values for the attribute. Other values
    are preserved.

If the specified LDAP filter returns multiple objects, the command
will be applied to all of the objects. You may want to use the dry run (-n)
option to validate your filter before running the command with updates
enabled.

Valid commands are:
  accountAttr~LDAP filter~attribute values dict
    Update account attributes
  accountRestore~LDAP filter
    Restore an account

  personCreate~Organization Name~Profile Name~attribute list
    Create an identity of type Profile Name (e.g. LOCALPerson) in 
    Organization Name (e.g. LOCALUsers) with the specified attributes.
  personSuspend~LDAP filter
    Suspend the person and all accounts
  personRestore~LDAP filter
    Restore the person and all accounts
  personExtract~LDAP filter~attribute list
    Dump person data in the command input format.
  personAttr~LDAP filter~attribute value operations dict
    Update person attributes

  serviceAttr~LDAP filter~attribute value operations dict
    Update service attributes

  [DO NOT USE]systemuserAttr~LDAP filter~attribute value operations dict
    Update systemuser (ITIM account) attributes

  wait~secs
    Pause the specified number of seconds. May be needed for large 
    number of requests.
  waitForRequests~secs
    Wait the specified number of seconds for submitted requests to complete.
    By default itimUtil waits 30 seconds at the end for requests to complete.

ITIM applies filtering for object type so generally you do not need to
specify (objectclass=erPersonItem) type clauses to your LDAP filters.

Results of requests are included in the output in the following format:
Result: succ 10:20:15 personAttr name-globalid=jsparks5-8015048491193667326 {'rep':{'ercreatedate': '199912131200Z'}}
Result: succ 10:20:15 personAttr name-globalid=jsparks6-8015047087550458673 {'rep':{'ercreatedate': '199912131200Z'}}
|       |    |        |          |                                          +> change details
|       |    |        |          + object identifier and ITIM globalid
|       |    |        + command performed
|       |    + timestamp that request was completed
|       + Status indication (succ, fail, or warn)
+ Results lines start with "Result: "

EXAMPLES

accountAttr~(&(eritamgroupname=helpdesk)(!(eritamgroupname=helpdesk_limited)))~{'del':{'eritamgroupname':'helpdesk'}, 'add':{'eritamgroupname':'helpdesk_limited'}}
  Change TAM group membership from helpdesk to helpdesk_limited
  for all persons that have helpdesk but not helpdesk_limited.

serviceAttr~(erservicename=TAM Local)~{'rep':{'erservicepwd1':'newTamPW', 'erservicepwd2':'newLdapPW'}}
  Change TAM and LDAP passwords for the TAM Local TAM service

EOF
    exit 1
}

function checkRequiredArg {
    NAME="$1"
    MSG="$2"
    if [[ "" == "$NAME" ]]; then 
        abort "$MSG"
    fi
}



while getopts "nw:p:o:" option; do
    case "${option}" in
        o) OUTPUT_FILE="${OPTARG}";;
        n) DRY_RUN="Y";;
    esac
done

# Get rid of processed options leaving only arguments (presumably).
shift $((( ${OPTIND} - 1)))

USER_ID="$1"
checkRequiredArg "$USER_ID" "ITIM user login ID must be specified."

# COMMAND_FILE is optional. If it does not exist, read from STDIN
if [[ "" != "$2" ]]; then
    if [[ -r "$2" ]]; then
        COMMAND_FILE="$2"
    else
        abort "Command file: $2 does not exist or is not readable."
    fi
fi

export USER_ID
export USER_PW="$_IU_USER_PW"
export PLATFORM_PW="$_IU_PLAT_PW"
export COMMAND_FILE
export OUTPUT_FILE
export DRY_RUN

AS_HOME=$(dirname $0)

AS_LOGIN_CONFIG=${ITIMHOME}/extensions/6.0/examples/apps/bin/jaas_login_was.conf
AS_CP=${ITIMHOME}/data:${ITIMHOME}/lib/jlog.jar:${ITIMHOME}/lib/api_ejb.jar:${ITIMHOME}/lib/itim_api.jar:${ITIMHOME}/lib/itim_common.jar:${ITIMHOME}/lib/jlog.jar:${ITIMHOME}/lib/com.ibm.cv.kmip.ext.jar

$WASHOME/bin/wsadmin.sh -conntype none -lang jython \
  -profile $AS_HOME/jythonSetup.py \
  -javaoption "-Djava.security.auth.login.config=${AS_LOGIN_CONFIG}" \
  -javaoption "-Dapiscript.security.auth.login.config=${AS_LOGIN_CONFIG}" \
  -p ${ITIMHOME}/data/enRole.properties \
  -wsadmin_classpath "$AS_CP" \
  -f $AS_HOME/itimUtil.py

