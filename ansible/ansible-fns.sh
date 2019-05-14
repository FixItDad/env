
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

    mkdir -p "${ROLEDIR}" "${ROLEDIR}/defaults" "${ROLEDIR}/files" "${ROLEDIR}/handlers" "${ROLEDIR}/meta" "${ROLEDIR}/tasks" "${ROLEDIR}/vars"
    ln -s files "${ROLEDIR}/templates"

    cat >${ROLEDIR}/tasks/main.yml <<EOF
---
- include: tasks.yml
  tags: ${ANSROLE}
EOF
    cat >${ROLEDIR}/tasks/tasks.yml <<EOF
---
- name: packages
  yum: name={{packages}} state=present
  vars:
    packages:
    - ${ANSROLE}
  when: (ansible_pkg_mgr == 'yum')
- name: packages
  apt: name={{packages}} state=present
  vars:
    packages:
    - ${ANSROLE}
  when: (ansible_pkg_mgr == 'apt')

- name: packages
  apt: name={{item}} state=latest
  when: (ansible_pkg_mgr == "apt")
  with_items:
    - ${ANSROLE}

- name: config files mode 0644
  copy: src={{item}} dest=/{{item}} mode=0644
  with_items:

  notify: restart ${ANSROLE}

EOF
    ln -s tasks/tasks.yml ${ROLEDIR}/${ANSROLE}.tasks.yml

    cat >${ROLEDIR}/defaults/main.yml <<EOF
---
#var: value
#var:
#  - value
EOF
    ln -s defaults/main.yml ${ROLEDIR}/${ANSROLE}.defaults.yml

    cat >${ROLEDIR}/vars/main.yml <<EOF
---
#var: value
#var:
#  - value
EOF
    ln -s vars/main.yml ${ROLEDIR}/${ANSROLE}.vars.yml

    cat >${ROLEDIR}/handlers/main.yml <<EOF
#-*- mode: yaml -*-

#- name: restart ${ANSROLE}
#  service: name=${ANSROLE} state=restarted

EOF
    ln -s handlers/main.yml ${ROLEDIR}/${ANSROLE}.handlers.yml

    cat >${ROLEDIR}/meta/main.yml <<EOF
galaxy_info:
  author: your name
  description: your description
  company: your company (optional)

  # If the issue tracker for your role is not on github, uncomment the
  # next line and provide a value
  # issue_tracker_url: http://example.com/issue/tracker

  # Some suggested licenses:
  # - BSD (default)
  # - MIT
  # - GPLv2
  # - GPLv3
  # - Apache
  # - CC-BY
  license: license (GPLv2, CC-BY, etc)

  min_ansible_version: 1.2

  # If this a Container Enabled role, provide the minimum Ansible Container version.
  # min_ansible_container_version:

  # Optionally specify the branch Galaxy will use when accessing the GitHub
  # repo for this role. During role install, if no tags are available,
  # Galaxy will use this branch. During import Galaxy will access files on
  # this branch. If Travis integration is configured, only notifications for this
  # branch will be accepted. Otherwise, in all cases, the repo's default branch
  # (usually master) will be used.
  #github_branch:

  #
  # platforms is a list of platforms, and each platform has a name and a list of versions.
  #
  # platforms:
  # - name: Fedora
  #   versions:
  #   - all
  #   - 25
  # - name: SomePlatform
  #   versions:
  #   - all
  #   - 1.0
  #   - 7
  #   - 99.99

  galaxy_tags: []
    # List tags for your role here, one per line. A tag is a keyword that describes
    # and categorizes the role. Users find roles by searching for tags. Be sure to
    # remove the '[]' above, if you add tags to this list.
    #
    # NOTE: A tag is limited to a single word comprised of alphanumeric characters.
    #       Maximum 20 tags per role.

dependencies: []
  # List your role dependencies here, one per line. Be sure to remove the '[]' above,
  # if you add dependencies to this list.
EOF

}
