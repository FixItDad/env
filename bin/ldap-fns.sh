# -*-sh-*-

# Set up for easy access to LDAP servers. This requires storing LDAP
# passwords encrypted on disk. A user specific password is defined in
# the shell environment as a decryption key. Because the ldap
# utilities are limited in secure ways to accept a password, a named
# pipe is used to feed the decrypted LDAP bind password to the ldap
# utility. That way it is not visible on the command line, is stored in decrypted form on disk and the
# value is consumed very quickly.
_LDAPDIR=${HOME}/.ldap
function ldapinit {
  mkdir -p ${HOME}/.ldap/cred
  chmod -R 700 ${HOME}/.ldap
  if [[ ! -p ${_LDAPDIR}/hash ]]; then
     rm -f ${_LDAPDIR}/hash
     mkfifo -m 600 ${_LDAPDIR}/hash
  fi
  if [[ "" == "${_LDAP_ENC_KEY}" ]]; then
      echo -n "Enter your personal LDAP credentials encryption password: "
      read -s _LDAP_ENC_KEY
      echo
  fi
  export _LDAP_ENC_KEY
  if [[ ! -f ${_LDAPDIR}/servers ]]; then
      echo "nickname~serverURL~bind DN" > ${_LDAPDIR}/servers
      chmod 600 ${_LDAPDIR}/servers
      echo "Please define your ldap servers in ${_LDAPDIR}/servers"
      echo "Use ldapsavepw to store the password."
  fi
}

# Remove personal password from the environment. Use if you typo your password in ldapinit.
function ldapdone {
    unset _LDAP_ENC_KEY
}

# Save an LDAP bind password encrypted on disk
function ldapsavepw {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  _LDAPDN=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f3)
  rm -f ${_LDAPDIR}/cred/${1}
  touch ${_LDAPDIR}/cred/${1}
  chmod 600 ${_LDAPDIR}/cred/${1}
  echo -n "Enter bind password for ${_LDAPDN} on ${_LDAPIP}: "
  read -s _LDAPTMP
  echo
  echo -n "${_LDAPTMP}"| openssl enc -aes-256-cbc -md sha256 -pass env:_LDAP_ENC_KEY -out ${_LDAPDIR}/cred/${1}
  unset _LDAPTMP
}

function ldapchk {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  ldapsearch -H ${_LDAPIP} -LLL -x -W -D "${2}" -s base '(objectclass=*)' namingcontexts
}

function ldapq {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  _LDAPDN=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f3)
  (openssl enc -d -aes-256-cbc -md sha256 -pass env:_LDAP_ENC_KEY -in ${_LDAPDIR}/cred/${1} -out ${_LDAPDIR}/hash &)
  shift
  ldapsearch -H ${_LDAPIP} -y ${_LDAPDIR}/hash -LLL -x -D "$_LDAPDN" "$@"
}
# for IBM version of ldapsearch
function ildapq {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  _LDAPDN=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f3)
  (openssl enc -d -aes-256-cbc -md sha256 -pass env:_LDAP_ENC_KEY -in ${_LDAPDIR}/cred/${1} -out ${_LDAPDIR}/hash &)
  shift
  ldapsearch -s sub -H ${_LDAPIP} -L -w $(<${_LDAPDIR}/hash) -D "$_LDAPDN" -b '' "$@"
}

function ldappw {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  _LDAPDN=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f3)
  (openssl enc -d -aes-256-cbc -md sha256 -pass env:_LDAP_ENC_KEY -in ${_LDAPDIR}/cred/${1} -out ${_LDAPDIR}/hash &)
  shift
  ldappasswd -H ${_LDAPIP} -x -y ${_LDAPDIR}/hash -D "$_LDAPDN" -S "$@"
}

function ldapmod {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  _LDAPDN=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f3)
  (openssl enc -d -aes-256-cbc -md sha256 -pass env:_LDAP_ENC_KEY -in ${_LDAPDIR}/cred/${1} -out ${_LDAPDIR}/hash &)
  shift
  ldapmodify -H ${_LDAPIP} -x -y ${_LDAPDIR}/hash -D "$_LDAPDN"  "$@"
}

function ildapmod {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  _LDAPDN=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f3)
  (openssl enc -d -aes-256-cbc -md sha256 -pass env:_LDAP_ENC_KEY -in ${_LDAPDIR}/cred/${1} -out ${_LDAPDIR}/hash &)
  shift
  /opt/ibm/ldap/V6.3/bin/idsldapmodify -H ${_LDAPIP} -w $(<${_LDAPDIR}/hash) -D "$_LDAPDN"  "$@"
}

function ldapdel {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  _LDAPDN=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f3)
  (openssl enc -d -aes-256-cbc -md sha256 -pass env:_LDAP_ENC_KEY -in ${_LDAPDIR}/cred/${1} -out ${_LDAPDIR}/hash &)
  shift
  ldifUnfold |grep ^dn |
  sed -e 'a\
changetype: delete\
' |
  ldapmodify -H ${_LDAPIP} -x -y ${_LDAPDIR}/hash -D "$_LDAPDN" "$@"
}

function ldapunlock {
  _LDAPIP=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f2)
  _LDAPDN=$(grep "^${1}~" ${_LDAPDIR}/servers |cut -d~ -f3)
  (openssl enc -d -aes-256-cbc -md sha256 -pass env:_LDAP_ENC_KEY -in ${_LDAPDIR}/cred/${1} -out ${_LDAPDIR}/hash &)
  DN=$(ldapq "${1}" -b 'dc=TODO' "dn=${2}" dn |ldifUnfold |grep ^dn)
  (echo $DN;
  echo "changetype: modify"
  echo "delete: pwdfailuretime"
  echo "-"
  echo "delete: pwdaccountlockedtime"
  echo "-"
  ) |/opt/ibm/ldap/V6.3/bin/64/ldapmodify -k -D "$_LDAPDN" -w "$(<${_LDAPDIR}/hash)"
}

