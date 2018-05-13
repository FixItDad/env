# -*-sh-*-
# Shell functions for manipulating LDAP objects for IBM ISIM / ITIM product

function itimGetForm {
  ldapq "${1}" -b 'dc=itim ' "erformname=${2}" erxml |sed -e '1d' -e '2s/^erxml:: //' |openssl enc -d -base64
}

function itimSetForm {
  DN=$(ldapq "${1}" "erformname=${2}" dn |ldifUnfold |grep ^dn)
  (echo $DN;
  echo "changetype: modify"
  echo "replace: erxml"
  openssl enc -base64 -in ${3} |sed -n -e '1s/^/erxml:: /p' -e '2,$s/^/ /p'
  ) |ldapmod "${1}"
}

function itimGetMail {
  TEXT=$(ldapq "${1}" -b "ou=${3},ou=values,ou=itim,ou=localcorp,dc=itim" "cn=${2}" cisproperty)
  if echo "$TEXT" | grep "^cisproperty::" >/dev/null; then
      echo "$TEXT"|sed -e '1d' -e '2s/^cisproperty:: //' |openssl enc -d -base64
  else
      echo "$TEXT"|ldifUnfold |sed -e '1d' -e '2s/^cisproperty: //'
  fi
}

function itimSetHtmlMail {
  if (( "$#" < 4 )); then
      cat <<EOF
Usage: itimSetHtmlMail <ldapID> <IDP> <emailID> <HTML filename>
e.g. itimSetHtmlMail 4 leo emailarchive newtext.html
EOF
      return
  fi
  DN=$(ldapq "${1}" -b "ou=${3}-htmlbody,ou=values,ou=itim,ou=localcorp,dc=itim" "cn=${2}" dn |ldifUnfold |grep ^dn)
  (echo $DN;
  echo "changetype: modify"
  echo "replace: cisproperty"
  openssl enc -base64 -in ${4} |sed -n -e '1s/^/cisproperty:: /p' -e '2,$s/^/ /p'
  ) |ldapmod "${1}"
}

function itimSetTextMail {
  if (( "$#" < 4 )); then
      cat <<EOF
Usage: itimSetTextMail <ldapID> <IDP> <emailID> <HTML filename>
e.g. itimSetTextMail 4 leo emailarchive newtext.html
EOF
      return
  fi
  DN=$(ldapq "${1}" -b "ou=${3}-textbody,ou=values,ou=itim,ou=localcorp,dc=itim" "cn=${2}" dn |ldifUnfold |grep ^dn)
  (echo $DN;
  echo "changetype: modify"
  echo "replace: cisproperty"
  openssl enc -base64 -in ${4} |sed -n -e '1s/^/cisproperty:: /p' -e '2,$s/^/ /p'
  ) |ldapmod "${1}"
}

function itimGetProcessByName {
  ldapq "${1}" -b 'ou=operations,ou=itim,ou=LOCALCORP,dc=itim' "erprocessname=${2}" erxml |sed -e '1d' -e '2s/^erxml:: //' -e '/^$/q' |openssl enc -d -base64
}

function itimSetProcessByName {
  DN=$(ldapq "${1}" -b 'ou=operations,ou=itim,ou=LOCALCORP,dc=itim' "erprocessname=${2}" dn |ldifUnfold |grep ^dn)
  (echo $DN;
  echo "changetype: modify"
  echo "replace: erxml"
  openssl enc -base64 -in ${3} |sed -n -e '1s/^/erxml:: /p' -e '2,$s/^/ /p'
  ) |ldapmod "${1}"
}

function itimGetProcessById {
  ldapq "${1}" -b 'ou=operations,ou=itim,ou=LOCALCORP,dc=itim' "erglobalid=${2}" erxml |sed -e '1d' -e '2s/^erxml:: //' -e '/^$/q' |openssl enc -d -base64
}

function itimSetProcessById {
  DN=$(ldapq "${1}" -b 'ou=operations,ou=itim,ou=LOCALCORP,dc=itim' "erglobalid=${2}" dn |ldifUnfold |grep ^dn)
  (echo $DN;
  echo "changetype: modify"
  echo "replace: erxml"
  openssl enc -base64 -in ${3} |sed -n -e '1s/^/erxml:: /p' -e '2,$s/^/ /p'
  ) |ldapmod "${1}"
}

# Simulate N days from current day of inactivity for a user (for testing)
function simInactivity {
    if [[ "$3" == "" ]]; then
	echo "Usage: simInactivity <env> <uid> <number of days>"
	exit 1
    fi
    ID="${2}"
    DAYS="$3"
    DN=$(ldapq "${1}" -b 'ou=LOCALCORP,dc=itim' "(&(objectclass=localcorpperson)(uid=${ID}))" dn |ldifUnfold |grep ^dn: |cut -c 5-)
    AGE=$(date -d "today - ${DAYS} days" +"%Y%m%d0000Z")
    echo -e "dn: ${DN}\nchangetype:modify\nreplace: erlastaccessdate\nerlastaccessdate: ${AGE}\n-\n\n" |ldapmod "${1}"
}

