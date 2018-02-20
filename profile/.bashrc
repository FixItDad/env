# .bashrc

# Source global definitions
if [ -f /etc/bashrc ]; then
    . /etc/bashrc
fi
# Do my own version if I don;t like the system default
#if [ -f ${HOME}/.sys_bashrc ]; then
#    . ${HOME}/.sys_bashrc
#fi

# Include user specific aliases and functions
if [ -f ${HOME}/.aliases ]; then
  . ${HOME}/.aliases
fi

# Include ansible functions
if [ -f "${HOME}/bin/ansible-fns.sh" ]; then
  . "${HOME}/bin/ansible-fns.sh"
fi

# Include ldap functions
if [ -f "${HOME}/bin/ldap-fns.sh" ]; then
  . "${HOME}/bin/ldap-fns.sh"
fi

# Include itim functions (requires LDAP fns above)
if [ -f "${HOME}/bin/itim-fns.sh" ]; then
  . "${HOME}/bin/itim-fns.sh"
fi

PATH="${HOME}"/bin:$PATH:/sbin:/usr/sbin

export EDITOR=emacs
export HISTCONTROL=ignoredups:ignorespace
export HISTFILE=~/.bash_history-${HOSTNAME%%.*}
export HISTTIMEFORMAT="%d-%H%M%S "

####SSHagent settings####
SSH_ENV="$HOME/.ssh/environment"
# List of hosts where ssh-agent should start
STARTHOSTS='TODOhomesvr'

function start_agent {
    echo "Initializing new SSH agent..."
    /usr/bin/ssh-agent | sed 's/^echo/#echo/' > "${SSH_ENV}"
    echo succeeded
    chmod 600 "${SSH_ENV}"
    . "${SSH_ENV}" > /dev/null
}

# Source SSH settings, if applicable
if echo "$STARTHOSTS" |grep "$HOSTNAME" >/dev/null; then
    if [ -f "${SSH_ENV}" ]; then
        . "${SSH_ENV}" > /dev/null
        kill -0 ${SSH_AGENT_PID} >/dev/null || {
            start_agent;
        }
    else
        start_agent;
    fi
fi
if [ ! $DISPLAY ] ; then
    if [ "$SSH_CLIENT" ] ; then
        export DISPLAY=`echo $SSH_CLIENT|cut -f1 -d\ `:0.0
    fi
fi
