
# Stash values for use with Ansible
# Requires changes to ansible.cfg and the getvaultpw.sh script
function ansiblepw {
echo -n "become(sudo): "
read -s CTPW
export APV1=$(echo -n "$CTPW" |base64)
echo
echo -n "vault: "
read -s CTPW
export APV2=$(echo -n "$CTPW" |base64)
echo
unset CTPW
echo "Use ansibleoe or ansiblepb <str#> to run playbooks"
}

function ansiblepb() {
  APBENV="${1}"
  shift
  ansible-playbook -i env${APBENV} -e "@env${APBENV}.vault" -b $@
}

# Runs an ansible playbook
# For high security environment where SSH keys are not normally permitted.
# Copies SSH keys into place in an NFS mounted home directory for the
# duration of the ansible run then removes them.
function ansibleoe() {
  if [[ -f ~/.ssh/authorized_keys ]]; then
    echo "***** You have an ~/.ssh/authorized_keys file. Aborting to prevent overwriting."
    return
  fi
  /bin/cp -n ~/.ssh/ansible ~/.ssh/authorized_keys
  ansible-playbook -i env0 -e "@env0.vault" -b "$@"
  /bin/rm -f ~/.ssh/authorized_keys

}

# Runs an ansible command
# For high security environment where SSH keys are not normally permitted.
# Copies SSH keys into place in an NFS mounted home directory for the
# duration of the ansible run then removes them.
function ansiblecmd() {
  if [[ -f ~/.ssh/authorized_keys ]]; then
    echo "***** You have an ~/.ssh/authorized_keys file. Aborting to prevent overwriting."
    return
  fi
  /bin/cp -n ~/.ssh/ansible ~/.ssh/authorized_keys
  ansible -i env0 -e "@env0.vault" "$@"
  /bin/rm -f ~/.ssh/authorized_keys

}

# Creates a skeleton directory for an Ansible role. Creates the following files:
# rolename/rolename.tasks
# rolename/rolename.vars
# rolename/rolename.handlers
# This naming scheme keeps from having a bunch of main.yml files open in an editor.
function ansibleRole() {
    if [[ ! -d roles ]] || [[ ! -f ansible.cfg ]]; then
	echo "Please cd to the root of your Ansible configuration and rerun."
	return
    fi
    echo -n "Enter role name. No spaces: "
    read ANSROLE
    ROLEDIR="roles/${ANSROLE}"
    if [[ -e "${ROLEDIR}" ]]; then
	echo "Refusing to overwrite existing location ${ROLEDIR}"
	return
    fi

    mkdir -p "${ROLEDIR}" "${ROLEDIR}/files" "${ROLEDIR}/handlers" "${ROLEDIR}/tasks" "${ROLEDIR}/vars"
    ln -s files "${ROLEDIR}/templates"

    cat >${ROLEDIR}/tasks/main.yml <<EOF
---
- include: ../${ANSROLE}.tasks
  tags: ${ANSROLE}
EOF
    cat >${ROLEDIR}/${ANSROLE}.tasks <<EOF
#-*- mode: yaml -*-

- name: packages
  yum: name={{item}} state=latest
  with_items:
    - ${ANSROLE}

- name: config files mode 0644
  copy: src={{item}} dest=/{{item}} mode=0644
  with_items:

  notify: restart ${ANSROLE}

EOF

    ln -s ../${ANSROLE}.vars ${ROLEDIR}/vars/main.yml
    cat >${ROLEDIR}/${ANSROLE}.vars <<EOF
#-*- mode: yaml -*-

#var: value
#var:
#  - value
EOF

    ln -s ../${ANSROLE}.handlers ${ROLEDIR}/handlers/main.yml
    cat >${ROLEDIR}/${ANSROLE}.handlers <<EOF
#-*- mode: yaml -*-

#- name: restart ${ANSROLE}
#  service: name=${ANSROLE} state=restarted

EOF
}
